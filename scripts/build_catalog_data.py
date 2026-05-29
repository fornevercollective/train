from __future__ import annotations

import csv
import json
import os
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SOURCE = ROOT.parent.parent / "erika" / "artifacts" / "ticker_checklist.csv"
SOURCE_CSV = Path(os.environ.get("ERIKA_DATA_PATH", DEFAULT_SOURCE)).resolve()
PUBLIC_DATA_DIR = ROOT / "public" / "data"
GENERATED_DIR = ROOT / "src" / "generated"
CATALOG_JSON = PUBLIC_DATA_DIR / "catalog.json"
PUBLIC_SUMMARY_JSON = PUBLIC_DATA_DIR / "catalog-meta.json"
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

US_EXCHANGES = {
    "NASDAQ",
    "NYSE",
    "NYSEARCA",
    "NYSEMKT",
    "NYSEAMERICAN",
    "AMEX",
    "BATS",
    "CBOE",
    "OTC",
    "OTCBB",
}


def _as_text(value: object) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _pick_text(source: dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = _as_text(source.get(key))
        if value:
            return value
    return ""


def _aliases_from_row(row: dict[str, Any]) -> list[str]:
    aliases_raw = _pick_text(row, "aliases")
    return [alias.strip() for alias in aliases_raw.split("|") if alias.strip()]


def _normalize_location(value: str) -> str:
    if not value:
        return ""
    normalized = " ".join(value.replace("|", ",").replace(";", ",").split())
    return normalized.strip(", ")


def _normalize_utc_timestamp(value: str) -> str:
    if not value:
        return ""

    candidate = value.strip()
    if not candidate:
        return ""

    if len(candidate) == 10:
        candidate = f"{candidate}T00:00:00Z"

    normalized = candidate.replace(" ", "T")
    if normalized.endswith("Z"):
        parse_candidate = normalized[:-1] + "+00:00"
    else:
        parse_candidate = normalized

    parsed = datetime.fromisoformat(parse_candidate)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    else:
        parsed = parsed.astimezone(timezone.utc)

    return parsed.strftime("%Y-%m-%dT%H:%M:%SZ")


def _completeness(*values: str) -> str:
    present = sum(1 for value in values if value)
    if present == len(values):
        return "complete"
    if present > 0:
        return "partial"
    return "missing"


def _normalized_security_type(record_type: str) -> str:
    value = record_type.strip()
    if not value:
        return "Stock"
    upper = value.upper()
    if upper in {"ETF", "ETN", "ADR", "REIT", "CEF", "SPAC"}:
        return upper
    return value.title()


def _is_us_listing(country: str, exchange: str) -> bool:
    return country == "United States" or exchange.upper() in US_EXCHANGES


def _is_recent_foreign_tech_listing(
    *,
    country: str,
    exchange: str,
    sector: str,
    company_creation_iso: str,
    now_utc: datetime,
) -> bool:
    if not sector or "tech" not in sector.lower():
        return False
    if _is_us_listing(country, exchange):
        return False
    if not company_creation_iso:
        return False
    try:
        created = datetime.strptime(company_creation_iso, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError:
        return False
    return created >= now_utc - timedelta(days=365 * 3)


def compact_record(row: dict[str, Any], issues: dict[str, int]) -> dict[str, object] | None:
    normalized_ticker = _pick_text(row, "normalized_ticker", "id")
    if not normalized_ticker:
        issues["invalidRows"] += 1
        return None

    security_type = _normalized_security_type(_pick_text(row, "security_type", "ty"))

    aliases = _aliases_from_row(row)
    display_name = (
        _pick_text(row, "company_name")
        or _pick_text(row, "legal_entity_name", "ln")
        or _pick_text(row, "nm")
        or normalized_ticker
    )

    company_creation_raw = _pick_text(row, "company_creation_datetime_utc", "cd")
    ipo_creation_raw = _pick_text(row, "ipo_creation_datetime_utc", "ip")
    first_trade_raw = _pick_text(row, "first_trade_datetime_utc", "ft")
    filing_timestamp_raw = _pick_text(
        row,
        "llc_original_filing_timestamp_utc",
        "original_llc_filing_timestamp_utc",
        "llc_filing_timestamp_utc",
        "lt",
    )
    filing_location_raw = _pick_text(
        row,
        "llc_original_filing_location",
        "original_llc_filing_location",
        "llc_filing_location",
        "ll",
    )

    normalized_timestamps: dict[str, str] = {}
    for key, raw_value in {
        "cd": company_creation_raw,
        "ip": ipo_creation_raw,
        "ft": first_trade_raw,
        "lt": filing_timestamp_raw,
    }.items():
        if not raw_value:
            continue
        try:
            normalized_timestamps[key] = _normalize_utc_timestamp(raw_value)
        except ValueError:
            issues["invalidTimestamps"] += 1

    filing_location = _normalize_location(filing_location_raw)
    if filing_location_raw and not filing_location:
        issues["invalidFilingLocations"] += 1

    country = _pick_text(row, "country", "co")
    exchange = _pick_text(row, "exchange", "ex")
    sector = _pick_text(row, "stock_sector", "se")

    ipo_founding_coverage = _completeness(
        normalized_timestamps.get("cd", ""),
        normalized_timestamps.get("ip", ""),
    )
    filing_coverage = _completeness(
        normalized_timestamps.get("lt", ""),
        filing_location,
    )

    date_coverage = "complete"

    record: dict[str, object] = {
        "id": normalized_ticker,
        "sy": _pick_text(row, "symbol", "sy"),
        "ex": exchange,
        "nm": display_name,
        "ty": security_type,
        "dc": date_coverage,
        "su": _pick_text(row, "source_universe", "su"),
        "ic": ipo_founding_coverage,
        "fc": filing_coverage,
    }

    optional_fields = {
        "ln": _pick_text(row, "legal_entity_name", "ln"),
        "se": sector,
        "co": country,
        "cc": _pick_text(row, "country_code", "cc"),
        "is": _pick_text(row, "isin", "is"),
        "al": aliases,
        "cd": normalized_timestamps.get("cd", ""),
        "ip": normalized_timestamps.get("ip", ""),
        "ft": normalized_timestamps.get("ft", ""),
        "lt": normalized_timestamps.get("lt", ""),
        "ll": filing_location,
        "lx": _pick_text(row, "listing_exchange_label", "lx"),
        "nt": _pick_text(row, "notes", "nt"),
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
    with_llc_filing_timestamp = 0
    with_llc_filing_location = 0
    ipo_founding_coverage = Counter()
    filing_coverage = Counter()

    for record in records:
        security_types[str(record.get("ty", "(none)"))] += 1
        countries[str(record.get("co", "(none)"))] += 1
        exchanges[str(record.get("ex", "(none)"))] += 1
        sectors[str(record.get("se", "(none)"))] += 1
        date_coverage[str(record.get("dc", "missing"))] += 1
        with_company_creation += int(bool(record.get("cd")))
        with_ipo_creation += int(bool(record.get("ip")))
        with_llc_filing_timestamp += int(bool(record.get("lt")))
        with_llc_filing_location += int(bool(record.get("ll")))
        ipo_founding_coverage[str(record.get("ic", "missing"))] += 1
        filing_coverage[str(record.get("fc", "missing"))] += 1

    return {
        "totalSymbols": len(records),
        "uniqueCountries": len([name for name in countries if name and name != "(none)"]),
        "uniqueExchanges": len([name for name in exchanges if name and name != "(none)"]),
        "withCompanyCreation": with_company_creation,
        "withIpoCreation": with_ipo_creation,
        "withLlcOriginalFilingTimestamp": with_llc_filing_timestamp,
        "withLlcOriginalFilingLocation": with_llc_filing_location,
        "securityTypes": top_items(security_types, limit=8),
        "topCountries": top_items(countries),
        "topExchanges": top_items(exchanges),
        "topSectors": top_items(sectors),
        "dateCoverage": {
            "complete": date_coverage.get("complete", 0),
            "partial": date_coverage.get("partial", 0),
            "missing": date_coverage.get("missing", 0),
        },
        "ipoFoundingCoverage": {
            "complete": ipo_founding_coverage.get("complete", 0),
            "partial": ipo_founding_coverage.get("partial", 0),
            "missing": ipo_founding_coverage.get("missing", 0),
        },
        "llcOriginalFilingCoverage": {
            "complete": filing_coverage.get("complete", 0),
            "partial": filing_coverage.get("partial", 0),
            "missing": filing_coverage.get("missing", 0),
        },
        "featuredListings": featured_records(records),
        "sourceCsv": str(SOURCE_CSV),
    }


def main() -> None:
    PUBLIC_DATA_DIR.mkdir(parents=True, exist_ok=True)
    GENERATED_DIR.mkdir(parents=True, exist_ok=True)

    issues = Counter()
    raw_rows: list[dict[str, Any]]
    source_mode: str

    if SOURCE_CSV.exists():
        with SOURCE_CSV.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            raw_rows = [dict(row) for row in reader]
        source_mode = "csv"
    elif CATALOG_JSON.exists():
        print(
            "Erika source CSV not found; rebuilding catalog from committed "
            f"catalog assets at {CATALOG_JSON}"
        )
        raw_rows = json.loads(CATALOG_JSON.read_text(encoding="utf-8"))
        source_mode = "catalog_fallback"
    else:
        raise SystemExit(
            "Erika source CSV not found and no generated catalog assets are available: "
            f"{SOURCE_CSV}"
        )

    seen_by_id: dict[str, dict[str, object]] = {}
    records: list[dict[str, object]] = []

    for raw_row in raw_rows:
        record = compact_record(raw_row, issues)
        if not record:
            continue

        record_id = str(record["id"])
        existing = seen_by_id.get(record_id)
        if existing:
            issues["duplicateSymbolsSkipped"] += 1
            if (
                existing.get("sy") != record.get("sy")
                or existing.get("ex") != record.get("ex")
                or existing.get("nm") != record.get("nm")
            ):
                issues["inconsistentDuplicates"] += 1
            continue

        seen_by_id[record_id] = record
        records.append(record)

    records.sort(key=lambda item: str(item.get("id", "")))

    summary = summarize(records)
    summary["validation"] = {
        "sourceMode": source_mode,
        "invalidRows": int(issues.get("invalidRows", 0)),
        "invalidTimestamps": int(issues.get("invalidTimestamps", 0)),
        "invalidFilingLocations": int(issues.get("invalidFilingLocations", 0)),
        "duplicateSymbolsSkipped": int(issues.get("duplicateSymbolsSkipped", 0)),
        "inconsistentDuplicates": int(issues.get("inconsistentDuplicates", 0)),
    }

    CATALOG_JSON.write_text(
        json.dumps(records, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    SUMMARY_JSON.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    PUBLIC_SUMMARY_JSON.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print(f"Wrote {len(records):,} catalog records to {CATALOG_JSON}")
    print(f"Wrote summary metadata to {SUMMARY_JSON}")
    print(f"Wrote public summary metadata to {PUBLIC_SUMMARY_JSON}")
    print(
        "Validation: "
        f"invalidRows={summary['validation']['invalidRows']}, "
        f"invalidTimestamps={summary['validation']['invalidTimestamps']}, "
        f"duplicateSymbolsSkipped={summary['validation']['duplicateSymbolsSkipped']}"
    )


if __name__ == "__main__":
    main()
