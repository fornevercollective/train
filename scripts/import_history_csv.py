"""Import OHLCV CSV files into the per-ticker history series store.

This is the manual-seed path. It accepts CSVs from any source (Stooq with API key,
Yahoo's "Historical Data" download, Polygon, Tiingo, your own data lake) as long
as they have a Date column and OHLCV columns. The script is forgiving about column
names: it tries common variants and falls back to positional ordering.

Usage:

  # One file per ticker (filename is the ticker by default)
  python3 scripts/import_history_csv.py csvs/AAPL.csv csvs/MSFT.csv

  # Override the ticker explicitly when the filename doesn't match
  python3 scripts/import_history_csv.py --ticker AAPL ./apple_eod_5y.csv

  # Glob with shell expansion
  python3 scripts/import_history_csv.py ./csvs/*.csv

Date format auto-detected: YYYY-MM-DD, YYYY/MM/DD, MM/DD/YYYY, YYYYMMDD.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Optional

ROOT = Path(__file__).resolve().parent.parent
CATALOG_JSON = ROOT / "public" / "data" / "catalog.json"
SERIES_DIR = ROOT / "public" / "data" / "history" / "series" / "v1"

DATE_COLUMNS = ("date", "datetime", "timestamp", "day")
OPEN_COLUMNS = ("open", "o")
HIGH_COLUMNS = ("high", "h")
LOW_COLUMNS = ("low", "l")
CLOSE_COLUMNS = ("close", "adj close", "adjusted close", "c")
VOLUME_COLUMNS = ("volume", "vol", "v")


def _detect_columns(header: list[str]) -> dict[str, int]:
    lower = [h.strip().lower() for h in header]
    indices: dict[str, int] = {}
    for key, candidates in (
        ("date", DATE_COLUMNS),
        ("open", OPEN_COLUMNS),
        ("high", HIGH_COLUMNS),
        ("low", LOW_COLUMNS),
        ("close", CLOSE_COLUMNS),
        ("volume", VOLUME_COLUMNS),
    ):
        for candidate in candidates:
            if candidate in lower:
                indices[key] = lower.index(candidate)
                break
    return indices


def _parse_date(raw: str) -> Optional[int]:
    raw = raw.strip().replace("/", "-")
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%m-%d-%Y", "%Y%m%d"):
        try:
            return int(datetime.strptime(raw, fmt).strftime("%Y%m%d"))
        except ValueError:
            continue
    if raw.isdigit() and len(raw) == 8:
        return int(raw)
    return None


def _resolve_ticker(path: Path, override: Optional[str]) -> str:
    if override:
        return override.strip().upper()
    return path.stem.upper()


def _resolve_record(ticker: str, catalog: list[dict[str, object]]) -> Optional[dict[str, object]]:
    for record in catalog:
        if str(record.get("id")) == ticker or str(record.get("sy")) == ticker:
            return record
    return None


def import_csv(
    csv_path: Path,
    *,
    catalog: list[dict[str, object]],
    override_ticker: Optional[str],
    source_label: str,
    lookback_years: int,
    lookback_mode: str,
) -> Optional[Path]:
    ticker = _resolve_ticker(csv_path, override_ticker)
    record = _resolve_record(ticker, catalog) or {"id": ticker, "sy": ticker, "ex": "", "nm": ticker}

    with csv_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.reader(handle)
        header = next(reader, None)
        if not header:
            print(f"  {csv_path}: empty CSV, skipping", file=sys.stderr)
            return None
        cols = _detect_columns(header)
        required = ("date", "open", "high", "low", "close")
        missing = [name for name in required if name not in cols]
        if missing:
            print(
                f"  {csv_path}: header missing column(s) {missing}; got {header!r}",
                file=sys.stderr,
            )
            return None

        rows: list[tuple[int, float, float, float, float, int]] = []
        for raw in reader:
            if not raw:
                continue
            try:
                day = _parse_date(raw[cols["date"]])
                if day is None:
                    continue
                o = float(raw[cols["open"]])
                h = float(raw[cols["high"]])
                low = float(raw[cols["low"]])
                c = float(raw[cols["close"]])
                v = int(float(raw[cols["volume"]])) if "volume" in cols else 0
            except (IndexError, ValueError):
                continue
            rows.append((day, o, h, low, c, v))

    if not rows:
        print(f"  {csv_path}: no usable rows, skipping", file=sys.stderr)
        return None
    rows.sort(key=lambda r: r[0])

    payload = {
        "schemaVersion": 1,
        "ticker": str(record["id"]),
        "exchange": str(record.get("ex") or ""),
        "displayName": str(record.get("nm") or record.get("ln") or record["id"]),
        "source": source_label,
        "sourceSymbol": ticker,
        "interval": "daily",
        "asOfISO": datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "lookbackYears": lookback_years,
        "lookbackMode": lookback_mode,
        "rows": len(rows),
        "rangeStart": rows[0][0],
        "rangeEnd": rows[-1][0],
        "d": [r[0] for r in rows],
        "o": [r[1] for r in rows],
        "h": [r[2] for r in rows],
        "l": [r[3] for r in rows],
        "c": [r[4] for r in rows],
        "v": [r[5] for r in rows],
    }

    SERIES_DIR.mkdir(parents=True, exist_ok=True)
    out_path = SERIES_DIR / f"{ticker}.json"
    out_path.write_text(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    print(f"  {csv_path} -> {out_path} ({len(rows)} rows, {rows[0][0]}..{rows[-1][0]})")
    return out_path


def main(argv: Optional[Iterable[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Import OHLCV CSV files into the history store.")
    parser.add_argument("csv_paths", nargs="+", help="One or more CSV files (or globs).")
    parser.add_argument("--ticker", default=None, help="Override ticker (only valid with one file).")
    parser.add_argument(
        "--source",
        default="manual",
        help="Source label written into the JSON (e.g. 'yahoo', 'stooq', 'polygon').",
    )
    parser.add_argument(
        "--lookback",
        default="max",
        help=(
            "How far back this CSV represents: 'max' (default, full available history) "
            "or '<N>y'. Used for metadata only; the actual rangeStart/rangeEnd come "
            "from the CSV itself."
        ),
    )
    parser.add_argument(
        "--lookback-years",
        type=int,
        default=None,
        help="DEPRECATED. Equivalent to --lookback <N>y.",
    )
    args = parser.parse_args(argv)

    if args.ticker and len(args.csv_paths) != 1:
        parser.error("--ticker can only be used with a single CSV path.")

    if not CATALOG_JSON.exists():
        print(f"catalog.json not found at {CATALOG_JSON}; run prepare:data first.", file=sys.stderr)
        return 1
    catalog = json.loads(CATALOG_JSON.read_text(encoding="utf-8"))

    raw_lookback = args.lookback
    if args.lookback_years is not None:
        raw_lookback = f"{args.lookback_years}y"
    raw_lookback = str(raw_lookback).strip().lower()
    if raw_lookback in ("max", "all", "full", "0"):
        lookback_years = 0
        lookback_mode = "max"
    else:
        token = raw_lookback[:-1] if raw_lookback.endswith(("y", "d")) else raw_lookback
        try:
            value = float(token)
        except ValueError as exc:
            raise SystemExit(f"Invalid --lookback {args.lookback!r}") from exc
        lookback_years = int(value if not raw_lookback.endswith("d") else value / 365.25)
        lookback_mode = "fixed"

    written = 0
    for path_str in args.csv_paths:
        path = Path(path_str)
        if not path.is_file():
            print(f"  {path}: not a file, skipping", file=sys.stderr)
            continue
        out = import_csv(
            path,
            catalog=catalog,
            override_ticker=args.ticker,
            source_label=args.source,
            lookback_years=lookback_years,
            lookback_mode=lookback_mode,
        )
        if out is not None:
            written += 1

    print(f"Imported {written} series file(s).")
    return 0 if written else 1


if __name__ == "__main__":
    raise SystemExit(main())
