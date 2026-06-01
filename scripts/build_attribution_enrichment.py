#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CATALOG = ROOT / "public" / "data" / "catalog.json"
DEFAULT_OUTPUT = ROOT / "public" / "data" / "enrichment" / "attribution-safe.json"

ALLOWED_REGISTRY_LICENSES = {
    "CC0",
    "CC-BY",
    "CC BY",
    "CCBY",
    "OGL",
    "NLOD",
    "ETALAB",
    "PUBLIC-DOMAIN",
    "PUBLIC DOMAIN",
    "PD",
}

FIELD_PRIORITIES: dict[str, list[str]] = {
    "ln": ["openregistry", "sec_edgar", "gleif"],
    "lt": ["openregistry", "sec_edgar"],
    "ll": ["openregistry", "sec_edgar"],
    "lc": ["sec_edgar"],
    "hq": ["openregistry", "gleif", "wikidata", "sec_edgar"],
    "hc": ["gleif", "wikidata"],
    "cd": ["openregistry", "wikidata", "gleif", "sec_edgar"],
    "br": ["openregistry", "registry"],
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


def _normalize_location(value: str) -> str:
    if not value:
        return ""
    return " ".join(value.replace("|", ",").replace(";", ",").split()).strip(", ")


def _normalize_coordinate(value: object, *, minimum: float, maximum: float) -> float | None:
    if value in (None, ""):
        return None
    try:
        number = float(str(value).strip())
    except ValueError:
        return None
    if number < minimum or number > maximum:
        return None
    return round(number, 6)


def _coordinate_pair(lat_value: object, lon_value: object) -> list[float] | None:
    lat = _normalize_coordinate(lat_value, minimum=-90, maximum=90)
    lon = _normalize_coordinate(lon_value, minimum=-180, maximum=180)
    if lat is None or lon is None:
        return None
    return [lat, lon]


def _normalize_timestamp(value: object) -> str:
    candidate = _as_text(value)
    if not candidate:
        return ""
    if len(candidate) == 10:
        candidate = f"{candidate}T00:00:00Z"
    normalized = candidate.replace(" ", "T")
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    else:
        parsed = parsed.astimezone(timezone.utc)
    return parsed.strftime("%Y-%m-%dT%H:%M:%SZ")


def _now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _normalize_ticker_id(row: dict[str, Any]) -> str:
    """Canonical overlay key — matches catalog.json `id` (bare ticker, not EX:SYMBOL)."""

    direct = _pick_text(row, "id", "normalized_ticker", "ticker")
    if direct:
        if ":" in direct:
            return direct.upper()
        return direct.upper()
    symbol = _pick_text(row, "symbol", "sy")
    if symbol:
        return symbol.upper()
    return ""


def _read_records(path: Path) -> list[dict[str, Any]]:
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        return []
    if path.suffix.lower() == ".json":
        payload = json.loads(text)
        if isinstance(payload, list):
            return [item for item in payload if isinstance(item, dict)]
        if isinstance(payload, dict):
            items = payload.get("records")
            if isinstance(items, list):
                return [item for item in items if isinstance(item, dict)]
        return []
    records: list[dict[str, Any]] = []
    for line in text.splitlines():
        candidate = line.strip()
        if not candidate:
            continue
        parsed = json.loads(candidate)
        if isinstance(parsed, dict):
            records.append(parsed)
    return records


def _branch_locations_from_row(row: dict[str, Any]) -> list[object]:
    raw = row.get("branch_locations") or row.get("branches") or row.get("br")
    if raw in (None, "", []):
        return []
    if isinstance(raw, str):
        stripped = raw.strip()
        if not stripped:
            return []
        try:
            raw = json.loads(stripped)
        except json.JSONDecodeError:
            return [_normalize_location(part) for part in stripped.split("|") if _normalize_location(part)]
    if isinstance(raw, dict):
        raw = [raw]
    if not isinstance(raw, list):
        return []
    return raw


def _extract_sec(row: dict[str, Any]) -> dict[str, Any]:
    record: dict[str, Any] = {}
    ln = _pick_text(row, "legal_entity_name", "ln", "name", "entity_name")
    lt = _pick_text(
        row,
        "llc_original_filing_timestamp_utc",
        "filing_timestamp_utc",
        "lt",
        "filedAt",
    )
    ll = _normalize_location(_pick_text(row, "llc_original_filing_location", "filing_location", "ll", "address"))
    hq = _normalize_location(
        _pick_text(row, "headquarters_location", "headquarters_address", "hq", "business_address")
    )
    lc = _coordinate_pair(
        row.get("llc_original_filing_latitude") or row.get("filing_latitude") or row.get("lat"),
        row.get("llc_original_filing_longitude") or row.get("filing_longitude") or row.get("lon"),
    )
    hc = _coordinate_pair(
        row.get("headquarters_latitude") or row.get("hq_latitude"),
        row.get("headquarters_longitude") or row.get("hq_longitude") or row.get("hq_lon"),
    )
    if ln:
        record["ln"] = ln
    if lt:
        try:
            record["lt"] = _normalize_timestamp(lt)
        except ValueError:
            pass
    if ll:
        record["ll"] = ll
    if hq:
        record["hq"] = hq
    if lc:
        record["lc"] = lc
    if hc:
        record["hc"] = hc
    cik = _pick_text(row, "cik")
    jurisdiction = _pick_text(row, "registry_jurisdiction") or "US"
    if cik or _pick_text(row, "registry_source") == "sec_edgar":
        record["registry"] = {
            "source": "sec_edgar",
            "jurisdiction": jurisdiction,
            "companyId": cik,
            "license": "PUBLIC-DOMAIN",
        }
    if record:
        record["source"] = "sec_edgar"
        record["updatedAt"] = _normalize_timestamp(
            _pick_text(row, "updated_at", "retrieved_at", "as_of", "timestamp") or _now_utc()
        )
    return record


def _extract_gleif(row: dict[str, Any]) -> dict[str, Any]:
    record: dict[str, Any] = {}
    hq = _normalize_location(
        _pick_text(
            row,
            "headquarters_location",
            "headquarters_address",
            "hq",
            "legal_address",
            "address",
        )
    )
    hc = _coordinate_pair(
        row.get("headquarters_latitude") or row.get("hq_latitude") or row.get("lat"),
        row.get("headquarters_longitude") or row.get("hq_longitude") or row.get("lon"),
    )
    cd = _pick_text(row, "company_creation_datetime_utc", "inception_date", "founded_on", "cd")
    if hq:
        record["hq"] = hq
    if hc:
        record["hc"] = hc
    if cd:
        try:
            record["cd"] = _normalize_timestamp(cd)
        except ValueError:
            pass
    if record:
        record["source"] = "gleif"
        record["updatedAt"] = _normalize_timestamp(
            _pick_text(row, "updated_at", "retrieved_at", "as_of", "timestamp") or _now_utc()
        )
    return record


def _extract_wikidata(row: dict[str, Any]) -> dict[str, Any]:
    record: dict[str, Any] = {}
    cd = _pick_text(row, "company_creation_datetime_utc", "founded", "inception", "cd")
    hq = _normalize_location(_pick_text(row, "headquarters_location", "hq", "headquarters"))
    hc = _coordinate_pair(
        row.get("headquarters_latitude") or row.get("hq_latitude") or row.get("lat"),
        row.get("headquarters_longitude") or row.get("hq_longitude") or row.get("lon"),
    )
    if cd:
        try:
            record["cd"] = _normalize_timestamp(cd)
        except ValueError:
            pass
    if hq:
        record["hq"] = hq
    if hc:
        record["hc"] = hc
    if record:
        record["source"] = "wikidata"
        record["updatedAt"] = _normalize_timestamp(
            _pick_text(row, "updated_at", "retrieved_at", "as_of", "timestamp") or _now_utc()
        )
    return record


def _extract_openregistry(row: dict[str, Any], *, license_name: str = "") -> dict[str, Any]:
    """Normalize rows from fetch_registry_enrichment.py or raw MCP search/profile payloads."""

    record: dict[str, Any] = {}
    ln = _pick_text(
        row,
        "legal_entity_name",
        "ln",
        "company_name",
        "registered_name",
        "title",
    )
    lt = _pick_text(
        row,
        "llc_original_filing_timestamp_utc",
        "incorporation_date",
        "incorporation_datetime_utc",
        "lt",
    )
    ll = _normalize_location(
        _pick_text(
            row,
            "llc_original_filing_location",
            "registered_address",
            "registered_office",
            "ll",
        )
    )
    hq = _normalize_location(
        _pick_text(row, "headquarters_location", "registered_address", "hq", "address")
    )
    cd = _pick_text(row, "company_creation_datetime_utc", "incorporation_date", "cd")
    branches = _branch_locations_from_row(row)

    if ln:
        record["ln"] = ln
    if lt:
        try:
            record["lt"] = _normalize_timestamp(lt)
        except ValueError:
            pass
    if ll:
        record["ll"] = ll
    if hq:
        record["hq"] = hq
    if cd:
        try:
            record["cd"] = _normalize_timestamp(cd)
        except ValueError:
            pass
    if branches:
        record["br"] = branches

    registry_id = _pick_text(row, "registry_company_id", "company_id")
    jurisdiction = _pick_text(row, "registry_jurisdiction", "jurisdiction")
    if registry_id or jurisdiction:
        record["registry"] = {
            "source": "openregistry",
            "jurisdiction": jurisdiction,
            "companyId": registry_id,
            "license": license_name or _pick_text(row, "registry_license", "license") or "CC-BY",
        }

    if record:
        record["source"] = "openregistry"
        record["updatedAt"] = _normalize_timestamp(
            _pick_text(row, "updated_at", "retrieved_at", "as_of", "timestamp") or _now_utc()
        )
    return record


def _extract_registry(row: dict[str, Any], *, license_name: str) -> dict[str, Any]:
    registry_source = _pick_text(row, "registry_source", "source")
    if registry_source == "openregistry":
        return _extract_openregistry(row, license_name=license_name)

    normalized_license = license_name.upper().strip()
    if normalized_license not in ALLOWED_REGISTRY_LICENSES:
        return {}
    record: dict[str, Any] = {}
    branches = _branch_locations_from_row(row)
    if branches:
        record["br"] = branches
    if record:
        record["source"] = "registry"
        record["license"] = normalized_license
        record["updatedAt"] = _normalize_timestamp(
            _pick_text(row, "updated_at", "retrieved_at", "as_of", "timestamp") or _now_utc()
        )
    return record


def _priority_rank(field: str, source: str) -> int:
    priorities = FIELD_PRIORITIES.get(field, [])
    if source in priorities:
        return priorities.index(source)
    return 999


def _merge_into_state(state: dict[str, Any], payload: dict[str, Any]) -> None:
    source = _pick_text(payload, "source")
    updated_at = _pick_text(payload, "updatedAt") or _now_utc()
    if payload.get("registry"):
        state["registry"] = payload["registry"]
    for field in ("ln", "lt", "ll", "lc", "hq", "hc", "cd", "br"):
        value = payload.get(field)
        if value in (None, "", []):
            continue
        rank = _priority_rank(field, source)
        current_rank = int(state.get("_rank", {}).get(field, 999))
        if rank > current_rank:
            continue
        state[field] = value
        state.setdefault("fieldSource", {})[field] = source
        state.setdefault("fieldUpdatedAt", {})[field] = updated_at
        state.setdefault("_rank", {})[field] = rank


def _build_overlay(
    *,
    catalog_ids: set[str],
    sec_file: Path | None,
    gleif_file: Path | None,
    wikidata_file: Path | None,
    registry_files: list[Path],
    registry_licenses: list[str],
) -> tuple[dict[str, dict[str, Any]], dict[str, int]]:
    state_by_ticker: dict[str, dict[str, Any]] = {}
    counters = {
        "catalogTickers": len(catalog_ids),
        "secRows": 0,
        "gleifRows": 0,
        "wikidataRows": 0,
        "registryRows": 0,
        "skippedUnknownTicker": 0,
    }

    def consume(rows: list[dict[str, Any]], extractor: Any, counter_key: str, **kwargs: Any) -> None:
        for row in rows:
            ticker = _normalize_ticker_id(row)
            if not ticker or ticker not in catalog_ids:
                counters["skippedUnknownTicker"] += 1
                continue
            payload = extractor(row, **kwargs)
            if not payload:
                continue
            counters[counter_key] += 1
            state = state_by_ticker.setdefault(ticker, {})
            _merge_into_state(state, payload)

    if sec_file and sec_file.exists():
        consume(_read_records(sec_file), _extract_sec, "secRows")
    if gleif_file and gleif_file.exists():
        consume(_read_records(gleif_file), _extract_gleif, "gleifRows")
    if wikidata_file and wikidata_file.exists():
        consume(_read_records(wikidata_file), _extract_wikidata, "wikidataRows")
    for file_path, license_name in zip(registry_files, registry_licenses):
        if file_path.exists():
            consume(_read_records(file_path), _extract_registry, "registryRows", license_name=license_name)

    overlay: dict[str, dict[str, Any]] = {}
    for ticker, state in state_by_ticker.items():
        record: dict[str, Any] = {}
        for key in ("ln", "lt", "ll", "lc", "hq", "hc", "cd", "br"):
            value = state.get(key)
            if value not in (None, "", []):
                record[key] = value
        field_source: dict[str, str] = state.get("fieldSource", {})
        if "ln" in record:
            record["ls"] = field_source.get("ln", "")
        if "lt" in record or "ll" in record or "lc" in record:
            if field_source.get("lt") == "sec_edgar" or field_source.get("ll") == "sec_edgar" or field_source.get("lc") == "sec_edgar":
                record["fs"] = "sec_edgar"
            elif field_source.get("lt") == "openregistry" or field_source.get("ll") == "openregistry":
                record["fs"] = "openregistry"
        if "hq" in record or "hc" in record:
            if field_source.get("hq"):
                record["hs"] = field_source["hq"]
            elif field_source.get("hc"):
                record["hs"] = field_source["hc"]
        if "br" in record:
            record["bs"] = field_source.get("br", "registry")
        if state.get("registry"):
            record["registry"] = state["registry"]
        record["meta"] = {
            "fieldSource": field_source,
            "fieldUpdatedAt": state.get("fieldUpdatedAt", {}),
        }
        overlay[ticker] = record
    counters["overlayTickers"] = len(overlay)
    return overlay, counters


def _load_catalog_ids(path: Path) -> set[str]:
    rows = json.loads(path.read_text(encoding="utf-8"))
    ids: set[str] = set()
    if not isinstance(rows, list):
        return ids
    for row in rows:
        if isinstance(row, dict):
            ticker = _normalize_ticker_id(row)
            if ticker:
                ids.add(ticker)
    return ids


def _discover_source_files(sources_dir: Path) -> tuple[Path | None, list[Path], list[str]]:
    """Auto-load fetch_registry_enrichment.py outputs from public/data/enrichment/sources/."""

    sec_file: Path | None = None
    registry_files: list[Path] = []
    registry_licenses: list[str] = []

    if not sources_dir.exists():
        return sec_file, registry_files, registry_licenses

    sec_candidate = sources_dir / "sec-edgar.ndjson"
    if sec_candidate.exists():
        sec_file = sec_candidate

    or_candidate = sources_dir / "openregistry.ndjson"
    if or_candidate.exists():
        registry_files.append(or_candidate)
        registry_licenses.append("CC-BY")

    return sec_file, registry_files, registry_licenses


def main() -> None:
    parser = argparse.ArgumentParser(description="Build attribution-safe enrichment overlay for the catalog.")
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--sources-dir",
        type=Path,
        default=ROOT / "public" / "data" / "enrichment" / "sources",
        help="Auto-merge sec-edgar.ndjson and openregistry.ndjson when present.",
    )
    parser.add_argument("--sec", type=Path, help="SEC EDGAR normalized rows (json or ndjson)")
    parser.add_argument("--gleif", type=Path, help="GLEIF normalized rows (json or ndjson)")
    parser.add_argument("--wikidata", type=Path, help="Wikidata normalized rows (json or ndjson)")
    parser.add_argument(
        "--registry",
        action="append",
        type=Path,
        default=[],
        help="Per-country registry normalized rows (json or ndjson). Repeat for multiple files.",
    )
    parser.add_argument(
        "--registry-license",
        action="append",
        default=[],
        help="License label for each --registry file (e.g. OGL, NLOD, CC-BY).",
    )
    args = parser.parse_args()

    if len(args.registry) != len(args.registry_license):
        raise SystemExit("Each --registry input requires a matching --registry-license value.")

    auto_sec, auto_registry_files, auto_registry_licenses = _discover_source_files(args.sources_dir)
    sec_file = args.sec or auto_sec
    registry_files = list(args.registry) + auto_registry_files
    registry_licenses = list(args.registry_license) + auto_registry_licenses

    catalog_ids = _load_catalog_ids(args.catalog)
    overlay, counters = _build_overlay(
        catalog_ids=catalog_ids,
        sec_file=sec_file,
        gleif_file=args.gleif,
        wikidata_file=args.wikidata,
        registry_files=registry_files,
        registry_licenses=registry_licenses,
    )

    payload = {
        "schemaVersion": 1,
        "generatedAt": _now_utc(),
        "sources": {
            "sec": str(sec_file) if sec_file else "",
            "gleif": str(args.gleif) if args.gleif else "",
            "wikidata": str(args.wikidata) if args.wikidata else "",
            "registries": [str(path) for path in registry_files],
            "sourcesDir": str(args.sources_dir),
        },
        "policy": {
            "branchLocationsOptional": True,
            "allowedRegistryLicenses": sorted(ALLOWED_REGISTRY_LICENSES),
        },
        "summary": counters,
        "records": overlay,
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(overlay):,} enrichment records to {args.output}")


if __name__ == "__main__":
    main()
