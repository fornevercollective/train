from __future__ import annotations

import csv
import json
import os
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SOURCE = ROOT.parent.parent / "erika" / "artifacts" / "ticker_checklist.csv"
SOURCE_CSV = Path(os.environ.get("ERIKA_DATA_PATH", DEFAULT_SOURCE)).resolve()
PUBLIC_DATA_DIR = ROOT / "public" / "data"
GENERATED_DIR = ROOT / "src" / "generated"
CATALOG_JSON = PUBLIC_DATA_DIR / "catalog.json"
SUMMARY_JSON = GENERATED_DIR / "catalog-meta.json"

PREFERRED_FEATURED_IDS = [
    "NASDAQ:AAPL",
    "NASDAQ:MSFT",
    "NASDAQ:TSLA",
    "NYSE:NVDA",
    "NYSEARCA:SPY",
    "NASDAQ:QQQ",
    "KRX:000240",
    "SZSE:000078",
]


def compact_record(row: dict[str, str]) -> dict[str, object]:
    aliases = [alias.strip() for alias in row.get("aliases", "").split("|") if alias.strip()]
    display_name = row.get("company_name") or row.get("legal_entity_name") or row["normalized_ticker"]
    record: dict[str, object] = {
        "id": row["normalized_ticker"],
        "sy": row.get("symbol", ""),
        "ex": row.get("exchange", ""),
        "nm": display_name,
        "ty": row.get("security_type", ""),
        "dc": row.get("date_coverage") or "missing",
        "su": row.get("source_universe", ""),
    }

    optional_fields = {
        "ln": row.get("legal_entity_name", ""),
        "se": row.get("stock_sector", ""),
        "ec": row.get("etf_category", ""),
        "co": row.get("country", ""),
        "cc": row.get("country_code", ""),
        "is": row.get("isin", ""),
        "al": aliases,
        "cd": row.get("company_creation_datetime_utc", ""),
        "ip": row.get("ipo_creation_datetime_utc", ""),
        "ft": row.get("first_trade_datetime_utc", ""),
        "lx": row.get("listing_exchange_label", ""),
        "nt": row.get("notes", ""),
    }

    for key, value in optional_fields.items():
        if value not in ("", [], None):
            record[key] = value

    return record


def top_items(counter: Counter[str], limit: int = 12) -> list[dict[str, object]]:
    return [{"name": name, "count": count} for name, count in counter.most_common(limit)]


def featured_records(records: list[dict[str, object]]) -> list[dict[str, object]]:
    by_id = {record["id"]: record for record in records}
    selected: list[dict[str, object]] = []
    used_ids: set[str] = set()

    for identifier in PREFERRED_FEATURED_IDS:
        record = by_id.get(identifier)
        if record and record.get("dc") != "missing":
            selected.append(record)
            used_ids.add(identifier)

    if len(selected) >= 8:
        return selected[:8]

    seen_countries: set[str] = {str(record.get("co", "")) for record in selected if record.get("co")}

    for record in records:
        if record["id"] in used_ids or record.get("dc") == "missing":
            continue

        country = str(record.get("co", ""))
        if country and country in seen_countries and len(selected) < 5:
            continue

        selected.append(record)
        used_ids.add(str(record["id"]))
        if country:
            seen_countries.add(country)

        if len(selected) >= 8:
            break

    return selected


def summarize(records: list[dict[str, object]]) -> dict[str, object]:
    security_types = Counter()
    countries = Counter()
    exchanges = Counter()
    sectors = Counter()
    date_coverage = Counter()
    with_company_creation = 0
    with_ipo_creation = 0

    for record in records:
        security_types[str(record.get("ty", "(none)"))] += 1
        countries[str(record.get("co", "(none)"))] += 1
        exchanges[str(record.get("ex", "(none)"))] += 1
        sectors[str(record.get("se", "(none)"))] += 1
        date_coverage[str(record.get("dc", "missing"))] += 1
        with_company_creation += int(bool(record.get("cd")))
        with_ipo_creation += int(bool(record.get("ip")))

    return {
        "totalSymbols": len(records),
        "uniqueCountries": len([name for name in countries if name and name != "(none)"]),
        "uniqueExchanges": len([name for name in exchanges if name and name != "(none)"]),
        "withCompanyCreation": with_company_creation,
        "withIpoCreation": with_ipo_creation,
        "securityTypes": top_items(security_types, limit=8),
        "topCountries": top_items(countries),
        "topExchanges": top_items(exchanges),
        "topSectors": top_items(sectors),
        "dateCoverage": {
            "complete": date_coverage.get("complete", 0),
            "partial": date_coverage.get("partial", 0),
            "missing": date_coverage.get("missing", 0),
        },
        "featuredListings": featured_records(records),
        "sourceCsv": str(SOURCE_CSV),
    }


def main() -> None:
    PUBLIC_DATA_DIR.mkdir(parents=True, exist_ok=True)
    GENERATED_DIR.mkdir(parents=True, exist_ok=True)

    if not SOURCE_CSV.exists():
        if CATALOG_JSON.exists() and SUMMARY_JSON.exists():
            print(
                "Erika source CSV not found; using committed generated catalog assets "
                f"at {CATALOG_JSON} and {SUMMARY_JSON}"
            )
            return
        raise SystemExit(
            "Erika source CSV not found and no generated catalog assets are available: "
            f"{SOURCE_CSV}"
        )

    with SOURCE_CSV.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        records = [compact_record(row) for row in reader if row.get("normalized_ticker")]

    summary = summarize(records)

    CATALOG_JSON.write_text(
        json.dumps(records, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    SUMMARY_JSON.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print(f"Wrote {len(records):,} catalog records to {CATALOG_JSON}")
    print(f"Wrote summary metadata to {SUMMARY_JSON}")


if __name__ == "__main__":
    main()
