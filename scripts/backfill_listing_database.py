#!/usr/bin/env python3
"""Batch backfill listing completeness: catalog, history, health shards, quotes, enrichment.

Full US universe (~16k listings) at 0.25s/ticker history ≈ 70+ minutes per pass.
Run in batches with --limit and --resume; repeat until coverage targets are met.

Examples:
  python3 scripts/backfill_listing_database.py --phase normalize
  python3 scripts/backfill_listing_database.py --phase history --exchange NASDAQ --limit 200
  python3 scripts/backfill_listing_database.py --phase quotes --limit 1000
  python3 scripts/backfill_listing_database.py --phase enrichment --exchange NASDAQ --limit 100
  python3 scripts/backfill_listing_database.py --phase prepare
  python3 scripts/backfill_listing_database.py --phase all --exchange NASDAQ,NYSE --limit 500
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STATE = ROOT / "public" / "data" / "backfill-state.json"
CATALOG = ROOT / "public" / "data" / "catalog.json"
HISTORY_DIR = ROOT / "public" / "data" / "history" / "series" / "v1"
HEALTH_MANIFEST = ROOT / "public" / "data" / "health" / "manifest.json"


def _run(cmd: list[str]) -> None:
    print("+", " ".join(cmd), flush=True)
    subprocess.run(cmd, cwd=ROOT, check=True)


def _coverage_report() -> dict:
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    history_files = set(p.stem for p in HISTORY_DIR.glob("*.json")) if HISTORY_DIR.exists() else set()
    with_history = sum(1 for r in catalog if str(r.get("id", "")).replace(":", "-") in history_files or str(r.get("id")) in history_files)
    ic_complete = sum(1 for r in catalog if r.get("ic") == "complete")
    fc_complete = sum(1 for r in catalog if r.get("fc") == "complete")
    quotes = ROOT / "public" / "data" / "quotes" / "latest.json"
    quote_n = 0
    if quotes.exists():
        quote_n = int(json.loads(quotes.read_text()).get("symbolCount") or 0)
    patch_n = 0
    if HEALTH_MANIFEST.exists():
        patch_n = int(json.loads(HEALTH_MANIFEST.read_text()).get("patchCount") or 0)
    return {
        "catalog": len(catalog),
        "withHistory": with_history,
        "icComplete": ic_complete,
        "fcComplete": fc_complete,
        "quotes": quote_n,
        "patches": patch_n,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Backfill full listing database completeness.")
    parser.add_argument(
        "--phase",
        choices=["normalize", "history", "quotes", "enrichment", "prepare", "report", "all"],
        default="report",
    )
    parser.add_argument("--exchange", default="NASDAQ,NYSE,NYSEARCA,NYSEMKT,AMEX")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--delay", type=float, default=0.25)
    parser.add_argument("--source", default="yfinance", choices=["yahoo", "yfinance", "stooq"])
    parser.add_argument("--skip", type=int, default=0)
    parser.add_argument("--force-history", action="store_true")
    args = parser.parse_args()

    if args.phase == "report":
        stats = _coverage_report()
        print(json.dumps(stats, indent=2))
        return 0

    if args.phase in ("normalize", "all"):
        _run([sys.executable, "scripts/normalize_catalog_completeness.py"])

    if args.phase in ("history", "all"):
        cmd = [
            sys.executable,
            "scripts/fetch_us_history.py",
            "--exchange",
            args.exchange,
            "--source",
            args.source,
            "--delay",
            str(args.delay),
            "--lookback",
            "max",
        ]
        if args.limit:
            cmd.extend(["--limit", str(args.limit)])
        if args.skip:
            cmd.extend(["--skip", str(args.skip)])
        if args.force_history:
            cmd.append("--force")
        _run(cmd)
        _run([sys.executable, "scripts/build_history_manifest.py"])

    if args.phase in ("quotes", "all"):
        cmd = [sys.executable, "scripts/build_quotes_snapshot.py"]
        if args.limit:
            cmd.extend(["--limit", str(args.limit)])
        _run(cmd)

    if args.phase in ("enrichment", "all"):
        cmd = [
            sys.executable,
            "scripts/collect_listing_profiles.py",
            "--exchange",
            args.exchange.split(",")[0],
            "--delay",
            str(max(args.delay, 0.2)),
        ]
        if args.limit:
            cmd.extend(["--limit", str(min(args.limit, 200))])
        _run(cmd)

    if args.phase in ("prepare", "all"):
        _run([sys.executable, "scripts/build_catalog_data.py"])
        _run([sys.executable, "scripts/build_health_shards.py"])
        _run([sys.executable, "scripts/build_history_manifest.py"])

    stats = _coverage_report()
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps({"lastRun": stats}, indent=2) + "\n", encoding="utf-8")
    print("Coverage:", json.dumps(stats))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
