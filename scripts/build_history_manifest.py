"""Index every per-ticker history series file into a manifest.

Walks `public/data/history/series/v1/*.json` and writes
`public/data/history/manifest.json` with one entry per ticker, including a sha-256
etag of the canonical bytes. Clients fetch the manifest first and then only
re-download per-ticker files whose etag has flipped — never the whole catalog.

This script is intentionally fast and side-effect-light so it can run on every
`npm run prepare:data` without slowing the dev loop. The actual price fetching
lives in `scripts/fetch_us_history.py` (network-bound, separate command).
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parent.parent
SERIES_DIR = ROOT / "public" / "data" / "history" / "series" / "v1"
MANIFEST_PATH = ROOT / "public" / "data" / "history" / "manifest.json"


def _canonical_bytes(payload: object) -> bytes:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )


def _sha256(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def _iter_series(series_dir: Path) -> Iterable[Path]:
    if not series_dir.exists():
        return []
    return sorted(series_dir.glob("*.json"))


def main() -> None:
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)

    entries: list[dict[str, object]] = []
    earliest = 99999999
    latest = 0
    total_bytes = 0
    lookback_years = 0
    any_max = False

    for path in _iter_series(SERIES_DIR):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise SystemExit(f"Invalid history series JSON at {path}: {exc}") from exc

        ticker = str(payload.get("ticker") or "").strip()
        if not ticker:
            raise SystemExit(f"history series missing ticker: {path}")

        canonical = _canonical_bytes(payload)
        if canonical != path.read_bytes():
            # Re-write canonical so the manifest etag stays stable across build hosts.
            path.write_bytes(canonical)

        rows = int(payload.get("rows") or 0)
        if rows <= 0:
            continue

        range_start = int(payload.get("rangeStart") or 0)
        range_end = int(payload.get("rangeEnd") or 0)
        earliest = min(earliest, range_start) if range_start else earliest
        latest = max(latest, range_end)
        total_bytes += len(canonical)
        lookback_years = max(lookback_years, int(payload.get("lookbackYears") or 0))
        if str(payload.get("lookbackMode") or "").lower() == "max":
            any_max = True

        entries.append(
            {
                "ticker": ticker,
                "exchange": str(payload.get("exchange") or ""),
                "url": f"series/v1/{path.name}",
                "etag": _sha256(canonical),
                "bytes": len(canonical),
                "rows": rows,
                "rangeStart": range_start,
                "rangeEnd": range_end,
                "asOfISO": str(payload.get("asOfISO") or ""),
                "source": str(payload.get("source") or "unknown"),
            }
        )

    entries.sort(key=lambda entry: entry["ticker"])

    manifest = {
        "schemaVersion": 1,
        "generatedAt": datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        # 0 (with lookbackMode='max') means at least one ticker stores its full
        # available history rather than a fixed N-year window.
        "lookbackYears": 0 if any_max and lookback_years == 0 else lookback_years,
        "lookbackMode": "max" if any_max else "fixed",
        "tickerCount": len(entries),
        "totalBytes": total_bytes,
        "earliest": earliest if earliest != 99999999 else 0,
        "latest": latest,
        "entries": entries,
    }
    MANIFEST_PATH.write_bytes(_canonical_bytes(manifest))

    print(
        f"Indexed {len(entries):,} ticker series ({total_bytes/1e6:.2f} MB) "
        f"into {MANIFEST_PATH}"
    )


if __name__ == "__main__":
    main()
