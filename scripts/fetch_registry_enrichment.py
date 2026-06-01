#!/usr/bin/env python3
"""Fetch registry-shaped enrichment rows for the Train catalog.

US listings (NASDAQ, NYSE, etc.) use SEC EDGAR submissions — OpenRegistry's free
web/MCP search does not expose jurisdiction US. Non-US listings use the OpenRegistry
public search API where the listing's country maps to a supported ISO jurisdiction.

Output is NDJSON consumed by `build_attribution_enrichment.py` (via --sec and
--registry flags, or the auto-loaded `public/data/enrichment/sources/` folder).

Examples:
  python3 scripts/fetch_registry_enrichment.py --tickers TSLA,AAPL,MSFT
  python3 scripts/fetch_registry_enrichment.py --exchange NASDAQ --limit 50 --delay 0.2
  python3 scripts/fetch_registry_enrichment.py --openregistry-only --country-code GB --limit 20
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Optional

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
from us_registry_geo import geocode_us_address, state_sos_venue  # noqa: E402

ROOT = SCRIPT_DIR.parent
CATALOG_JSON = ROOT / "public" / "data" / "catalog.json"
SOURCES_DIR = ROOT / "public" / "data" / "enrichment" / "sources"

SEC_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
SEC_SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik:010d}.json"
OPENREGISTRY_SEARCH_URL = "https://openregistry.sophymarine.com/api/v1/search"

DEFAULT_USER_AGENT = os.environ.get(
    "SEC_USER_AGENT",
    "qbitos-train-enrichment/1.0 (contact: enrichment@qbitos.ai)",
)

US_EXCHANGES = {"NASDAQ", "NYSE", "NYSEARCA", "NYSEMKT", "CBOE", "AMEX", "BATS", "OTC", "OTCBB"}

# Catalog country / exchange hints → OpenRegistry ISO (free-tier web search whitelist).
COUNTRY_TO_JURISDICTION: dict[str, str] = {
    "United Kingdom": "GB",
    "UK": "GB",
    "France": "FR",
    "Spain": "ES",
    "Ireland": "IE",
    "Norway": "NO",
    "Finland": "FI",
    "Czech Republic": "CZ",
    "Czechia": "CZ",
    "Poland": "PL",
    "Australia": "AU",
    "New Zealand": "NZ",
    "Canada": "CA",
    "Switzerland": "CH",
    "Belgium": "BE",
    "Netherlands": "NL",
    "Hong Kong": "HK",
    "Taiwan": "TW",
    "South Korea": "KR",
    "Korea": "KR",
    "Italy": "IT",
    "Japan": "JP",
    "Malaysia": "MY",
    "Cyprus": "CY",
    "Iceland": "IS",
    "Isle of Man": "IM",
    "Monaco": "MC",
    "Liechtenstein": "LI",
    "Mexico": "MX",
    "Russia": "RU",
}

OPENREGISTRY_LICENSE_BY_JURISDICTION: dict[str, str] = {
    "GB": "OGL",
    "NO": "NLOD",
    "FR": "ETALAB",
    "IE": "CC-BY",
    "ES": "CC-BY",
    "FI": "CC-BY",
    "CZ": "CC-BY",
    "PL": "CC-BY",
    "AU": "CC-BY",
    "NZ": "CC-BY",
    "CA": "CC-BY",
    "CH": "CC-BY",
    "BE": "CC-BY",
    "NL": "CC-BY",
    "HK": "CC-BY",
    "TW": "CC-BY",
    "KR": "CC-BY",
    "IT": "CC-BY",
    "JP": "CC-BY",
    "MY": "CC-BY",
    "CY": "CC-BY",
    "IS": "CC-BY",
    "IM": "CC-BY",
    "MC": "CC-BY",
    "LI": "CC-BY",
    "MX": "CC-BY",
    "RU": "CC-BY",
}


def _http_get(url: str, *, user_agent: str, accept: str = "application/json") -> bytes:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": user_agent, "Accept": accept},
    )
    with urllib.request.urlopen(request, timeout=45) as response:
        return response.read()


def _normalize_ticker_id(record: dict[str, Any]) -> str:
    direct = str(record.get("id") or "").strip().upper()
    if direct:
        return direct
    symbol = str(record.get("sy") or "").strip().upper()
    exchange = str(record.get("ex") or "").strip().upper()
    if symbol and exchange:
        return f"{exchange}:{symbol}"
    return symbol


STATUTORY_FORM_PREFIXES = (
    "S-1",
    "S-3",
    "S-4",
    "10-12B",
    "8-A12B",
    "424B4",
    "CERT",
)
STATUTORY_FORM_FALLBACK_PREFIXES = ("REGDEX", "10-K", "10-Q")


def _format_sec_address(address: dict[str, Any] | None) -> str:
    if not address:
        return ""
    parts = [
        str(address.get("street1") or "").strip(),
        str(address.get("street2") or "").strip(),
        str(address.get("city") or "").strip(),
        str(address.get("stateOrCountryDescription") or address.get("stateOrCountry") or "").strip(),
        str(address.get("zipCode") or "").strip(),
    ]
    return ", ".join(part for part in parts if part)


def _load_sec_ticker_index(user_agent: str) -> dict[str, dict[str, Any]]:
    payload = json.loads(_http_get(SEC_TICKERS_URL, user_agent=user_agent).decode("utf-8"))
    by_ticker: dict[str, dict[str, Any]] = {}
    for entry in payload.values():
        if not isinstance(entry, dict):
            continue
        ticker = str(entry.get("ticker") or "").strip().upper()
        if ticker:
            by_ticker[ticker] = entry
    return by_ticker


def _append_filing_rows(
    target: list[tuple[str, str, str]],
    payload: dict[str, Any],
) -> None:
    dates = payload.get("filingDate") or []
    forms = payload.get("form") or []
    accepts = payload.get("acceptanceDateTime") or []
    for index, filing_date in enumerate(dates):
        form = str(forms[index] if index < len(forms) else "")
        accepted = str(accepts[index] if index < len(accepts) else "")
        target.append((str(filing_date), form, accepted))


def _collect_sec_filings(body: dict[str, Any], *, user_agent: str) -> list[tuple[str, str, str]]:
    filings: list[tuple[str, str, str]] = []
    recent = body.get("filings", {}).get("recent") if isinstance(body.get("filings"), dict) else None
    if isinstance(recent, dict):
        _append_filing_rows(filings, recent)

    for file_meta in body.get("filings", {}).get("files") or []:
        if not isinstance(file_meta, dict):
            continue
        name = str(file_meta.get("name") or "").strip()
        if not name:
            continue
        chunk_url = f"https://data.sec.gov/submissions/{name}"
        try:
            chunk = json.loads(_http_get(chunk_url, user_agent=user_agent).decode("utf-8"))
        except urllib.error.HTTPError:
            continue
        if isinstance(chunk, dict):
            _append_filing_rows(filings, chunk)
    return filings


def _earliest_statutory_filing(
    filings: list[tuple[str, str, str]],
) -> tuple[str, str, str]:
    """Return (acceptance_iso, filing_date, form) for the earliest registration-class filing."""

    if not filings:
        return "", "", ""

    ranked = sorted(filings, key=lambda row: row[0])

    def _matches(form_upper: str, prefixes: tuple[str, ...]) -> bool:
        return any(form_upper.startswith(prefix) for prefix in prefixes)

    for filing_date, form, accepted in ranked:
        form_upper = form.upper()
        if _matches(form_upper, STATUTORY_FORM_PREFIXES):
            timestamp = accepted.strip() or f"{filing_date}T00:00:00Z"
            return timestamp, filing_date, form

    for filing_date, form, accepted in ranked:
        form_upper = form.upper()
        if _matches(form_upper, STATUTORY_FORM_FALLBACK_PREFIXES):
            timestamp = accepted.strip() or f"{filing_date}T00:00:00Z"
            return timestamp, filing_date, form

    filing_date, form, accepted = ranked[0]
    timestamp = accepted.strip() or f"{filing_date}T00:00:00Z"
    return timestamp, filing_date, form


def _fetch_sec_row(
    *,
    catalog_id: str,
    symbol: str,
    sec_entry: dict[str, Any],
    user_agent: str,
    geocode: bool,
) -> Optional[dict[str, Any]]:
    cik = int(sec_entry.get("cik_str") or 0)
    if not cik:
        return None
    url = SEC_SUBMISSIONS_URL.format(cik=cik)
    try:
        body = json.loads(_http_get(url, user_agent=user_agent).decode("utf-8"))
    except urllib.error.HTTPError:
        return None

    legal_name = str(body.get("name") or sec_entry.get("title") or "").strip()
    if not legal_name:
        return None

    addresses = body.get("addresses") if isinstance(body.get("addresses"), dict) else {}
    business = addresses.get("business") if isinstance(addresses.get("business"), dict) else {}
    mailing = addresses.get("mailing") if isinstance(addresses.get("mailing"), dict) else {}
    inc_state = str(body.get("stateOfIncorporation") or "").strip().upper()
    hq = _format_sec_address(business)
    registered_office = _format_sec_address(mailing)

    venue_label, venue_coords = state_sos_venue(inc_state)
    filing_location = venue_label
    if registered_office:
        filing_location = f"{venue_label} · Registered office (SEC): {registered_office}"

    filings = _collect_sec_filings(body, user_agent=user_agent)
    filing_ts, filing_date, filing_form = _earliest_statutory_filing(filings)

    row: dict[str, Any] = {
        "id": catalog_id,
        "ticker": symbol,
        "cik": str(cik),
        "legal_entity_name": legal_name,
        "company_name": legal_name,
        "headquarters_location": hq,
        "llc_original_filing_location": filing_location,
        "llc_original_filing_source": "sec_edgar",
        "llc_original_filing_notes": (
            f"Statutory venue = state filing office ({inc_state or 'US'}). "
            f"Timestamp = SEC acceptance of earliest registration-class filing "
            f"({filing_form or 'n/a'} on {filing_date or 'n/a'})."
        ),
        "headquarters_source": "sec_edgar",
        "registry_source": "sec_edgar",
        "registry_jurisdiction": "US",
        "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    if filing_ts:
        row["llc_original_filing_timestamp_utc"] = filing_ts
    if venue_coords:
        row["llc_original_filing_latitude"] = venue_coords[0]
        row["llc_original_filing_longitude"] = venue_coords[1]

    if geocode and hq:
        hq_coords = geocode_us_address(
            hq,
            user_agent=user_agent,
            fallback_state=inc_state,
            allow_state_sos_fallback=False,
        )
        if hq_coords:
            row["headquarters_latitude"] = hq_coords[0]
            row["headquarters_longitude"] = hq_coords[1]

    return row


def _openregistry_jurisdiction(record: dict[str, Any]) -> Optional[str]:
    cc = str(record.get("cc") or "").strip().upper()
    if cc and cc != "US":
        for key, iso in COUNTRY_TO_JURISDICTION.items():
            if key.upper() == cc or (len(cc) == 2 and cc == iso):
                return iso
    country = str(record.get("co") or "").strip()
    if country in COUNTRY_TO_JURISDICTION:
        return COUNTRY_TO_JURISDICTION[country]
    return None


def _fetch_openregistry_row(
    *,
    catalog_id: str,
    record: dict[str, Any],
    user_agent: str,
) -> Optional[dict[str, Any]]:
    jurisdiction = _openregistry_jurisdiction(record)
    if not jurisdiction:
        return None

    query = str(record.get("ln") or record.get("nm") or record.get("sy") or "").strip()
    if not query:
        return None

    params = urllib.parse.urlencode(
        {"q": query, "jurisdiction": jurisdiction, "limit": "3"},
    )
    url = f"{OPENREGISTRY_SEARCH_URL}?{params}"
    try:
        payload = json.loads(_http_get(url, user_agent=user_agent).decode("utf-8"))
    except urllib.error.HTTPError:
        return None

    if payload.get("error"):
        return None

    results = payload.get("results") or []
    if not isinstance(results, list) or not results:
        return None

    hit = results[0]
    if not isinstance(hit, dict):
        return None

    company_name = str(hit.get("company_name") or "").strip()
    if not company_name:
        return None

    registered = str(hit.get("registered_address") or "").strip()
    incorporation = str(hit.get("incorporation_date") or "").strip()
    company_id = str(hit.get("company_id") or "").strip()

    row: dict[str, Any] = {
        "id": catalog_id,
        "legal_entity_name": company_name,
        "company_name": company_name,
        "headquarters_location": registered,
        "llc_original_filing_location": registered,
        "registry_source": "openregistry",
        "registry_jurisdiction": jurisdiction,
        "registry_company_id": company_id,
        "registry_license": OPENREGISTRY_LICENSE_BY_JURISDICTION.get(jurisdiction, "CC-BY"),
        "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    if incorporation:
        row["company_creation_datetime_utc"] = f"{incorporation}T00:00:00Z" if len(incorporation) == 10 else incorporation
        row["llc_original_filing_timestamp_utc"] = row["company_creation_datetime_utc"]
    return row


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Fetch SEC + OpenRegistry enrichment rows.")
    parser.add_argument("--catalog", type=Path, default=CATALOG_JSON)
    parser.add_argument("--output-dir", type=Path, default=SOURCES_DIR)
    parser.add_argument("--exchange", default=None, help="Comma-separated US exchanges.")
    parser.add_argument("--tickers", default=None, help="Comma-separated catalog ids or symbols.")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--skip", type=int, default=0)
    parser.add_argument("--delay", type=float, default=0.12, help="Delay between SEC requests.")
    parser.add_argument("--sec-only", action="store_true")
    parser.add_argument("--openregistry-only", action="store_true")
    parser.add_argument("--user-agent", default=DEFAULT_USER_AGENT)
    parser.add_argument(
        "--no-geocode",
        action="store_true",
        help="Skip US Census / SOS coordinate enrichment (faster bulk runs).",
    )
    args = parser.parse_args(argv)
    geocode = not args.no_geocode

    if not args.catalog.exists():
        print(f"catalog.json not found: {args.catalog}", file=sys.stderr)
        return 1

    catalog = json.loads(args.catalog.read_text(encoding="utf-8"))
    if not isinstance(catalog, list):
        print("catalog.json must be an array", file=sys.stderr)
        return 1

    tickers_filter: Optional[set[str]] = None
    if args.tickers:
        tickers_filter = {t.strip().upper() for t in args.tickers.split(",") if t.strip()}

    exchanges = None
    if args.exchange:
        exchanges = {e.strip().upper() for e in args.exchange.split(",") if e.strip()}

    queue: list[dict[str, Any]] = []
    for record in catalog:
        if not isinstance(record, dict):
            continue
        catalog_id = _normalize_ticker_id(record)
        symbol = str(record.get("sy") or catalog_id).strip().upper()
        if tickers_filter and catalog_id not in tickers_filter and symbol not in tickers_filter:
            continue
        if exchanges and str(record.get("ex") or "").upper() not in exchanges:
            continue
        queue.append(record)

    queue.sort(key=lambda r: _normalize_ticker_id(r))
    if args.skip:
        queue = queue[args.skip :]
    if args.limit is not None:
        queue = queue[: args.limit]

    args.output_dir.mkdir(parents=True, exist_ok=True)
    sec_path = args.output_dir / "sec-edgar.ndjson"
    or_path = args.output_dir / "openregistry.ndjson"

    sec_rows: list[dict[str, Any]] = []
    or_rows: list[dict[str, Any]] = []

    sec_index: dict[str, dict[str, Any]] = {}
    if not args.openregistry_only:
        print("Loading SEC company tickers index…")
        sec_index = _load_sec_ticker_index(args.user_agent)

    for index, record in enumerate(queue, start=1):
        catalog_id = _normalize_ticker_id(record)
        symbol = str(record.get("sy") or catalog_id).strip().upper()
        exchange = str(record.get("ex") or "").upper()
        is_us = str(record.get("cc") or "").upper() == "US" or exchange in US_EXCHANGES

        if is_us and not args.openregistry_only:
            sec_entry = sec_index.get(symbol)
            if sec_entry:
                row = _fetch_sec_row(
                    catalog_id=catalog_id,
                    symbol=symbol,
                    sec_entry=sec_entry,
                    user_agent=args.user_agent,
                    geocode=geocode,
                )
                if row:
                    sec_rows.append(row)
                    print(f"  [{index}/{len(queue)}] SEC {catalog_id}: {row['legal_entity_name']}")
                else:
                    print(f"  [{index}/{len(queue)}] SEC {catalog_id}: no submission data", file=sys.stderr)
            else:
                print(f"  [{index}/{len(queue)}] SEC {catalog_id}: not in SEC ticker index", file=sys.stderr)
            time.sleep(args.delay)

        if not args.sec_only and not is_us:
            row = _fetch_openregistry_row(
                catalog_id=catalog_id,
                record=record,
                user_agent=args.user_agent,
            )
            if row:
                or_rows.append(row)
                print(
                    f"  [{index}/{len(queue)}] OR {catalog_id}: "
                    f"{row['legal_entity_name']} ({row['registry_jurisdiction']})"
                )
            time.sleep(max(args.delay, 0.35))

    sec_path.write_text(
        "\n".join(json.dumps(row, ensure_ascii=False) for row in sec_rows) + ("\n" if sec_rows else ""),
        encoding="utf-8",
    )
    or_path.write_text(
        "\n".join(json.dumps(row, ensure_ascii=False) for row in or_rows) + ("\n" if or_rows else ""),
        encoding="utf-8",
    )

    print(f"Wrote {len(sec_rows)} SEC rows to {sec_path}")
    print(f"Wrote {len(or_rows)} OpenRegistry rows to {or_path}")
    print("Next: npm run enrichment:build && npm run prepare:data")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
