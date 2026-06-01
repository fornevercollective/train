#!/usr/bin/env python3
"""Smoke-test listing charts (ECharts line + calendar + flowGL) and snowflake coverage.

Mirrors the verified AAPL history workflow:
  1. Seed a ~25y synthetic daily CSV (no real prices shipped).
  2. Import into public/data/history/series/v1/AAPL.json.
  3. Promote a demo snowflake patch with mixed pass/fail/na states.
  4. Rebuild history + health manifests.

Cleanup removes the synthetic series and resets the AAPL patch so the repo
does not ship fake OHLCV.

Usage:
  python3 scripts/smoke_listing_viz.py --apply
  python3 scripts/smoke_listing_viz.py --apply --verify
  python3 scripts/smoke_listing_viz.py --cleanup
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import random
import subprocess
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FIXTURES = ROOT / "scripts" / "fixtures"
SMOKE_CSV = FIXTURES / "smoke_aapl_25y.csv"
SERIES_PATH = ROOT / "public" / "data" / "history" / "series" / "v1" / "AAPL.json"
PATCH_PATH = ROOT / "public" / "data" / "health" / "patches" / "v1" / "AAPL.json"
CLEAN_PATCH_BACKUP = FIXTURES / "aapl_patch_na_only.json"


def _write_synthetic_csv(path: Path, *, seed: int = 42) -> int:
    """~25 calendar years of trading days ending today."""
    path.parent.mkdir(parents=True, exist_ok=True)
    rng = random.Random(seed)
    end = date.today()
    start = date(2001, 5, 8)
    price = 1.25
    rows: list[tuple[str, float, float, float, float, int]] = []
    d = start
    while d <= end:
        if d.weekday() < 5:
            drift = rng.gauss(0.0004, 0.012)
            price = max(0.05, price * math.exp(drift))
            o = price * (1 + rng.uniform(-0.004, 0.004))
            c = price
            h = max(o, c) * (1 + rng.uniform(0, 0.008))
            low = min(o, c) * (1 - rng.uniform(0, 0.008))
            vol = int(8_000_000 + rng.random() * 40_000_000)
            rows.append((d.isoformat(), round(o, 4), round(h, 4), round(low, 4), round(c, 4), vol))
        d += timedelta(days=1)

    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["Date", "Open", "High", "Low", "Close", "Volume"])
        writer.writerows(rows)
    return len(rows)


def _demo_snowflake_patch() -> dict:
    now = datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    def axis(name: str, label: str, checks: list[tuple[str, str, str, str]]) -> dict:
        passed = sum(1 for *_, state in checks if state == "pass")
        total = len(checks)
        return {
            "name": name,
            "label": label,
            "passed": passed,
            "total": total,
            "scoreLabel": f"{passed}/{total}",
            "checks": [
                {"id": cid, "label": clabel, "detail": detail, "state": state}
                for cid, clabel, detail, state in checks
            ],
        }

    return {
        "schemaVersion": 1,
        "ticker": "AAPL",
        "displayName": "Apple Inc",
        "asOfISO": now,
        "sourceNotes": [
            "Smoke test overlay (scripts/smoke_listing_viz.py)",
            "Mixed pass/fail/na for ECharts snowflake radar verification.",
        ],
        "axes": [
            axis(
                "value",
                "Value",
                [
                    ("price-vs-fair", "Trading below estimated fair value", "Smoke: pass", "pass"),
                    ("price-vs-peers", "Price-to-earnings vs peers", "Smoke: fail", "fail"),
                ],
            ),
            axis(
                "future",
                "Future",
                [
                    ("eps-growth-fwd", "Forecast EPS growth above market", "Smoke: pass", "pass"),
                    ("revenue-growth-fwd", "Forecast revenue growth above market", "Smoke: pass", "pass"),
                    ("roe-forecast", "Forecast return on equity", "Smoke: na", "na"),
                ],
            ),
            axis(
                "past",
                "Past",
                [
                    ("eps-growth-5y", "EPS growth over the past 5 years", "Smoke: pass", "pass"),
                    ("revenue-growth-5y", "Revenue growth over the past 5 years", "Smoke: fail", "fail"),
                    ("eps-acceleration-1y", "EPS growth accelerating last 12 months", "Smoke: pass", "pass"),
                ],
            ),
            axis(
                "health",
                "Health",
                [
                    ("debt-to-equity", "Debt-to-equity ratio in safe range", "Smoke: pass", "pass"),
                    ("operating-cashflow", "Operating cashflow covers debt", "Smoke: pass", "pass"),
                    ("interest-coverage", "Interest coverage ratio healthy", "Smoke: fail", "fail"),
                ],
            ),
            axis(
                "dividends",
                "Dividends",
                [
                    ("dividend-yield", "Dividend yield is above market average", "Smoke: fail", "fail"),
                    ("payout-ratio", "Payout ratio is sustainable", "Smoke: na", "na"),
                    ("dividend-growth", "Dividend growth is positive", "Smoke: pass", "pass"),
                ],
            ),
        ],
    }


def _run(cmd: list[str]) -> None:
    print("+", " ".join(cmd))
    subprocess.run(cmd, cwd=ROOT, check=True)


def apply(*, verify: bool) -> int:
    row_count = _write_synthetic_csv(SMOKE_CSV)
    print(f"Wrote {row_count} synthetic rows to {SMOKE_CSV}")

    _run(
        [
            sys.executable,
            "scripts/import_history_csv.py",
            "--ticker",
            "AAPL",
            "--lookback",
            "max",
            "--source",
            "smoke_test",
            str(SMOKE_CSV),
        ]
    )
    _run([sys.executable, "scripts/build_history_manifest.py"])

    PATCH_PATH.parent.mkdir(parents=True, exist_ok=True)
    PATCH_PATH.write_text(
        json.dumps(_demo_snowflake_patch(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote demo snowflake patch to {PATCH_PATH}")

    _run([sys.executable, "scripts/build_health_shards.py"])

    if SERIES_PATH.exists():
        series = json.loads(SERIES_PATH.read_text(encoding="utf-8"))
        manifest = json.loads(
            (ROOT / "public" / "data" / "history" / "manifest.json").read_text(encoding="utf-8")
        )
        entry = next((e for e in manifest.get("entries", []) if e.get("ticker") == "AAPL"), None)
        print(
            f"AAPL series: rows={series.get('rows')} "
            f"range={series.get('rangeStart')}..{series.get('rangeEnd')} "
            f"lookbackYears={series.get('lookbackYears')} lookbackMode={series.get('lookbackMode')}"
        )
        if entry:
            print(
                f"Manifest entry: rows={entry.get('rows')} "
                f"lookback via manifest lookbackYears={manifest.get('lookbackYears')} "
                f"lookbackMode={manifest.get('lookbackMode')}"
            )

    if verify:
        _run(["npm", "run", "check"])
        _run(["npm", "run", "build"])
        print("Smoke verify: check + build OK")

    print("Open /listing/?id=AAPL to view line, calendar, flowGL, and snowflake radar.")
    return 0


def cleanup() -> int:
    removed: list[str] = []
    if SERIES_PATH.exists():
        SERIES_PATH.unlink()
        removed.append(str(SERIES_PATH))
    if SMOKE_CSV.exists():
        SMOKE_CSV.unlink()
        removed.append(str(SMOKE_CSV))

    if CLEAN_PATCH_BACKUP.exists():
        PATCH_PATH.write_text(CLEAN_PATCH_BACKUP.read_text(encoding="utf-8"), encoding="utf-8")
        removed.append(f"restored {PATCH_PATH.name} from fixture backup")
    elif PATCH_PATH.exists():
        PATCH_PATH.unlink()
        removed.append(str(PATCH_PATH))

    _run([sys.executable, "scripts/build_history_manifest.py"])
    _run([sys.executable, "scripts/build_health_shards.py"])

    manifest = json.loads(
        (ROOT / "public" / "data" / "history" / "manifest.json").read_text(encoding="utf-8")
    )
    print(f"History manifest entries: {manifest.get('tickerCount', 0)}")
    if removed:
        print("Removed / restored:")
        for line in removed:
            print(f"  - {line}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Smoke-test listing ECharts + snowflake.")
    parser.add_argument("--apply", action="store_true", help="Seed synthetic AAPL data + demo patch.")
    parser.add_argument("--cleanup", action="store_true", help="Remove synthetic history; restore patch.")
    parser.add_argument("--verify", action="store_true", help="With --apply, run npm run check && build.")
    args = parser.parse_args()

    if args.cleanup and args.apply:
        parser.error("Use --apply or --cleanup, not both.")
    if not args.cleanup and not args.apply:
        parser.error("Pass --apply or --cleanup.")
    if args.cleanup:
        return cleanup()
    return apply(verify=args.verify)


if __name__ == "__main__":
    raise SystemExit(main())
