#!/usr/bin/env python3
"""
Emit compact Erika-style catalog rows for crypto natal (ty=Crypto, ex=CRYPTO).

Reads public/data/crypto-natal-config.json (copied from ipo-astro-lookup).

  python3 scripts/build-crypto-natal-catalog.py
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / "public" / "data" / "crypto-natal-config.json"
OUT = ROOT / "public" / "data" / "crypto-natal-catalog.json"


def genesis_to_fields(genesis_utc: str) -> tuple[str, str] | None:
    s = str(genesis_utc or "").strip()
    if not s:
        return None
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(s)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    dt = dt.astimezone(timezone.utc)
    return dt.strftime("%Y-%m-%d"), dt.strftime("%H:%M")


def main() -> None:
    if not CONFIG.is_file():
        raise SystemExit(f"Missing {CONFIG}")

    cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
    instruments = cfg.get("instruments") or []
    rows: list[dict] = []

    for inst in instruments:
        tickers = inst.get("tickers") or []
        primary = str(tickers[0] if tickers else "").strip().upper()
        if not primary:
            continue
        primary = primary.replace("-USD", "")
        fields = genesis_to_fields(inst.get("genesisUtc") or "")
        if not fields:
            continue
        ipo_date, birth_time = fields
        name = str(inst.get("name") or primary)
        loc = str(inst.get("birthLocation") or "")
        row = {
            "id": f"CRYPTO:{primary}",
            "sy": primary,
            "ex": "CRYPTO",
            "nm": name,
            "ty": "Crypto",
            "dc": "crypto_natal",
            "su": "crypto_natal_config",
            "ln": name,
            "ipoDate": ipo_date,
            "birthTime": birth_time,
            "birthTz": "UTC",
            "birthLocation": loc,
            "lat": inst.get("lat"),
            "lon": inst.get("lon"),
            "genesisUtc": inst.get("genesisUtc"),
            "al": [name.lower(), primary.lower(), f"crypto {primary.lower()}"],
        }
        cg_ids = inst.get("cgIds") or []
        if cg_ids:
            row["cgId"] = str(cg_ids[0])
        rows.append(row)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(rows, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"Wrote {len(rows)} crypto natal catalog rows → {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
