#!/usr/bin/env python3
"""
Stub fundamentals → snowflake JSON pipeline (dividend axis placeholder).

Later: ingest FMP / EDGAR per ticker, fill checks, write to public/data/health/ or API bucket.

Usage:
  python3 scripts/snowflake_pipeline_stub.py --ticker NASDAQ:TSLA --out /tmp/tsla-snowflake.json
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


def axis(name: str, label: str, passed: int, total: int, checks: list[dict]) -> dict:
    pct = int(100 * passed / total) if total else 0
    return {
        "name": name,
        "label": label,
        "scoreLabel": f"{passed}/{total} ({pct}%)",
        "passed": passed,
        "total": total,
        "checks": checks,
    }


def build_stub(ticker: str) -> dict:
    now = datetime.now(timezone.utc).isoformat()
    return {
        "schemaVersion": 1,
        "ticker": ticker,
        "asOfISO": now,
        "sourceNotes": [
            "stub: wire FMP key + EDGAR CIK mapping for real scores",
            "dividends: implement from cash-dividend history or EDGAR events",
        ],
        "axes": [
            axis(
                "value",
                "Value",
                0,
                6,
                [
                    {
                        "id": "stub",
                        "label": "Fundamentals pipeline",
                        "detail": "Not run — placeholder only",
                        "state": "na",
                    }
                ],
            ),
            axis("future", "Future", 0, 6, []),
            axis("past", "Past", 0, 6, []),
            axis("health", "Health", 0, 6, []),
            axis(
                "dividends",
                "Dividends",
                0,
                6,
                [
                    {
                        "id": "div-pending",
                        "label": "Dividend data present",
                        "detail": "Not implemented in stub",
                        "state": "fail",
                    }
                ],
            ),
        ],
    }


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--ticker", required=True, help="e.g. NASDAQ:TSLA")
    p.add_argument("--out", required=True, help="output JSON path")
    args = p.parse_args()
    payload = build_stub(args.ticker)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
