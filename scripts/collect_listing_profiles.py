#!/usr/bin/env python3
"""Batch-collect registry enrichment and rebuild catalog for listing profiles.

Fills identity / classification / quick-view fields (ln, lt, ll, lc, hq, hc, fc, ic)
by fetching SEC EDGAR (US) or OpenRegistry (supported non-US), then merging into catalog.

Examples:
  python3 scripts/collect_listing_profiles.py --exchange NASDAQ --limit 100 --delay 0.25
  python3 scripts/collect_listing_profiles.py --tickers TSLA,AAPL,MSFT --delay 0.2
  python3 scripts/collect_listing_profiles.py --resume --exchange NYSE --limit 500
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CATALOG = ROOT / "public" / "data" / "catalog.json"
STATE_PATH = ROOT / "public" / "data" / "enrichment" / "collect-state.json"
FETCH = ROOT / "scripts" / "fetch_registry_enrichment.py"
BUILD_ATTR = ROOT / "scripts" / "build_attribution_enrichment.py"
BUILD_CATALOG = ROOT / "scripts" / "build_catalog_data.py"

US_EXCHANGES = {"NASDAQ", "NYSE", "NYSEARCA", "NYSEMKT", "AMEX", "BATS", "OTC", "OTCBB"}


def _load_catalog() -> list[dict]:
    return json.loads(CATALOG.read_text(encoding="utf-8"))


def _needs_enrichment(row: dict) -> bool:
    if row.get("fc") == "complete" and row.get("ic") in ("complete", "partial"):
        if row.get("ln") and (row.get("lt") or row.get("cd")):
            return False
    if row.get("ln") and row.get("lt") and row.get("ll"):
        return False
    return True


def _select_tickers(
    catalog: list[dict],
    *,
    exchange: str | None,
    tickers: list[str] | None,
    limit: int,
    us_only: bool,
    missing_only: bool,
) -> list[str]:
    if tickers:
        return [t.strip().upper() for t in tickers if t.strip()][:limit]

    out: list[str] = []
    for row in catalog:
        sym = str(row.get("sy") or row.get("id") or "").strip().upper()
        if not sym or ":" in sym:
            continue
        ex = str(row.get("ex") or "").strip().upper()
        if exchange and ex != exchange.upper():
            continue
        if us_only and ex not in US_EXCHANGES and row.get("co") != "United States":
            continue
        if missing_only and not _needs_enrichment(row):
            continue
        out.append(sym)
        if len(out) >= limit:
            break
    return out


def _load_state() -> set[str]:
    if not STATE_PATH.exists():
        return set()
    try:
        data = json.loads(STATE_PATH.read_text(encoding="utf-8"))
        return set(data.get("done", []))
    except json.JSONDecodeError:
        return set()


def _save_state(done: set[str]) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(
        json.dumps({"done": sorted(done)}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Batch collect listing profile enrichment.")
    parser.add_argument("--exchange", help="Filter catalog by exchange (e.g. NASDAQ)")
    parser.add_argument("--tickers", help="Comma-separated tickers")
    parser.add_argument("--limit", type=int, default=50, help="Max tickers this run")
    parser.add_argument("--delay", type=float, default=0.25, help="SEC/OpenRegistry delay seconds")
    parser.add_argument("--us-only", action="store_true", default=True)
    parser.add_argument("--missing-only", action="store_true", default=True)
    parser.add_argument("--resume", action="store_true", help="Skip tickers in collect-state.json")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    catalog = _load_catalog()
    tickers = _select_tickers(
        catalog,
        exchange=args.exchange,
        tickers=[t.strip() for t in args.tickers.split(",")] if args.tickers else None,
        limit=args.limit,
        us_only=args.us_only,
        missing_only=args.missing_only,
    )

    done = _load_state() if args.resume else set()
    pending = [t for t in tickers if t not in done]
    print(f"Selected {len(tickers)} tickers; {len(pending)} to fetch after resume filter.")

    if args.dry_run:
        print("Dry run:", ", ".join(pending[:20]), ("…" if len(pending) > 20 else ""))
        return 0

    if not pending:
        print("Nothing to fetch.")
        return 0

    batch = ",".join(pending)
    subprocess.run(
        [
            sys.executable,
            str(FETCH),
            "--tickers",
            batch,
            "--delay",
            str(args.delay),
        ],
        cwd=ROOT,
        check=True,
    )
    subprocess.run([sys.executable, str(BUILD_ATTR)], cwd=ROOT, check=True)
    subprocess.run([sys.executable, str(BUILD_CATALOG)], cwd=ROOT, check=True)

    done.update(pending)
    _save_state(done)
    print(f"Done. {len(done)} tickers recorded in {STATE_PATH.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
