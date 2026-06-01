#!/usr/bin/env python3
"""Ensure at least one demo OHLCV series exists for local chart development.

When public/data/history/manifest.json has zero entries, writes compact synthetic
daily series for AAPL and TSLA so listing charts (line, calendar, flowGL) render
during `npm run dev` without committing large fake datasets.

Usage (automatic via npm run dev):
  python3 scripts/ensure_demo_history.py
"""

from __future__ import annotations

import json
import math
import random
import subprocess
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "public" / "data" / "history" / "manifest.json"
SERIES_DIR = ROOT / "public" / "data" / "history" / "series" / "v1"
CATALOG = ROOT / "public" / "data" / "catalog.json"

DEMO_TICKERS = ("AAPL", "TSLA")
PATCHES_DIR = ROOT / "public" / "data" / "health" / "patches" / "v1"


def _demo_snowflake_patch(ticker: str, display_name: str) -> dict:
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
        "ticker": ticker,
        "displayName": display_name,
        "asOfISO": now,
        "sourceNotes": ["Demo overlay for local dev (ensure_demo_history.py)"],
        "axes": [
            axis(
                "value",
                "Value",
                [
                    ("price-vs-fair", "Trading below estimated fair value", "Demo pass", "pass"),
                    ("price-vs-peers", "Price-to-earnings vs peers", "Demo fail", "fail"),
                ],
            ),
            axis(
                "future",
                "Future",
                [
                    ("eps-growth-fwd", "Forecast EPS growth above market", "Demo pass", "pass"),
                    ("revenue-growth-fwd", "Forecast revenue growth above market", "Demo pass", "pass"),
                    ("roe-forecast", "Forecast return on equity", "Demo na", "na"),
                ],
            ),
            axis(
                "past",
                "Past",
                [
                    ("eps-growth-5y", "EPS growth over the past 5 years", "Demo pass", "pass"),
                    ("revenue-growth-5y", "Revenue growth over the past 5 years", "Demo fail", "fail"),
                    ("eps-acceleration-1y", "EPS growth accelerating last 12 months", "Demo pass", "pass"),
                ],
            ),
            axis(
                "health",
                "Health",
                [
                    ("debt-to-equity", "Debt-to-equity ratio in safe range", "Demo pass", "pass"),
                    ("operating-cashflow", "Operating cashflow covers debt", "Demo pass", "pass"),
                    ("interest-coverage", "Interest coverage ratio healthy", "Demo fail", "fail"),
                ],
            ),
            axis(
                "dividends",
                "Dividends",
                [
                    ("dividend-yield", "Dividend yield is above market average", "Demo fail", "fail"),
                    ("payout-ratio", "Payout ratio is sustainable", "Demo na", "na"),
                    ("dividend-growth", "Dividend growth is positive", "Demo pass", "pass"),
                ],
            ),
        ],
    }


def _ensure_demo_snowflake_patches() -> None:
    PATCHES_DIR.mkdir(parents=True, exist_ok=True)
    names = {"AAPL": "Apple Inc", "TSLA": "Tesla, Inc."}
    wrote = False
    for ticker, display in names.items():
        path = PATCHES_DIR / f"{ticker}.json"
        force_demo = False
        if path.exists():
            try:
                existing = json.loads(path.read_text(encoding="utf-8"))
                if existing.get("sourceNotes") and "Demo overlay" in str(
                    existing.get("sourceNotes", [""])[0]
                ):
                    force_demo = True
                elif any(
                    c.get("state") != "na"
                    for ax in existing.get("axes", [])
                    for c in ax.get("checks", [])
                ):
                    continue
            except json.JSONDecodeError:
                pass
        if force_demo:
            path.write_text(
                json.dumps(_demo_snowflake_patch(ticker, display), ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            print(f"Demo snowflake: refreshed patch {path.name}")
            wrote = True
            continue
        path.write_text(
            json.dumps(_demo_snowflake_patch(ticker, display), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(f"Demo snowflake: wrote patch {path.name}")
        wrote = True
    if wrote:
        subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "build_health_shards.py")],
            cwd=ROOT,
            check=True,
        )


def _write_series(ticker: str, *, seed: int, start: date, end: date, base_price: float) -> int:
    rng = random.Random(seed)
    SERIES_DIR.mkdir(parents=True, exist_ok=True)
    price = base_price
    d_list: list[int] = []
    o_list: list[float] = []
    h_list: list[float] = []
    l_list: list[float] = []
    c_list: list[float] = []
    v_list: list[int] = []

    day = start
    while day <= end:
        if day.weekday() < 5:
            drift = rng.gauss(0.00035, 0.011)
            price = max(0.05, price * math.exp(drift))
            o = price * (1 + rng.uniform(-0.003, 0.003))
            c = price
            h = max(o, c) * (1 + rng.uniform(0, 0.006))
            low = min(o, c) * (1 - rng.uniform(0, 0.006))
            vol = int(5_000_000 + rng.random() * 25_000_000)
            key = int(day.strftime("%Y%m%d"))
            d_list.append(key)
            o_list.append(round(o, 4))
            h_list.append(round(h, 4))
            l_list.append(round(low, 4))
            c_list.append(round(c, 4))
            v_list.append(vol)
        day += timedelta(days=1)

    payload = {
        "schemaVersion": 1,
        "ticker": ticker,
        "exchange": "NASDAQ",
        "displayName": ticker,
        "source": "demo_dev",
        "sourceSymbol": ticker,
        "interval": "daily",
        "asOfISO": datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "lookbackYears": 0,
        "lookbackMode": "max",
        "rows": len(d_list),
        "rangeStart": d_list[0],
        "rangeEnd": d_list[-1],
        "d": d_list,
        "o": o_list,
        "h": h_list,
        "l": l_list,
        "c": c_list,
        "v": v_list,
    }
    out = SERIES_DIR / f"{ticker}.json"
    out.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    return len(d_list)


def main() -> int:
    end = date.today()
    start = date(end.year - 5, end.month, min(end.day, 28))
    seeds = {"AAPL": (42, 85.0), "TSLA": (7, 220.0)}
    wrote = 0
    for ticker in DEMO_TICKERS:
        series_path = SERIES_DIR / f"{ticker}.json"
        if series_path.exists():
            continue
        seed, base = seeds[ticker]
        rows = _write_series(ticker, seed=seed, start=start, end=end, base_price=base)
        print(f"Demo history: wrote {ticker} ({rows} rows, {start}..{end})")
        wrote += 1

    if wrote:
        subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "build_history_manifest.py")],
            cwd=ROOT,
            check=True,
        )
    elif not any((SERIES_DIR / ticker).exists() for ticker in DEMO_TICKERS):
        print("Demo history: nothing to write.")
    else:
        print("Demo history: AAPL + TSLA series present.")

    _ensure_demo_snowflake_patches()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
