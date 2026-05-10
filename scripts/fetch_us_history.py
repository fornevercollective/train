"""Fetch full daily OHLCV history for every US listing in the catalog.

Defaults to Yahoo Finance's `v8/finance/chart` endpoint (keyless, JSON, supports
adjusted close + split metadata). Stooq is available as a fallback via
`--source stooq` for users with a Stooq API key (`--apikey` or `STOOQ_APIKEY`).
The `yfinance` Python package is the recommended path for full backfills — it
handles Yahoo's auth crumbs and is robust against rate limits.

By default the fetcher requests **max** available history per ticker (so IBM
goes back to 1962, AAPL to 1980, etc.). Pass `--lookback 5y` or `--lookback 1825d`
if you only want a fixed window.

Output is one compact JSON file per ticker under
`public/data/history/series/v1/<TICKER>.json`. The
`build_history_manifest.py` step then collapses those files into a small index with
sha-256 etags so clients can fetch only what changed — never the whole catalog.

Design notes:
  - Resumable: existing files are kept unless older than --max-age-days (default 7).
  - Throttled: --delay seconds between requests (default 0.25, ~4 req/s).
  - Filterable: --exchange, --tickers, --limit, --skip flags so you can backfill
    in batches and parallel-shard across machines.
  - Polite: identifies a User-Agent, retries with long backoff on 429 / 5xx.

Usage examples:
  # Smoke test (10 NASDAQ listings, full available history each)
  python3 scripts/fetch_us_history.py --exchange NASDAQ --limit 10

  # Specific watchlist, only the last 5 years
  python3 scripts/fetch_us_history.py --tickers AAPL,MSFT,SPY,QQQ,NVDA --lookback 5y

  # Full backfill across the major US exchanges, full history each (slow; run in CI)
  python3 scripts/fetch_us_history.py --source yfinance \\
      --exchange NASDAQ,NYSE,NYSEARCA,NYSEMKT,CBOE --lookback max
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable, Optional

ROOT = Path(__file__).resolve().parent.parent
CATALOG_JSON = ROOT / "public" / "data" / "catalog.json"
SERIES_DIR = ROOT / "public" / "data" / "history" / "series" / "v1"

US_EXCHANGES = {"NASDAQ", "NYSE", "NYSEARCA", "NYSEMKT", "CBOE", "AMEX", "BATS", "OTC", "OTCBB"}

YAHOO_BASE = "https://query1.finance.yahoo.com/v8/finance/chart/"
STOOQ_BASE = "https://stooq.com/q/d/l/"

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)
DEFAULT_LOOKBACK = "max"
DEFAULT_DELAY_SECONDS = 0.25
DEFAULT_MAX_AGE_DAYS = 7
DEFAULT_RETRIES = 3

# Earliest plausible US equity date Yahoo / Stooq will accept; pre-dates every
# major exchange's electronic record. Stooq's earliest US series go back to 1969,
# Yahoo's CBOE / NYSE archives reach 1962. period1=0 means epoch (1970-01-01).
EARLIEST_FULL_HISTORY_DATE = date(1962, 1, 2)


class Lookback:
    """Parsed --lookback value. Either 'max' (full available history) or a fixed window."""

    def __init__(self, raw: str):
        self.raw = raw.strip().lower()
        self.is_max = self.raw in ("max", "all", "full", "0")
        self.days: Optional[int] = None
        if not self.is_max:
            if self.raw.endswith("y"):
                self.days = int(float(self.raw[:-1]) * 365.25)
            elif self.raw.endswith("d"):
                self.days = int(self.raw[:-1])
            else:
                # Bare integer = years (back-compat with the old --lookback-years int).
                try:
                    self.days = int(float(self.raw) * 365.25)
                except ValueError as exc:
                    raise SystemExit(
                        f"Invalid --lookback value: {raw!r}. "
                        "Expected 'max', '<N>y', '<N>d', or a plain integer year count."
                    ) from exc

    @property
    def years_hint(self) -> int:
        """Numeric years value to write into the JSON. 0 => 'max'."""

        if self.is_max:
            return 0
        return int(round((self.days or 0) / 365.25))

    def start_date(self, end: date) -> date:
        if self.is_max:
            return EARLIEST_FULL_HISTORY_DATE
        return end - timedelta(days=int(self.days or 0))

    def yfinance_period(self) -> str:
        if self.is_max:
            return "max"
        years = max(1, self.years_hint)
        if years <= 10:
            return f"{years}y"
        return "max"

    def __str__(self) -> str:
        return "max" if self.is_max else f"{self.days}d"


def _yahoo_symbol(record: dict[str, object]) -> Optional[str]:
    """Yahoo accepts most US symbols verbatim; class shares use a hyphen (e.g. BRK-B)."""

    exchange = str(record.get("ex") or "").upper()
    if exchange not in US_EXCHANGES:
        return None
    sym = str(record.get("sy") or "").strip().upper()
    if not sym:
        return None
    return sym.replace(".", "-")


def _stooq_symbol(record: dict[str, object]) -> Optional[str]:
    """Stooq US symbols are lowercased and have a `.us` suffix; class shares use a hyphen."""

    exchange = str(record.get("ex") or "").upper()
    if exchange not in US_EXCHANGES:
        return None
    sym = str(record.get("sy") or "").strip()
    if not sym:
        return None
    cleaned = sym.lower().replace(".", "-").replace(" ", "")
    if not cleaned or any(ch not in "abcdefghijklmnopqrstuvwxyz0123456789-" for ch in cleaned):
        return None
    return f"{cleaned}.us"


def _patch_filename(ticker: str) -> str:
    safe = "".join(ch if ch.isalnum() or ch in "._-" else "-" for ch in ticker)
    return f"{safe}.json"


def _filter_records(
    records: list[dict[str, object]],
    *,
    exchanges: set[str],
    tickers: Optional[set[str]],
    skip: int,
    limit: Optional[int],
) -> list[dict[str, object]]:
    selected: list[dict[str, object]] = []
    for record in records:
        if tickers is not None:
            if str(record.get("id")) not in tickers and str(record.get("sy")) not in tickers:
                continue
        else:
            if str(record.get("ex") or "").upper() not in exchanges:
                continue
        selected.append(record)
    selected.sort(key=lambda r: str(r.get("id", "")))
    if skip:
        selected = selected[skip:]
    if limit is not None:
        selected = selected[:limit]
    return selected


def _http_get(url: str, *, retries: int, user_agent: str) -> bytes:
    last_exc: Optional[Exception] = None
    for attempt in range(retries + 1):
        request = urllib.request.Request(
            url,
            headers={
                "User-Agent": user_agent,
                "Accept": "*/*",
                "Accept-Language": "en-US,en;q=0.9",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return response.read()
        except urllib.error.HTTPError as exc:
            last_exc = exc
            if exc.code == 429 and attempt < retries:
                # Yahoo, Stooq, etc. all penalize bursts heavily. Back off in minutes.
                backoff = 30 * (attempt + 1)
                time.sleep(backoff)
                continue
            if exc.code in (500, 502, 503, 504) and attempt < retries:
                time.sleep(2.0 * (attempt + 1))
                continue
            raise
        except urllib.error.URLError as exc:
            last_exc = exc
            if attempt < retries:
                time.sleep(1.0 * (attempt + 1))
                continue
            raise
    raise RuntimeError(f"unreachable: {last_exc}")


def _parse_stooq_csv(payload: bytes) -> list[tuple[int, float, float, float, float, int]]:
    text = payload.decode("utf-8", errors="replace").strip()
    if not text or text.lower().startswith("no data") or text.lower().startswith("get your apikey"):
        return []
    reader = csv.reader(io.StringIO(text))
    header = next(reader, None)
    if not header or header[0].lower() != "date":
        return []
    rows: list[tuple[int, float, float, float, float, int]] = []
    for raw in reader:
        if len(raw) < 6:
            continue
        try:
            d = int(raw[0].replace("-", ""))
            o = float(raw[1])
            h = float(raw[2])
            low = float(raw[3])
            c = float(raw[4])
            v = int(float(raw[5]))
        except ValueError:
            continue
        rows.append((d, o, h, low, c, v))
    rows.sort(key=lambda r: r[0])
    return rows


def _parse_yahoo_chart(payload: bytes) -> list[tuple[int, float, float, float, float, int]]:
    try:
        body = json.loads(payload.decode("utf-8", errors="replace"))
    except json.JSONDecodeError:
        return []
    chart = body.get("chart") or {}
    if chart.get("error"):
        return []
    results = chart.get("result") or []
    if not results:
        return []
    result = results[0]
    timestamps = result.get("timestamp") or []
    indicators = result.get("indicators") or {}
    quote = (indicators.get("quote") or [{}])[0]
    opens = quote.get("open") or []
    highs = quote.get("high") or []
    lows = quote.get("low") or []
    closes = quote.get("close") or []
    volumes = quote.get("volume") or []

    rows: list[tuple[int, float, float, float, float, int]] = []
    for index, ts in enumerate(timestamps):
        try:
            o = opens[index]
            h = highs[index]
            low = lows[index]
            c = closes[index]
            v = volumes[index]
        except IndexError:
            continue
        if c is None or o is None or h is None or low is None:
            continue
        day = datetime.fromtimestamp(int(ts), tz=timezone.utc).strftime("%Y%m%d")
        rows.append((int(day), float(o), float(h), float(low), float(c), int(v or 0)))
    rows.sort(key=lambda r: r[0])
    return rows


def _series_payload(
    *,
    record: dict[str, object],
    source: str,
    source_symbol: str,
    rows: list[tuple[int, float, float, float, float, int]],
    lookback: "Lookback",
) -> dict[str, object]:
    return {
        "schemaVersion": 1,
        "ticker": str(record["id"]),
        "exchange": str(record.get("ex") or ""),
        "displayName": str(record.get("nm") or record.get("ln") or record["id"]),
        "source": source,
        "sourceSymbol": source_symbol,
        "interval": "daily",
        "asOfISO": datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "lookbackYears": lookback.years_hint,
        "lookbackMode": "max" if lookback.is_max else "fixed",
        "rows": len(rows),
        "rangeStart": rows[0][0] if rows else 0,
        "rangeEnd": rows[-1][0] if rows else 0,
        "d": [r[0] for r in rows],
        "o": [r[1] for r in rows],
        "h": [r[2] for r in rows],
        "l": [r[3] for r in rows],
        "c": [r[4] for r in rows],
        "v": [r[5] for r in rows],
    }


def _is_fresh(path: Path, max_age_days: int) -> bool:
    try:
        existing = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    as_of = str(existing.get("asOfISO") or "")
    if not as_of:
        return False
    try:
        when = datetime.strptime(as_of, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError:
        return False
    return datetime.now(tz=timezone.utc) - when < timedelta(days=max_age_days)


def fetch_one(
    record: dict[str, object],
    *,
    lookback: "Lookback",
    user_agent: str,
    retries: int,
    source: str,
    stooq_apikey: Optional[str] = None,
) -> Optional[dict[str, object]]:
    end = date.today()
    start = lookback.start_date(end)

    if source == "yahoo":
        symbol = _yahoo_symbol(record)
        if not symbol:
            return None
        # period1=0 (epoch) means "give me everything you have" on Yahoo's v8 endpoint.
        period_start = (
            0
            if lookback.is_max
            else int(datetime(start.year, start.month, start.day, tzinfo=timezone.utc).timestamp())
        )
        period_end = int(datetime(end.year, end.month, end.day, tzinfo=timezone.utc).timestamp())
        query = urllib.parse.urlencode(
            {
                "period1": period_start,
                "period2": period_end,
                "interval": "1d",
                "events": "history",
                "includeAdjustedClose": "true",
            }
        )
        url = f"{YAHOO_BASE}{urllib.parse.quote(symbol)}?{query}"
        payload = _http_get(url, retries=retries, user_agent=user_agent)
        rows = _parse_yahoo_chart(payload)
        if not rows:
            return None
        return _series_payload(
            record=record,
            source="yahoo",
            source_symbol=symbol,
            rows=rows,
            lookback=lookback,
        )

    if source == "stooq":
        symbol = _stooq_symbol(record)
        if not symbol:
            return None
        params = {
            "s": symbol,
            "i": "d",
            "d1": start.strftime("%Y%m%d"),
            "d2": end.strftime("%Y%m%d"),
        }
        if stooq_apikey:
            params["apikey"] = stooq_apikey
        url = f"{STOOQ_BASE}?{urllib.parse.urlencode(params)}"
        payload = _http_get(url, retries=retries, user_agent=user_agent)
        rows = _parse_stooq_csv(payload)
        if not rows:
            return None
        return _series_payload(
            record=record,
            source="stooq",
            source_symbol=symbol,
            rows=rows,
            lookback=lookback,
        )

    if source == "yfinance":
        symbol = _yahoo_symbol(record)
        if not symbol:
            return None
        try:
            import yfinance  # type: ignore
        except ImportError as exc:
            raise SystemExit(
                "--source yfinance requires the yfinance package. "
                "Install it with: pip install yfinance"
            ) from exc
        ticker = yfinance.Ticker(symbol)
        df = ticker.history(
            period=lookback.yfinance_period(),
            interval="1d",
            auto_adjust=False,
        )
        if df is None or df.empty:
            return None
        rows: list[tuple[int, float, float, float, float, int]] = []
        for index, row in df.iterrows():
            try:
                day = int(index.strftime("%Y%m%d"))  # type: ignore[union-attr]
                rows.append(
                    (
                        day,
                        float(row["Open"]),
                        float(row["High"]),
                        float(row["Low"]),
                        float(row["Close"]),
                        int(row.get("Volume", 0) or 0),
                    )
                )
            except (KeyError, ValueError, TypeError):
                continue
        if not rows:
            return None
        rows.sort(key=lambda r: r[0])
        return _series_payload(
            record=record,
            source="yahoo",
            source_symbol=symbol,
            rows=rows,
            lookback=lookback,
        )

    raise SystemExit(f"unknown source: {source!r} (expected 'yahoo', 'yfinance', or 'stooq')")


def main(argv: Optional[Iterable[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Fetch 5y daily OHLCV for US listings.")
    parser.add_argument(
        "--exchange",
        default=",".join(sorted(US_EXCHANGES)),
        help="Comma-separated US exchanges to include.",
    )
    parser.add_argument(
        "--tickers",
        default=None,
        help="Comma-separated list of explicit catalog ids or symbols (overrides --exchange).",
    )
    parser.add_argument("--limit", type=int, default=None, help="Stop after N tickers.")
    parser.add_argument("--skip", type=int, default=0, help="Skip the first N tickers.")
    parser.add_argument(
        "--lookback",
        default=os.environ.get("HISTORY_LOOKBACK", DEFAULT_LOOKBACK),
        help=(
            "How far back to fetch: 'max' (default, full available history), "
            "'<N>y' (e.g. '5y'), '<N>d' (days), or a bare integer year count."
        ),
    )
    parser.add_argument(
        "--lookback-years",
        type=int,
        default=None,
        help="DEPRECATED. Equivalent to --lookback <N>y. Kept for back-compat.",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=DEFAULT_DELAY_SECONDS,
        help="Seconds to sleep between requests (politeness).",
    )
    parser.add_argument(
        "--max-age-days",
        type=int,
        default=DEFAULT_MAX_AGE_DAYS,
        help="Skip a ticker if its file is younger than this many days.",
    )
    parser.add_argument("--retries", type=int, default=DEFAULT_RETRIES)
    parser.add_argument("--user-agent", default=DEFAULT_USER_AGENT)
    parser.add_argument(
        "--source",
        choices=["yahoo", "yfinance", "stooq"],
        default=os.environ.get("HISTORY_SOURCE", "yahoo"),
        help=(
            "Upstream EOD source. Default: yahoo (keyless v8 chart endpoint). "
            "Use 'yfinance' for the Python package (handles Yahoo crumbs, much fewer 429s). "
            "Use 'stooq' if you have a Stooq API key (--apikey or STOOQ_APIKEY)."
        ),
    )
    parser.add_argument(
        "--apikey",
        default=os.environ.get("STOOQ_APIKEY"),
        help="Stooq API key (only needed when --source stooq).",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-fetch even when an existing file is still fresh.",
    )
    args = parser.parse_args(argv)

    if not CATALOG_JSON.exists():
        print(f"catalog.json not found at {CATALOG_JSON}; run prepare:data first.", file=sys.stderr)
        return 1

    SERIES_DIR.mkdir(parents=True, exist_ok=True)

    exchanges = {ex.strip().upper() for ex in args.exchange.split(",") if ex.strip()}
    tickers: Optional[set[str]] = None
    if args.tickers:
        tickers = {t.strip() for t in args.tickers.split(",") if t.strip()}

    raw_lookback = args.lookback
    if args.lookback_years is not None:
        raw_lookback = f"{args.lookback_years}y"
    lookback = Lookback(raw_lookback)

    records = json.loads(CATALOG_JSON.read_text(encoding="utf-8"))
    queue = _filter_records(records, exchanges=exchanges, tickers=tickers, skip=args.skip, limit=args.limit)
    if not queue:
        print("No tickers matched the filter.", file=sys.stderr)
        return 2

    print(
        f"Targeting {len(queue)} listings; "
        f"lookback={'max' if lookback.is_max else lookback}, source={args.source}, delay={args.delay}s"
    )

    fetched = skipped_fresh = empty = errors = 0
    for index, record in enumerate(queue, start=1):
        ticker = str(record["id"])
        out_path = SERIES_DIR / _patch_filename(ticker)
        if out_path.exists() and not args.force and _is_fresh(out_path, args.max_age_days):
            skipped_fresh += 1
            continue

        try:
            payload = fetch_one(
                record,
                lookback=lookback,
                user_agent=args.user_agent,
                retries=args.retries,
                source=args.source,
                stooq_apikey=args.apikey,
            )
        except Exception as exc:  # noqa: BLE001
            errors += 1
            print(f"  [{index}/{len(queue)}] {ticker}: ERROR {exc}", file=sys.stderr)
            time.sleep(args.delay)
            continue

        if not payload:
            empty += 1
            print(f"  [{index}/{len(queue)}] {ticker}: no data from {args.source}", file=sys.stderr)
        else:
            out_path.write_text(
                json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
                encoding="utf-8",
            )
            fetched += 1
            span_years = (int(payload["rangeEnd"]) // 10000) - (int(payload["rangeStart"]) // 10000)
            print(
                f"  [{index}/{len(queue)}] {ticker}: rows={payload['rows']:>5} "
                f"range={payload['rangeStart']}..{payload['rangeEnd']} (~{span_years}y)"
            )
        time.sleep(args.delay)

    print(
        f"Done. fetched={fetched} skipped_fresh={skipped_fresh} empty={empty} errors={errors}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
