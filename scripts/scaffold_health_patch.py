"""Scaffold an editable per-ticker snowflake overlay (a tiny shim/blob).

Usage:
    python3 scripts/scaffold_health_patch.py NASDAQ:AAPL [--force]

What it does:
  1. Loads the manifest + ticker index.
  2. Reads the current shard entry for the requested ticker.
  3. Writes that profile (verbatim) to `public/data/health/patches/v1/<ticker>.json`,
     stamped with `asOfISO=now`, ready for the researcher to flip individual check
     states (`pass` / `fail` / `na`) and tweak detail strings.
  4. Re-running `python3 scripts/build_health_shards.py` (or `npm run prepare:data`)
     promotes that patch into the manifest with its sha-256 etag, so clients only
     download THAT patch on next visit instead of the whole catalog.

This is the "small shim/shards/blobs" iteration loop: edits land as ~1KB JSON files
that override the corresponding shard entry without invalidating the rest of the lake.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HEALTH_DIR = ROOT / "public" / "data" / "health"
MANIFEST = HEALTH_DIR / "manifest.json"
INDEX = HEALTH_DIR / "shards" / "v1" / "index.json"
SHARDS_DIR = HEALTH_DIR / "shards" / "v1"
PATCHES_DIR = HEALTH_DIR / "patches" / "v1"

_FILENAME_RE = re.compile(r"[^A-Za-z0-9._-]+")


def _patch_filename(ticker: str) -> str:
    return _FILENAME_RE.sub("-", ticker.strip()) + ".json"


def main() -> int:
    parser = argparse.ArgumentParser(description="Scaffold a snowflake patch for one ticker.")
    parser.add_argument("ticker", help="Catalog id, e.g. NASDAQ:AAPL")
    parser.add_argument("--force", action="store_true", help="Overwrite an existing patch.")
    args = parser.parse_args()

    if not MANIFEST.exists() or not INDEX.exists():
        print(
            "Manifest/index not found. Run `npm run prepare:data` first to seed the shards.",
            file=sys.stderr,
        )
        return 1

    index = json.loads(INDEX.read_text(encoding="utf-8"))
    shard_id = index.get(args.ticker)
    if not shard_id:
        print(f"Ticker not in coverage index: {args.ticker}", file=sys.stderr)
        return 2

    shard_path = SHARDS_DIR / f"{shard_id}.json"
    shard = json.loads(shard_path.read_text(encoding="utf-8"))
    profile = shard["profiles"].get(args.ticker)
    if profile is None:
        print(f"Profile missing from shard {shard_id}: {args.ticker}", file=sys.stderr)
        return 3

    profile = json.loads(json.dumps(profile))
    profile["asOfISO"] = datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    profile["sourceNotes"] = [
        f"Manual overlay scaffold (scaffold_health_patch.py {args.ticker})",
        "Edit per-check `state` (pass | fail | na) and `detail` strings, then re-run "
        "`npm run prepare:data` to promote into the manifest.",
    ]

    PATCHES_DIR.mkdir(parents=True, exist_ok=True)
    out_path = PATCHES_DIR / _patch_filename(args.ticker)
    if out_path.exists() and not args.force:
        print(f"Patch already exists at {out_path}; pass --force to overwrite.", file=sys.stderr)
        return 4

    out_path.write_text(
        json.dumps(profile, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote scaffold patch to {out_path}")
    print("Next steps:")
    print("  1) Edit the file (flip `state` from `na` to `pass`/`fail`, fill `detail`).")
    print("  2) Re-run `npm run prepare:data` to update the manifest etag for this patch.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
