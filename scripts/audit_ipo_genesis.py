#!/usr/bin/env python3
"""
Audit catalog IPO / first-trade genesis (ip, ft) for proxy dates and history drift.

The train catalog is built from erika ticker_checklist.csv (see build_catalog_data.py).
Many rows use Yahoo max-history or listing-date proxies — not exchange first-trade clocks.

Usage:
  python3 scripts/audit_ipo_genesis.py
  python3 scripts/audit_ipo_genesis.py --ticker POET
  python3 scripts/audit_ipo_genesis.py --exchange NASDAQ --limit 50
  python3 scripts/audit_ipo_genesis.py --flag proxy_note --json report.json
  python3 scripts/audit_ipo_genesis.py --compare-history --min-drift-days 30

Exit code: 0 always (reporting tool). Review stdout / --json output.
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
CATALOG_JSON = ROOT / "public" / "data" / "catalog.json"
HISTORY_DIR = ROOT / "public" / "data" / "history" / "series" / "v1"
DEFAULT_ERIKA_CSV = ROOT.parent.parent / "erika" / "artifacts" / "ticker_checklist.csv"

PROXY_NOTE_RE = re.compile(
    r"yahoo|max-history|max history|listing-date proxy|public-market proxy",
    re.I,
)
JAN1_RE = re.compile(r"-01-01T", re.I)


def _iso_to_ymd(iso: str) -> int | None:
    if not iso or not isinstance(iso, str):
        return None
    s = iso.strip()
    if len(s) < 10:
        return None
    try:
        return int(s[:10].replace("-", ""))
    except ValueError:
        return None


def _iso_to_date(iso: str) -> datetime | None:
    ymd = _iso_to_ymd(iso)
    if ymd is None:
        return None
    try:
        return datetime.strptime(str(ymd), "%Y%m%d").replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def _ymd_int_to_date(ymd: int) -> datetime | None:
    try:
        return datetime.strptime(str(ymd), "%Y%m%d").replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def _load_catalog() -> list[dict[str, Any]]:
    if not CATALOG_JSON.is_file():
        raise SystemExit(f"Missing catalog: {CATALOG_JSON}")
    data = json.loads(CATALOG_JSON.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise SystemExit("catalog.json must be a JSON array")
    return data


def _history_range_start(ticker: str) -> int | None:
    path = HISTORY_DIR / f"{ticker}.json"
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    rs = payload.get("rangeStart")
    if rs is None:
        return None
    try:
        return int(rs)
    except (TypeError, ValueError):
        return None


def _flags_for_row(row: dict[str, Any], *, compare_history: bool, min_drift_days: int) -> list[str]:
    flags: list[str] = []
    sy = str(row.get("sy") or row.get("id") or "").strip().upper()
    ip = str(row.get("ip") or "")
    ft = str(row.get("ft") or "")
    cd = str(row.get("cd") or "")
    nt = str(row.get("nt") or "")

    if not ip and not ft:
        flags.append("missing_ip_ft")
    if ip and ft and ip != ft:
        flags.append("ip_ft_mismatch")
    if nt and PROXY_NOTE_RE.search(nt):
        flags.append("proxy_note")
    if (ip and JAN1_RE.search(ip)) or (ft and JAN1_RE.search(ft)):
        flags.append("jan1_placeholder")
    if ip and not ft:
        flags.append("ip_without_ft")
    if ft and not ip:
        flags.append("ft_without_ip")

    ip_ymd = _iso_to_ymd(ip)
    ft_ymd = _iso_to_ymd(ft)
    cd_ymd = _iso_to_ymd(cd)
    if ip_ymd and cd_ymd and ip_ymd < cd_ymd:
        flags.append("ip_before_company_cd")
    if ip_ymd and ft_ymd and abs(ip_ymd - ft_ymd) > 0:
        # same-day mismatch only (dates differ)
        if ip[:10] != ft[:10]:
            flags.append("ip_ft_date_mismatch")

    if compare_history and sy:
        hist_start = _history_range_start(sy)
        ip_dt = _iso_to_date(ip)
        hist_dt = _ymd_int_to_date(hist_start) if hist_start else None
        if hist_dt and ip_dt:
            drift_days = abs((hist_dt - ip_dt).days)
            if drift_days >= min_drift_days:
                flags.append(f"history_drift_{drift_days}d")

    return flags


def _row_report(row: dict[str, Any], flags: list[str], hist_start: int | None) -> dict[str, Any]:
    sy = str(row.get("sy") or row.get("id") or "").strip().upper()
    return {
        "id": row.get("id"),
        "sy": sy,
        "ex": row.get("ex"),
        "nm": row.get("nm"),
        "co": row.get("co"),
        "cc": row.get("cc"),
        "cd": row.get("cd"),
        "ip": row.get("ip"),
        "ft": row.get("ft"),
        "lx": row.get("lx"),
        "nt": row.get("nt"),
        "historyRangeStart": hist_start,
        "flags": flags,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit catalog IPO/first-trade genesis fields.")
    parser.add_argument("--ticker", action="append", default=[], help="Filter symbol(s), repeatable")
    parser.add_argument("--exchange", default="", help="Filter exchange code (e.g. NASDAQ)")
    parser.add_argument("--country", default="", help="Filter country name (e.g. United States)")
    parser.add_argument("--flag", action="append", default=[], help="Only rows with this flag")
    parser.add_argument("--limit", type=int, default=0, help="Max rows to print (0 = all)")
    parser.add_argument("--compare-history", action="store_true", help="Flag ip vs history rangeStart drift")
    parser.add_argument("--min-drift-days", type=int, default=30, help="Min |ip - rangeStart| for history_drift")
    parser.add_argument("--json", default="", help="Write full flagged report JSON to path")
    parser.add_argument("--summary-only", action="store_true")
    args = parser.parse_args()

    catalog = _load_catalog()
    tickers = {t.strip().upper() for t in args.ticker if t.strip()}
    ex_filter = args.exchange.strip().upper()
    co_filter = args.country.strip()

    flagged: list[dict[str, Any]] = []
    flag_counts: dict[str, int] = {}

    for row in catalog:
        sy = str(row.get("sy") or row.get("id") or "").strip().upper()
        if tickers and sy not in tickers:
            continue
        if ex_filter and str(row.get("ex") or "").upper() != ex_filter:
            continue
        if co_filter and str(row.get("co") or "").strip() != co_filter:
            continue

        flags = _flags_for_row(
            row,
            compare_history=args.compare_history,
            min_drift_days=args.min_drift_days,
        )
        if not flags:
            continue
        if args.flag:
            want = set(args.flag)
            if not any(
                any(w == f or f.startswith(f"{w}_") or w in f for w in want) for f in flags
            ):
                continue

        hist_start = _history_range_start(sy) if args.compare_history else None
        rep = _row_report(row, flags, hist_start)
        flagged.append(rep)
        for f in flags:
            base = f.split("_drift_")[0] if f.startswith("history_drift_") else f
            flag_counts[base] = flag_counts.get(base, 0) + 1

    flagged.sort(key=lambda r: (str(r.get("ex") or ""), str(r.get("sy") or "")))

    summary = {
        "generatedAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "catalogPath": str(CATALOG_JSON),
        "catalogRows": len(catalog),
        "flaggedRows": len(flagged),
        "flagCounts": dict(sorted(flag_counts.items(), key=lambda x: -x[1])),
        "erikaSourceDefault": str(DEFAULT_ERIKA_CSV),
        "erikaSourceExists": DEFAULT_ERIKA_CSV.is_file(),
    }

    print(json.dumps(summary, indent=2))

    if not args.summary_only:
        limit = args.limit if args.limit > 0 else len(flagged)
        for rep in flagged[:limit]:
            print(
                f"\n{rep['sy']} ({rep.get('ex')}) — {', '.join(rep['flags'])}"
                f"\n  ip={rep.get('ip')} ft={rep.get('ft')} cd={rep.get('cd')}"
                + (f"\n  historyRangeStart={rep.get('historyRangeStart')}" if rep.get("historyRangeStart") else "")
                + (f"\n  nt={rep.get('nt')}" if rep.get("nt") else "")
            )

    if args.json:
        out_path = Path(args.json)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"summary": summary, "rows": flagged}
        out_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        print(f"\nWrote {len(flagged)} flagged rows → {out_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
