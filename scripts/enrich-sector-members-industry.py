#!/usr/bin/env python3
"""
Enrich sector-members tickers with Yahoo Finance industry + sector labels.

Yahoo predefined screeners return only symbol + name. This script uses the
finance/search endpoint (same industry fields as the Yahoo UI) and writes:

  { "sy": "UNP", "name": "...", "sector": "Industrials", "industry": "Railroads" }

Results are cached under public/data/sector-members/industry-cache.json so
re-runs only fetch missing symbols.

Usage:
  python3 scripts/enrich-sector-members-industry.py --sector industrials
  python3 scripts/enrich-sector-members-industry.py
  python3 scripts/enrich-sector-members-industry.py --refresh UNP,CSX
"""
from __future__ import annotations

import argparse
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SECTOR_DIR = ROOT / "public" / "data" / "sector-members"
TAXONOMY = Path(__file__).resolve().parent / "sector-taxonomy.json"
CACHE_PATH = SECTOR_DIR / "industry-cache.json"
CATALOG_PATH = ROOT / "public" / "data" / "catalog.json"
USER_AGENT = "RitualROI-TrainIndustryEnrich/1.0 (kevencraftrituals/train; local batch job)"
MAX_RETRIES = 4


def _load_taxonomy() -> dict:
    if not TAXONOMY.is_file():
        return {}
    return json.loads(TAXONOMY.read_text(encoding="utf-8"))


def normalize_industry_label(label: str | None, taxonomy: dict) -> str:
    text = str(label or "").strip()
    if not text:
        return ""
    mapping = taxonomy.get("industryLabelNormalize") or {}
    return mapping.get(text, text.replace("—", " - "))


def load_catalog_sectors() -> dict[str, str]:
    """sy -> catalog `se` sector label."""
    if not CATALOG_PATH.is_file():
        return {}
    records = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    out: dict[str, str] = {}
    if not isinstance(records, list):
        return out
    for row in records:
        sy = str(row.get("sy") or "").strip().upper()
        se = str(row.get("se") or "").strip()
        if sy and se and sy not in out:
            out[sy] = se
    return out


def load_cache() -> dict:
    if not CACHE_PATH.is_file():
        return {"updated": None, "source": "yahoo_finance_search", "tickers": {}}
    doc = json.loads(CACHE_PATH.read_text(encoding="utf-8"))
    if not isinstance(doc.get("tickers"), dict):
        doc["tickers"] = {}
    return doc


def save_cache(cache: dict) -> None:
    cache["updated"] = date.today().isoformat()
    SECTOR_DIR.mkdir(parents=True, exist_ok=True)
    CACHE_PATH.write_text(json.dumps(cache, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def fetch_yahoo_search(symbol: str) -> dict | None:
    qs = urllib.parse.urlencode({"q": symbol, "quotesCount": 6, "newsCount": 0})
    url = f"https://query1.finance.yahoo.com/v1/finance/search?{qs}"
    req = urllib.request.Request(
        url,
        headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
    )
    last_err: Exception | None = None
    for attempt in range(MAX_RETRIES):
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
            sym = symbol.upper()
            for quote in payload.get("quotes") or []:
                if str(quote.get("symbol") or "").upper() != sym:
                    continue
                qtype = str(quote.get("quoteType") or "").upper()
                if qtype and qtype not in {"EQUITY", "ETF"}:
                    continue
                sector = str(quote.get("sectorDisp") or quote.get("sector") or "").strip()
                industry = str(quote.get("industryDisp") or quote.get("industry") or "").strip()
                if sector or industry:
                    return {"sector": sector, "industry": industry}
            return None
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as err:
            last_err = err
            if attempt + 1 < MAX_RETRIES:
                time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"Yahoo search failed for {symbol}: {last_err}")


def collect_symbols(sector_filter: str | None) -> list[str]:
    symbols: set[str] = set()
    for path in sorted(SECTOR_DIR.glob("*.json")):
        if path.name in {"index.json", "industry-cache.json"}:
            continue
        doc = json.loads(path.read_text(encoding="utf-8"))
        if sector_filter and doc.get("sectorId") != sector_filter:
            continue
        for row in doc.get("tickers") or []:
            sy = str(row.get("sy") or "").strip().upper()
            if sy:
                symbols.add(sy)
    return sorted(symbols)


def enrich_cache(
    symbols: list[str],
    cache: dict,
    *,
    refresh: set[str],
    sleep_s: float,
    verbose: bool,
) -> tuple[int, int]:
    tickers = cache.setdefault("tickers", {})
    fetched = 0
    skipped = 0
    for i, sym in enumerate(symbols, 1):
        if sym in tickers and sym not in refresh:
            skipped += 1
            continue
        if verbose:
            print(f"  [{i}/{len(symbols)}] {sym} …", flush=True)
        try:
            hit = fetch_yahoo_search(sym)
        except Exception as err:
            print(f"  WARN {sym}: {err}", flush=True)
            hit = None
        if hit:
            tickers[sym] = hit
        else:
            tickers[sym] = {"sector": "", "industry": ""}
        fetched += 1
        if sleep_s > 0 and i < len(symbols):
            time.sleep(sleep_s)
    return fetched, skipped


def apply_cache_to_sector_files(
    cache: dict,
    taxonomy: dict,
    catalog_sectors: dict[str, str],
    sector_filter: str | None,
) -> list[tuple[str, int, int]]:
    tickers = cache.get("tickers") or {}
    yahoo_to_id = taxonomy.get("yahooSectorToSectorId") or {}
    catalog_to_id = taxonomy.get("catalogSectorToSectorId") or {}
    stats: list[tuple[str, int, int]] = []

    for path in sorted(SECTOR_DIR.glob("*.json")):
        if path.name in {"index.json", "industry-cache.json"}:
            continue
        doc = json.loads(path.read_text(encoding="utf-8"))
        sector_id = doc.get("sectorId")
        if sector_filter and sector_id != sector_filter:
            continue

        enriched = 0
        missing = 0
        for row in doc.get("tickers") or []:
            sy = str(row.get("sy") or "").strip().upper()
            if not sy:
                continue
            hit = tickers.get(sy) or {}
            sector = str(hit.get("sector") or "").strip()
            industry = normalize_industry_label(hit.get("industry"), taxonomy)

            if sector:
                row["sector"] = sector
            elif catalog_sectors.get(sy):
                row["sector"] = catalog_sectors[sy]

            if industry:
                row["industry"] = industry
                enriched += 1
            else:
                row.pop("industry", None)
                missing += 1

            # Drop stale keys from older experiments
            row.pop("subIndustry", None)

        doc["industryEnriched"] = date.today().isoformat()
        doc["industrySource"] = "yahoo_finance_search"
        path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        stats.append((path.name, enriched, missing))

    return stats


def update_index(sector_filter: str | None) -> None:
    index_path = SECTOR_DIR / "index.json"
    if not index_path.is_file():
        return
    index = json.loads(index_path.read_text(encoding="utf-8"))
    for entry in index.get("sectors") or []:
        fname = entry.get("file")
        if not fname:
            continue
        path = SECTOR_DIR / fname
        if not path.is_file():
            continue
        if sector_filter and entry.get("sectorId") != sector_filter:
            continue
        doc = json.loads(path.read_text(encoding="utf-8"))
        entry["industryEnriched"] = doc.get("industryEnriched")
    index["industryCache"] = "industry-cache.json"
    index_path.write_text(json.dumps(index, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Enrich sector-members JSON with Yahoo industry labels.")
    parser.add_argument("--sector", help="Only process one sectorId (e.g. industrials)")
    parser.add_argument("--sleep", type=float, default=0.35, help="Seconds between Yahoo search calls")
    parser.add_argument(
        "--refresh",
        help="Comma-separated symbols to re-fetch even if cached",
    )
    parser.add_argument(
        "--apply-only",
        action="store_true",
        help="Skip Yahoo fetch; apply existing industry-cache.json to sector files",
    )
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    taxonomy = _load_taxonomy()
    catalog_sectors = load_catalog_sectors()
    cache = load_cache()
    refresh = {s.strip().upper() for s in (args.refresh or "").split(",") if s.strip()}

    symbols = collect_symbols(args.sector)
    if not symbols:
        raise SystemExit("No sector-members tickers found.")

    if not args.apply_only:
        print(f"Fetching industry for {len(symbols)} symbol(s)…", flush=True)
        fetched, skipped = enrich_cache(
            symbols,
            cache,
            refresh=refresh,
            sleep_s=args.sleep,
            verbose=args.verbose,
        )
        save_cache(cache)
        print(f"Cache updated: {fetched} fetched, {skipped} cached → {CACHE_PATH.name}")

    stats = apply_cache_to_sector_files(cache, taxonomy, catalog_sectors, args.sector)
    update_index(args.sector)

    print("Sector files updated:")
    for name, enriched, missing in stats:
        print(f"  {name}: {enriched} with industry, {missing} without")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
