#!/usr/bin/env python3
"""
Fetch Yahoo Finance predefined sector screeners → public/data/sector-members/*.json

Run locally or in CI (weekly). Do NOT call from the Ritual ROI website — users load the JSON via jsDelivr.

Example:
  python3 scripts/fetch-yahoo-sector-members.py
  python3 scripts/fetch-yahoo-sector-members.py --sector technology
  python3 scripts/fetch-yahoo-sector-members.py --sleep 1.5

Yahoo UI reference:
  https://finance.yahoo.com/research-hub/screener/sec-ind_sec-largest-equities_technology/
"""
from __future__ import annotations

import argparse
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = Path(__file__).resolve().parent / "yahoo-sector-screeners.json"
OUT_DIR = ROOT / "public" / "data" / "sector-members"
USER_AGENT = "RitualROI-TrainSectorFetch/1.0 (kevencraftrituals/train; local batch job)"
PAGE_SIZE = 250
MAX_RETRIES = 4


def fetch_page(scr_id: str, start: int, count: int = PAGE_SIZE) -> dict:
    # Yahoo ignores `offset` on this endpoint; `start` paginates correctly.
    qs = urllib.parse.urlencode({"scrIds": scr_id, "count": count, "start": start})
    url = f"https://query1.finance.yahoo.com/v1/finance/screener/predefined/saved?{qs}"
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    last_err = None
    for attempt in range(MAX_RETRIES):
        try:
            with urllib.request.urlopen(req, timeout=90) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
            last_err = e
            if attempt + 1 < MAX_RETRIES:
                time.sleep(2.0 * (attempt + 1))
    raise RuntimeError(f"Yahoo screener failed after {MAX_RETRIES} tries: {last_err}")


def fetch_screener(scr_id: str, sleep_s: float, verbose: bool = False) -> list[dict]:
    seen: set[str] = set()
    rows: list[dict] = []
    start = 0
    total = None
    page = 0

    while True:
        page += 1
        payload = fetch_page(scr_id, start)
        result = (payload.get("finance") or {}).get("result") or []
        block = result[0] if result else {}
        if total is None:
            total = int(block.get("total") or 0)
        quotes = block.get("quotes") or []
        if verbose:
            print(f"    page {page}: start={start} got={len(quotes)} total={total}", flush=True)
        if not quotes:
            break
        added = 0
        for q in quotes:
            sym = str(q.get("symbol") or "").strip().upper()
            if not sym or sym in seen:
                continue
            seen.add(sym)
            name = str(q.get("longName") or q.get("shortName") or q.get("name") or sym).strip()
            rows.append({"sy": sym, "name": name})
            added += 1
        start += len(quotes)
        if start >= total or len(quotes) < PAGE_SIZE:
            break
        if sleep_s > 0:
            time.sleep(sleep_s)

    if total and len(rows) < total and verbose:
        print(f"    warning: expected {total} tickers, collected {len(rows)}", flush=True)
    return rows


def write_sector_file(entry: dict, tickers: list[dict], updated: str) -> Path:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / entry["file"]
    doc = {
        "sectorId": entry["sectorId"],
        "sectorLabel": entry["sectorLabel"],
        "yahooScrId": entry["yahooScrId"],
        "updated": updated,
        "count": len(tickers),
        "tickers": tickers,
    }
    out.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch Yahoo sector screener membership into train JSON.")
    parser.add_argument(
        "--sector",
        help="Only fetch one sectorId from manifest (e.g. technology)",
    )
    parser.add_argument(
        "--sleep",
        type=float,
        default=1.25,
        help="Seconds between paginated Yahoo requests (default 1.25)",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=MANIFEST,
        help="Path to yahoo-sector-screeners.json",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Print per-page fetch progress",
    )
    parser.add_argument(
        "--enrich-industry",
        action="store_true",
        help="After fetch, run enrich-sector-members-industry.py on updated sector files",
    )
    args = parser.parse_args()

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    sectors = manifest.get("sectors") or []
    if args.sector:
        sectors = [s for s in sectors if s.get("sectorId") == args.sector]
        if not sectors:
            raise SystemExit(f"Unknown sectorId: {args.sector}")

    updated = date.today().isoformat()
    index_sectors = []

    for i, entry in enumerate(sectors):
        scr = entry["yahooScrId"]
        label = entry.get("sectorLabel") or entry.get("sectorId")
        print(f"[{i + 1}/{len(sectors)}] {label} ({scr}) …", flush=True)
        try:
            tickers = fetch_screener(scr, args.sleep, verbose=args.verbose)
        except Exception as e:
            print(f"  FAILED: {e}", flush=True)
            continue
        path = write_sector_file(entry, tickers, updated)
        print(f"  wrote {path.name} ({len(tickers)} tickers)", flush=True)
        index_sectors.append(
            {
                "sectorId": entry["sectorId"],
                "sectorLabel": entry["sectorLabel"],
                "yahooScrId": scr,
                "file": entry["file"],
                "count": len(tickers),
            }
        )
        if args.sleep > 0 and i + 1 < len(sectors):
            time.sleep(args.sleep)

    index = {
        "updated": updated,
        "source": "yahoo_finance_predefined_screener",
        "sectors": index_sectors,
    }
    index_path = OUT_DIR / "index.json"
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    index_path.write_text(json.dumps(index, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {index_path} ({len(index_sectors)} sectors)")

    if args.enrich_industry and index_sectors:
        import subprocess
        enrich = Path(__file__).resolve().parent / "enrich-sector-members-industry.py"
        cmd = ["python3", str(enrich)]
        if args.sector:
            cmd.extend(["--sector", args.sector])
        print("Enriching industry labels…", flush=True)
        subprocess.run(cmd, check=True, cwd=ROOT)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
