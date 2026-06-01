"""Build per-listing snowflake coverage profiles into versioned shards + patches.

This script reads the generated `public/data/catalog.json` and writes:

    public/data/health/manifest.json                 # tiny: shard + patch index, sha256 etags
    public/data/health/shards/v1/<NNNN>.json         # ~SHARD_SIZE listings per shard
    public/data/health/shards/v1/index.json          # ticker -> shard id (for lookup)
    public/data/health/patches/v1/<TICKER>.json      # per-listing overlay (kept if hand-edited)

Why shards + patches?
- The full catalog is ~20 MB. We do not want clients re-downloading it for minor edits.
- Default skeletal SnowflakeProfileV1 records are deterministic; shards stay byte-stable
  across runs unless their listings actually changed, so etags only flip on real edits.
- Per-ticker JSON patches act as small "shims/blobs" that override a shard entry. Hand
  edits live under `patches/v1/<TICKER>.json` and survive regeneration (the script
  refuses to overwrite an existing patch, so iteration is safe).

The manifest is the only file every client must fetch; from there it picks just the
shards/patches whose etag differs from what it has cached.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

SCRIPT_DIR = Path(__file__).resolve().parent
import sys

sys.path.insert(0, str(SCRIPT_DIR))
from health_profile_from_history import profile_for_record  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
PUBLIC_DATA_DIR = ROOT / "public" / "data"
CATALOG_JSON = PUBLIC_DATA_DIR / "catalog.json"
HEALTH_DIR = PUBLIC_DATA_DIR / "health"
SHARDS_DIR = HEALTH_DIR / "shards" / "v1"
PATCHES_DIR = HEALTH_DIR / "patches" / "v1"
MANIFEST_PATH = HEALTH_DIR / "manifest.json"
TICKER_INDEX_PATH = SHARDS_DIR / "index.json"

DEFAULT_SHARD_SIZE = 256
SCHEMA_VERSION = 1

AXES: tuple[tuple[str, str, list[tuple[str, str]]], ...] = (
    (
        "value",
        "Value",
        [
            ("price-vs-fair", "Trading below estimated fair value"),
            ("price-vs-peers", "Price-to-earnings vs peers"),
        ],
    ),
    (
        "future",
        "Future",
        [
            ("eps-growth-fwd", "Forecast EPS growth above market"),
            ("revenue-growth-fwd", "Forecast revenue growth above market"),
            ("roe-forecast", "Forecast return on equity"),
        ],
    ),
    (
        "past",
        "Past",
        [
            ("eps-growth-5y", "EPS growth over the past 5 years"),
            ("revenue-growth-5y", "Revenue growth over the past 5 years"),
            ("eps-acceleration-1y", "EPS growth accelerating last 12 months"),
        ],
    ),
    (
        "health",
        "Health",
        [
            ("debt-to-equity", "Debt-to-equity ratio in safe range"),
            ("operating-cashflow", "Operating cashflow covers debt"),
            ("interest-coverage", "Interest coverage ratio healthy"),
        ],
    ),
    (
        "dividends",
        "Dividends",
        [
            ("dividend-yield", "Dividend yield is above market average"),
            ("payout-ratio", "Payout ratio is sustainable"),
            ("dividend-growth", "Dividend growth is positive"),
        ],
    ),
)

# Listings without dividend signal in the lake yet still get the axis but with `na`.
DEFAULT_AS_OF = "1970-01-01T00:00:00Z"


# Filenames must be safe across GH Pages, S3, and Cloudflare cache.
_PATCH_NAME_RE = re.compile(r"[^A-Za-z0-9._-]+")


def _patch_filename(ticker: str) -> str:
    """Return a filesystem-safe filename for a per-ticker overlay."""

    return _PATCH_NAME_RE.sub("-", ticker.strip()) + ".json"


def _canonical_json_bytes(payload: object) -> bytes:
    """Serialize JSON deterministically (sorted keys, no whitespace) for stable etags."""

    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )


def _sha256(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def _default_profile(record: dict[str, object]) -> dict[str, object]:
    """OHLCV-scored profile when history exists; otherwise skeleton. Patches still override."""

    return profile_for_record(record)  # type: ignore[arg-type]


def _iter_records(catalog_path: Path) -> Iterable[dict[str, object]]:
    with catalog_path.open("r", encoding="utf-8") as handle:
        records = json.load(handle)
    if not isinstance(records, list):
        raise SystemExit(f"Expected catalog.json to be an array, got {type(records).__name__}.")
    yield from sorted(records, key=lambda entry: str(entry.get("id", "")))


def _shard_id(index: int) -> str:
    return f"{index:04d}"


def _load_existing_patches() -> dict[str, dict[str, object]]:
    """Load any hand-curated overlays already on disk so we surface them in the manifest."""

    overlays: dict[str, dict[str, object]] = {}
    if not PATCHES_DIR.exists():
        return overlays
    for path in sorted(PATCHES_DIR.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise SystemExit(f"Invalid patch JSON at {path}: {exc}") from exc
        ticker = str(data.get("ticker", "")).strip()
        if not ticker:
            raise SystemExit(f"Patch missing 'ticker' field: {path}")
        overlays[ticker] = data
    return overlays


def build(shard_size: int) -> dict[str, object]:
    if not CATALOG_JSON.exists():
        raise SystemExit(
            f"catalog.json not found at {CATALOG_JSON}; run prepare:data first."
        )

    SHARDS_DIR.mkdir(parents=True, exist_ok=True)
    PATCHES_DIR.mkdir(parents=True, exist_ok=True)

    overlays = _load_existing_patches()

    records = list(_iter_records(CATALOG_JSON))
    total = len(records)
    if total == 0:
        raise SystemExit("catalog.json contained no records.")

    # Wipe stale shards but keep patches (they are user-authored).
    for stale in SHARDS_DIR.glob("*.json"):
        stale.unlink()

    ticker_index: dict[str, str] = {}
    shard_entries: list[dict[str, object]] = []

    for batch_index, batch_start in enumerate(range(0, total, shard_size)):
        batch = records[batch_start : batch_start + shard_size]
        shard_id = _shard_id(batch_index)

        profiles: dict[str, dict[str, object]] = {}
        ticker_list: list[str] = []
        for record in batch:
            ticker = str(record["id"])
            ticker_list.append(ticker)
            profiles[ticker] = _default_profile(record)
            ticker_index[ticker] = shard_id

        shard_payload = {
            "schemaVersion": SCHEMA_VERSION,
            "shardId": shard_id,
            "tickers": ticker_list,
            "profiles": profiles,
        }
        shard_bytes = _canonical_json_bytes(shard_payload)
        shard_path = SHARDS_DIR / f"{shard_id}.json"
        shard_path.write_bytes(shard_bytes)

        shard_entries.append(
            {
                "id": shard_id,
                "url": f"shards/v1/{shard_id}.json",
                "etag": _sha256(shard_bytes),
                "bytes": len(shard_bytes),
                "count": len(ticker_list),
                "first": ticker_list[0],
                "last": ticker_list[-1],
            }
        )

    index_bytes = _canonical_json_bytes(ticker_index)
    TICKER_INDEX_PATH.write_bytes(index_bytes)

    patch_entries: list[dict[str, object]] = []
    for ticker, payload in sorted(overlays.items()):
        filename = _patch_filename(ticker)
        patch_bytes = _canonical_json_bytes(payload)
        (PATCHES_DIR / filename).write_bytes(patch_bytes)
        patch_entries.append(
            {
                "ticker": ticker,
                "url": f"patches/v1/{filename}",
                "etag": _sha256(patch_bytes),
                "bytes": len(patch_bytes),
                "asOfISO": str(payload.get("asOfISO") or DEFAULT_AS_OF),
            }
        )

    manifest = {
        "schemaVersion": SCHEMA_VERSION,
        "generatedAt": datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "shardSize": shard_size,
        "tickerCount": total,
        "shardCount": len(shard_entries),
        "patchCount": len(patch_entries),
        "axes": [
            {"name": name, "label": label, "checkCount": len(checks)}
            for name, label, checks in AXES
        ],
        "indexUrl": "shards/v1/index.json",
        "indexEtag": _sha256(index_bytes),
        "indexBytes": len(index_bytes),
        "shards": shard_entries,
        "patches": patch_entries,
    }
    manifest_bytes = _canonical_json_bytes(manifest)
    MANIFEST_PATH.write_bytes(manifest_bytes)

    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description="Build snowflake coverage shards + manifest.")
    parser.add_argument(
        "--shard-size",
        type=int,
        default=int(os.environ.get("HEALTH_SHARD_SIZE", DEFAULT_SHARD_SIZE)),
        help=f"Listings per shard (default {DEFAULT_SHARD_SIZE}).",
    )
    args = parser.parse_args()

    if args.shard_size <= 0:
        raise SystemExit("--shard-size must be positive.")

    manifest = build(args.shard_size)
    print(
        f"Wrote {manifest['shardCount']} shards covering {manifest['tickerCount']} listings "
        f"to {SHARDS_DIR}"
    )
    print(f"Wrote ticker index to {TICKER_INDEX_PATH} ({manifest['indexBytes']} bytes)")
    print(
        f"Recorded {manifest['patchCount']} per-ticker overlay patch(es) under {PATCHES_DIR}"
    )
    print(f"Wrote manifest to {MANIFEST_PATH}")


if __name__ == "__main__":
    main()
