"""Split public/data/catalog.json into Workers-safe shards (<25 MiB each).

Writes:
  public/data/catalog/manifest.json
  public/data/catalog/shards/v1/<NNNN>.json   (~256 listings per shard)

The monolithic catalog.json remains for GitHub Pages / bulk export, but is listed
in public/.assetsignore so Cloudflare Workers static assets skip the 30 MiB file.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CATALOG_JSON = ROOT / "public" / "data" / "catalog.json"
CATALOG_DIR = ROOT / "public" / "data" / "catalog"
SHARDS_DIR = CATALOG_DIR / "shards" / "v1"
MANIFEST_PATH = CATALOG_DIR / "manifest.json"

DEFAULT_SHARD_SIZE = 256
SCHEMA_VERSION = 1


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _record_id(record: dict) -> str:
    return str(record.get("id") or record.get("sy") or "")


def build_catalog_shards(*, shard_size: int = DEFAULT_SHARD_SIZE) -> None:
    if not CATALOG_JSON.is_file():
        raise SystemExit(f"catalog.json not found at {CATALOG_JSON}; run build_catalog_data.py first.")

    records = json.loads(CATALOG_JSON.read_text(encoding="utf-8"))
    if not isinstance(records, list):
        raise SystemExit(f"Expected catalog.json to be an array, got {type(records).__name__}.")
    if not records:
        raise SystemExit("catalog.json contained no records.")

    SHARDS_DIR.mkdir(parents=True, exist_ok=True)

    shard_entries: list[dict] = []
    for shard_index, start in enumerate(range(0, len(records), shard_size)):
        chunk = records[start : start + shard_size]
        shard_id = f"{shard_index:04d}"
        payload = json.dumps(chunk, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        shard_path = SHARDS_DIR / f"{shard_id}.json"
        shard_path.write_bytes(payload)

        first = _record_id(chunk[0]) if chunk else ""
        last = _record_id(chunk[-1]) if chunk else ""
        shard_entries.append(
            {
                "id": shard_id,
                "count": len(chunk),
                "bytes": len(payload),
                "etag": _sha256_bytes(payload),
                "first": first,
                "last": last,
            }
        )

    manifest = {
        "schemaVersion": SCHEMA_VERSION,
        "generatedAt": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "recordCount": len(records),
        "shardCount": len(shard_entries),
        "shardSize": shard_size,
        "shards": shard_entries,
    }
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(
        f"Wrote catalog manifest ({len(records)} records, {len(shard_entries)} shards) "
        f"under {CATALOG_DIR.relative_to(ROOT)}"
    )


if __name__ == "__main__":
    build_catalog_shards()
