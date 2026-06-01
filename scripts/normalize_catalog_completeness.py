#!/usr/bin/env python3
"""Normalize catalog completeness flags (dc, ic, fc) from fields already on each row."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CATALOG = ROOT / "public" / "data" / "catalog.json"


def _has(*values: object) -> bool:
    for v in values:
        if v is None:
            continue
        if isinstance(v, str) and v.strip():
            return True
        if isinstance(v, (list, dict)) and v:
            return True
    return False


def _completeness(*values: object) -> str:
    return "complete" if _has(*values) else "missing"


def _partial(*values: object) -> str:
    present = sum(1 for v in values if _has(v))
    if present >= len(values):
        return "complete"
    if present > 0:
        return "partial"
    return "missing"


def normalize_record(row: dict) -> dict:
    out = dict(row)
    out["dc"] = _completeness(row.get("cd"), row.get("ip"), row.get("ft"))
    out["ic"] = _partial(row.get("cd"), row.get("ip"), row.get("ft"))
    out["fc"] = _partial(row.get("lt"), row.get("ll"), row.get("ln"))
    if _has(row.get("ln")) and not _has(row.get("ls")):
        out["ls"] = "catalog"
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description="Normalize catalog dc/ic/fc fields in place.")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    changed = 0
    for row in catalog:
        before = (row.get("dc"), row.get("ic"), row.get("fc"))
        updated = normalize_record(row)
        after = (updated.get("dc"), updated.get("ic"), updated.get("fc"))
        row.update(updated)
        if before != after:
            changed += 1

    print(f"Normalized {len(catalog):,} listings ({changed:,} rows updated).")
    if args.dry_run:
        print("Dry run — no file written.")
        return 0

    CATALOG.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {CATALOG}")
    print("Next: npm run prepare:data  (rebuild catalog-meta + health shards)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
