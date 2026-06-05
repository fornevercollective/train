#!/usr/bin/env python3
"""Apply etf-showcase.json genesis fields into catalog.json for pinned ETFs."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SHOWCASE = ROOT / "public" / "data" / "etf-showcase.json"
CATALOG = ROOT / "public" / "data" / "catalog.json"


def main() -> None:
    if not SHOWCASE.is_file():
        raise SystemExit(f"Missing {SHOWCASE}")
    if not CATALOG.is_file():
        raise SystemExit(f"Missing {CATALOG}")

    showcase = json.loads(SHOWCASE.read_text(encoding="utf-8"))
    by_sy = {str(t["sy"]).upper(): t for t in showcase.get("tickers") or [] if t.get("sy")}
    records = json.loads(CATALOG.read_text(encoding="utf-8"))
    patched = 0
    for row in records:
        sy = str(row.get("sy") or "").upper()
        src = by_sy.get(sy)
        if not src:
            continue
        for key in ("ip", "ft", "ic", "nt", "ec"):
            if src.get(key) is not None:
                row[key] = src[key]
        if row.get("dc") == "missing":
            row["dc"] = "partial"
        patched += 1

    CATALOG.write_text(json.dumps(records, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Patched {patched} ETF rows in {CATALOG}")


if __name__ == "__main__":
    main()
