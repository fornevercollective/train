#!/usr/bin/env python3
"""
Backfill catalog `se` (sector) from public/data/sector-members/*.json.

sector-members is Yahoo-sourced GICS identity — does NOT carry IPO dates.
Use after fetch-yahoo-sector-members.py + enrich-sector-members-industry.py.

  python3 scripts/patch_catalog_sectors_from_members.py           # dry-run stats
  python3 scripts/patch_catalog_sectors_from_members.py --apply   # write catalog + shards
  python3 scripts/patch_catalog_sectors_from_members.py --apply --us-only
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SECTOR_DIR = ROOT / "public" / "data" / "sector-members"
TAXONOMY = Path(__file__).resolve().parent / "sector-taxonomy.json"
CATALOG = ROOT / "public" / "data" / "catalog.json"
SHARD_DIR = ROOT / "public" / "data" / "catalog" / "shards" / "v1"

# Ritual ROI catalog + mood engine use these GICS-style sector strings.
YAHOO_TO_CATALOG_SECTOR = {
    "Technology": "Information Technology",
    "Financial Services": "Financials",
    "Communication Services": "Communication Services",
    "Consumer Cyclical": "Consumer Discretionary",
    "Consumer Defensive": "Consumer Staples",
    "Healthcare": "Health Care",
    "Health Care": "Health Care",
    "Industrials": "Industrials",
    "Energy": "Energy",
    "Basic Materials": "Materials",
    "Real Estate": "Real Estate",
    "Utilities": "Utilities",
}

US_EXCHANGES = frozenset(
    {
        "NYSE",
        "NASDAQ",
        "NYSEARCA",
        "NYSEMKT",
        "AMEX",
        "BATS",
        "CBOE",
        "OTC",
    }
)


def load_yahoo_to_catalog() -> dict[str, str]:
    out = dict(YAHOO_TO_CATALOG_SECTOR)
    if TAXONOMY.is_file():
        doc = json.loads(TAXONOMY.read_text(encoding="utf-8"))
        for yahoo, sid in (doc.get("yahooSectorToSectorId") or {}).items():
            # Reverse map sectorId files → catalog label via catalogSectorToSectorId
            for cat_label, cat_sid in (doc.get("catalogSectorToSectorId") or {}).items():
                if cat_sid == sid and yahoo not in out:
                    out[yahoo] = cat_label
    return out


def normalize_sector(raw: str, yahoo_map: dict[str, str]) -> str:
    s = str(raw or "").strip()
    if not s:
        return ""
    return yahoo_map.get(s, s)


def load_sector_member_index() -> dict[str, dict[str, str]]:
    """sy -> { se, industry } from sector-members JSON files."""
    by_sy: dict[str, dict[str, str]] = {}
    if not SECTOR_DIR.is_dir():
        return by_sy
    yahoo_map = load_yahoo_to_catalog()
    for path in sorted(SECTOR_DIR.glob("*.json")):
        if path.name == "index.json" or path.name == "industry-cache.json":
            continue
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        tickers = doc.get("tickers") if isinstance(doc, dict) else None
        if not isinstance(tickers, list):
            continue
        for row in tickers:
            if not isinstance(row, dict):
                continue
            sy = str(row.get("sy") or "").strip().upper()
            if not sy:
                continue
            sector_raw = str(row.get("sector") or doc.get("sectorLabel") or "").strip()
            industry = str(row.get("industry") or "").strip()
            se = normalize_sector(sector_raw, yahoo_map)
            if not se:
                continue
            prev = by_sy.get(sy)
            if prev and prev.get("se") == se:
                if industry and not prev.get("industry"):
                    prev["industry"] = industry
                continue
            by_sy[sy] = {"se": se, "industry": industry}
    return by_sy


def row_eligible(row: dict, us_only: bool) -> bool:
    if str(row.get("ty") or "").strip().lower() not in ("stock", ""):
        if str(row.get("ty") or "").strip().lower() != "stock":
            return False
    if not us_only:
        return True
    cc = str(row.get("cc") or "").strip().upper()
    ex = str(row.get("ex") or "").strip().upper()
    return cc == "US" and ex in US_EXCHANGES


def patch_row(row: dict, src: dict[str, str], overwrite: bool) -> bool:
    changed = False
    cur_se = str(row.get("se") or "").strip()
    next_se = str(src.get("se") or "").strip()
    if next_se and (overwrite or not cur_se) and cur_se != next_se:
        row["se"] = next_se
        changed = True
    # Future: optional `in` industry field when mood engine reads catalog industry.
    return changed


def patch_records(
    records: list[dict],
    by_sy: dict[str, dict[str, str]],
    *,
    us_only: bool,
    overwrite: bool,
) -> int:
    n = 0
    for row in records:
        sy = str(row.get("sy") or "").strip().upper()
        if not sy or not row_eligible(row, us_only):
            continue
        src = by_sy.get(sy)
        if not src:
            continue
        if patch_row(row, src, overwrite):
            n += 1
    return n


def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill catalog se from sector-members.")
    parser.add_argument("--apply", action="store_true", help="Write catalog.json and shard files")
    parser.add_argument("--us-only", action="store_true", help="Only US NYSE/NASDAQ/etc. stocks")
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Replace existing se when sector-members disagrees (use for known bad labels)",
    )
    args = parser.parse_args()

    by_sy = load_sector_member_index()
    if not by_sy:
        raise SystemExit(f"No sector-members data under {SECTOR_DIR}")

    missing_before = 0
    us_missing_before = 0
    would_patch = 0

    if CATALOG.is_file():
        records = json.loads(CATALOG.read_text(encoding="utf-8"))
        for row in records:
            sy = str(row.get("sy") or "").strip().upper()
            if not sy:
                continue
            if not str(row.get("se") or "").strip():
                missing_before += 1
                if row_eligible(row, True):
                    us_missing_before += 1
            src = by_sy.get(sy)
            if not src:
                continue
            if not row_eligible(row, args.us_only):
                continue
            cur = str(row.get("se") or "").strip()
            nxt = str(src.get("se") or "").strip()
            if nxt and (args.overwrite or not cur) and cur != nxt:
                would_patch += 1

        print(f"sector-members index: {len(by_sy)} tickers")
        print(f"catalog missing se: {missing_before} total · {us_missing_before} US listed")
        print(f"would patch rows: {would_patch} ({'apply' if args.apply else 'dry-run'})")

        if args.apply:
            n = patch_records(records, by_sy, us_only=args.us_only, overwrite=args.overwrite)
            CATALOG.write_text(json.dumps(records, ensure_ascii=False) + "\n", encoding="utf-8")
            print(f"patched catalog.json: {n} rows")
    else:
        print(f"Missing {CATALOG}")

    shard_files = 0
    shard_rows = 0
    if SHARD_DIR.is_dir():
        for path in sorted(SHARD_DIR.glob("*.json")):
            if path.name == "index.json":
                continue
            rows = json.loads(path.read_text(encoding="utf-8"))
            n = patch_records(rows, by_sy, us_only=args.us_only, overwrite=args.overwrite)
            if n and args.apply:
                path.write_text(json.dumps(rows, ensure_ascii=False) + "\n", encoding="utf-8")
                shard_files += 1
                shard_rows += n
        if args.apply:
            print(f"patched shards: {shard_rows} rows in {shard_files} file(s)")


if __name__ == "__main__":
    main()
