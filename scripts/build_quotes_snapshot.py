#!/usr/bin/env python3
"""Build public/data/quotes/latest.json from Yahoo via yfinance (US catalog symbols)."""

from __future__ import annotations

import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CATALOG = ROOT / "public" / "data" / "catalog.json"
QUOTES_DIR = ROOT / "public" / "data" / "quotes"
LATEST = QUOTES_DIR / "latest.json"

US_EXCHANGES = {"NASDAQ", "NYSE", "NYSEARCA", "NYSEMKT", "AMEX", "BATS", "OTC", "OTCBB", "CBOE"}


def _select_symbols(catalog: list[dict], *, limit: int | None, exchange: str | None) -> list[tuple[str, str]]:
    ex_filter = {exchange.upper()} if exchange else US_EXCHANGES
    out: list[tuple[str, str]] = []
    for row in catalog:
        sym = str(row.get("sy") or "").strip().upper()
        ex = str(row.get("ex") or "").strip().upper()
        cid = str(row.get("id") or sym)
        if not sym or ":" in sym or len(sym) > 12:
            continue
        if ex not in ex_filter and row.get("co") != "United States":
            continue
        out.append((cid, sym))
        if limit and len(out) >= limit:
            break
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description="Build latest quote snapshot for listing quick view.")
    parser.add_argument("--limit", type=int, default=500, help="Max symbols (default 500)")
    parser.add_argument("--exchange", default=None, help="Single exchange filter")
    parser.add_argument("--batch", type=int, default=50, help="yfinance batch size")
    parser.add_argument("--delay", type=float, default=0.5)
    args = parser.parse_args()

    try:
        import yfinance as yf
    except ImportError:
        print("Install yfinance: pip install yfinance", flush=True)
        return 1

    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    pairs = _select_symbols(catalog, limit=args.limit, exchange=args.exchange)
    if not pairs:
        print("No symbols matched.")
        return 2

    symbols: dict[str, dict] = {}
    for index, (_cid, sym) in enumerate(pairs, start=1):
        try:
            frame = yf.Ticker(sym).history(period="5d", interval="1d", auto_adjust=False)
            if frame is None or frame.empty:
                continue
            last = frame.iloc[-1]
            prev = frame.iloc[-2] if len(frame) > 1 else last
            price = float(last["Close"])
            prev_close = float(prev["Close"])
            day_open = float(last["Open"])
            change = ((price / prev_close) - 1) * 100 if prev_close else 0
            symbols[sym] = {
                "price": price,
                "dayOpen": day_open,
                "previousClose": prev_close,
                "changePct": change,
                "sessionDate": str(frame.index[-1].date()),
                "shortName": sym,
                "ingestSource": "yfinance",
            }
        except Exception as exc:
            print(f"  [{index}/{len(pairs)}] {sym}: {exc}", flush=True)
        if index % 25 == 0:
            print(f"  … {index}/{len(pairs)} ({len(symbols)} quotes)", flush=True)
        time.sleep(args.delay)

    now = datetime.now(tz=timezone.utc)
    payload = {
        "version": 1,
        "asOf": now.strftime("%Y-%m-%d"),
        "builtAt": now.isoformat().replace("+00:00", "Z"),
        "symbolCount": len(symbols),
        "ingestNotes": "Built by scripts/build_quotes_snapshot.py. Not for trading.",
        "symbols": symbols,
    }
    QUOTES_DIR.mkdir(parents=True, exist_ok=True)
    LATEST.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(symbols)} quotes to {LATEST}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
