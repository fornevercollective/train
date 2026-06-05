#!/usr/bin/env python3
"""
Build ETF category membership from train catalog.json → public/data/etf-members/

Groups United States ETFs by `ec` (etf_category). Tile weights are equal within category
until AUM data is wired. Run after catalog.json is built.

  python3 scripts/build-etf-members.py
"""
from __future__ import annotations

import json
from collections import defaultdict
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CATALOG = ROOT / "public" / "data" / "catalog.json"
SHOWCASE = ROOT / "public" / "data" / "etf-showcase.json"
OUT_DIR = ROOT / "public" / "data" / "etf-members"
TOP_PER_CATEGORY = 36
PREFERRED_COUNTRIES = ("United States",)


def slug(s: str) -> str:
    out = "".join(c if c.isalnum() else "-" for c in s.lower()).strip("-")
    while "--" in out:
        out = out.replace("--", "-")
    return out or "other"


def main() -> None:
    if not CATALOG.is_file():
        raise SystemExit(f"Missing {CATALOG} — run build_catalog_data.py first")

    records = json.loads(CATALOG.read_text(encoding="utf-8"))
    buckets: dict[str, list[dict]] = defaultdict(list)

    for row in records:
        if row.get("ty") != "ETF":
            continue
        co = str(row.get("co") or "")
        if PREFERRED_COUNTRIES and co not in PREFERRED_COUNTRIES:
            continue
        ec = str(row.get("ec") or "Other").strip() or "Other"
        sy = str(row.get("sy") or "").strip().upper()
        if not sy or len(sy) > 12 or " " in sy:
            continue
        buckets[ec].append(
            {
                "sy": sy,
                "name": str(row.get("nm") or row.get("ln") or sy).strip(),
                "id": row.get("id"),
            }
        )

    updated = date.today().isoformat()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    index_categories = []

    if SHOWCASE.is_file():
        showcase_doc = json.loads(SHOWCASE.read_text(encoding="utf-8"))
        showcase_tickers = [
            {
                "sy": str(t["sy"]).strip().upper(),
                "name": str(t.get("name") or t["sy"]).strip(),
                "id": t.get("id") or t["sy"],
            }
            for t in showcase_doc.get("tickers") or []
            if t.get("sy")
        ]
        if showcase_tickers:
            featured = {
                "categoryId": "featured",
                "categoryLabel": "Featured",
                "updated": updated,
                "count": len(showcase_tickers),
                "tickers": showcase_tickers,
            }
            (OUT_DIR / "featured.json").write_text(
                json.dumps(featured, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            index_categories.append(
                {
                    "categoryId": "featured",
                    "categoryLabel": "Featured",
                    "file": "featured.json",
                    "count": len(showcase_tickers),
                }
            )

    for ec in sorted(buckets.keys(), key=lambda k: (-len(buckets[k]), k)):
        tickers = sorted(buckets[ec], key=lambda t: t["sy"])[:TOP_PER_CATEGORY]
        if not tickers:
            continue
        cat_id = slug(ec)
        doc = {
            "categoryId": cat_id,
            "categoryLabel": ec,
            "updated": updated,
            "count": len(tickers),
            "tickers": tickers,
        }
        path = OUT_DIR / f"{cat_id}.json"
        path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        index_categories.append(
            {
                "categoryId": cat_id,
                "categoryLabel": ec,
                "file": path.name,
                "count": len(tickers),
            }
        )

    index = {
        "updated": updated,
        "source": "train_catalog_ec",
        "countryFilter": list(PREFERRED_COUNTRIES),
        "categories": index_categories,
    }
    (OUT_DIR / "index.json").write_text(json.dumps(index, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(index_categories)} ETF categories to {OUT_DIR}")


if __name__ == "__main__":
    main()
