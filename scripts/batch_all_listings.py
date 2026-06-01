#!/usr/bin/env python3
"""Run full-database listing backfill (US history, quotes, enrichment, rebuild).

Designed for long runs. Logs to logs/database-backfill.log. Resumes via:
  - fetch_us_history skipping fresh series files (--max-age-days)
  - collect_listing_profiles collect-state.json
  - optional --start-phase to skip completed stages

Usage:
  python3 scripts/batch_all_listings.py
  python3 scripts/batch_all_listings.py --history-only
  nohup python3 scripts/batch_all_listings.py >> logs/database-backfill.log 2>&1 &
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VENV_PY = ROOT / ".venv" / "bin" / "python3"
LOG_DIR = ROOT / "logs"
LOG_FILE = LOG_DIR / "database-backfill.log"
US_EXCHANGES = "NASDAQ,NYSE,NYSEARCA,NYSEMKT,AMEX,BATS,CBOE,OTC,OTCBB"


def log(msg: str) -> None:
    line = f"[{datetime.now(tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S')}] {msg}"
    print(line, flush=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    with LOG_FILE.open("a", encoding="utf-8") as handle:
        handle.write(line + "\n")


def run(cmd: list[str], *, optional: bool = False) -> int:
    log("+ " + " ".join(cmd))
    proc = subprocess.run(cmd, cwd=ROOT)
    if proc.returncode != 0 and not optional:
        log(f"FAILED exit {proc.returncode}: {' '.join(cmd)}")
        return proc.returncode
    return proc.returncode


def report() -> dict:
    proc = subprocess.run(
        [sys.executable, "scripts/backfill_listing_database.py", "--phase", "report"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError:
        return {"raw": proc.stdout}


def main() -> int:
    parser = argparse.ArgumentParser(description="Batch all listing backfill stages.")
    parser.add_argument("--history-only", action="store_true")
    parser.add_argument("--skip-normalize", action="store_true")
    parser.add_argument(
        "--history-delay",
        type=float,
        default=float(os.environ.get("HISTORY_DELAY", "1.0")),
        help="Seconds between tickers (default 1.0; yahoo needs higher)",
    )
    parser.add_argument(
        "--history-source",
        default=os.environ.get("HISTORY_SOURCE", "yfinance"),
        choices=["yahoo", "yfinance", "stooq"],
    )
    parser.add_argument("--history-max-age", type=int, default=7)
    parser.add_argument("--quote-limit", type=int, default=0, help="0 = all US symbols")
    parser.add_argument("--enrichment-limit", type=int, default=500, help="Per enrichment pass; 0=skip")
    parser.add_argument("--enrichment-passes", type=int, default=40, help="Max SEC batch passes")
    args = parser.parse_args()

    py = str(VENV_PY) if VENV_PY.is_file() else sys.executable
    log(f"python: {py}")
    log("=== batch_all_listings start ===")
    log(f"coverage before: {json.dumps(report())}")

    if not args.skip_normalize:
        run([py, "scripts/normalize_catalog_completeness.py"])

    # US OHLCV — resumable (skips fresh files)
    rc = run(
        [
            py,
            "scripts/fetch_us_history.py",
            "--exchange",
            US_EXCHANGES,
            "--source",
            args.history_source,
            "--lookback",
            "max",
            "--delay",
            str(args.history_delay),
            "--max-age-days",
            str(args.history_max_age),
        ]
    )
    if rc != 0:
        log("history fetch ended with errors; continuing to manifest + prepare")
    run([py, "scripts/build_history_manifest.py"])

    if args.history_only:
        log(f"coverage: {json.dumps(report())}")
        return 0

    quote_cmd = [py, "scripts/build_quotes_snapshot.py", "--delay", "0.35"]
    if args.quote_limit > 0:
        quote_cmd.extend(["--limit", str(args.quote_limit)])
    else:
        quote_cmd.extend(["--limit", "25000"])
    run(quote_cmd, optional=True)

    if args.enrichment_limit > 0:
        for pass_num in range(1, args.enrichment_passes + 1):
            log(f"enrichment pass {pass_num}/{args.enrichment_passes}")
            rc = run(
                [
                    py,
                    "scripts/collect_listing_profiles.py",
                    "--exchange",
                    US_EXCHANGES,
                    "--limit",
                    str(args.enrichment_limit),
                    "--delay",
                    "0.25",
                    "--resume",
                ],
                optional=True,
            )
            if rc != 0:
                log("enrichment pass stopped")
                break
            time.sleep(2)

    run([py, "scripts/build_catalog_data.py"])
    run([py, "scripts/build_attribution_enrichment.py"], optional=True)
    run([py, "scripts/build_catalog_data.py"])
    run([py, "scripts/build_health_shards.py"])
    run([py, "scripts/build_history_manifest.py"])

    log(f"coverage after: {json.dumps(report())}")
    log("=== batch_all_listings done ===")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
