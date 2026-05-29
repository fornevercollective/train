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
    "lt": ["sec_edgar"],
    "ll": ["sec_edgar"],
    "lc": ["sec_edgar"],
    "hq": ["gleif", "wikidata"],
    "hc": ["gleif", "wikidata"],
    "cd": ["wikidata", "gleif"],
    "br": ["registry"],
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
    direct = _pick_text(row, "id", "normalized_ticker", "ticker")
    if direct:
        if ":" in direct:
            return direct.upper()
        exchange = _pick_text(row, "exchange", "ex")
        if exchange:
            return f"{exchange.upper()}:{direct.upper()}"
        return direct.upper()
    symbol = _pick_text(row, "symbol", "sy")
    exchange = _pick_text(row, "exchange", "ex")
    if symbol and exchange:
        return f"{exchange.upper()}:{symbol.upper()}"
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
    lt = _pick_text(
        row,
        "llc_original_filing_timestamp_utc",
        "filing_timestamp_utc",
        "lt",
        "filedAt",
    )
    ll = _normalize_location(_pick_text(row, "llc_original_filing_location", "filing_location", "ll", "address"))
    lc = _coordinate_pair(
        row.get("llc_original_filing_latitude") or row.get("filing_latitude") or row.get("lat"),
        row.get("llc_original_filing_longitude") or row.get("filing_longitude") or row.get("lon"),
    )
    if lt:
        try:
            record["lt"] = _normalize_timestamp(lt)
        except ValueError:
            pass
    if ll:
        record["ll"] = ll
    if lc:
        record["lc"] = lc
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


def _extract_registry(row: dict[str, Any], *, license_name: str) -> dict[str, Any]:
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
    for field in ("lt", "ll", "lc", "hq", "hc", "cd", "br"):
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
        for key in ("lt", "ll", "lc", "hq", "hc", "cd", "br"):
            value = state.get(key)
            if value not in (None, "", []):
                record[key] = value
        field_source: dict[str, str] = state.get("fieldSource", {})
        if "lt" in record or "ll" in record or "lc" in record:
            if field_source.get("lt") == "sec_edgar" or field_source.get("ll") == "sec_edgar" or field_source.get("lc") == "sec_edgar":
                record["fs"] = "sec_edgar"
        if "hq" in record or "hc" in record:
            if field_source.get("hq"):
                record["hs"] = field_source["hq"]
            elif field_source.get("hc"):
                record["hs"] = field_source["hc"]
        if "br" in record:
            record["bs"] = "registry"
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


def main() -> None:
    parser = argparse.ArgumentParser(description="Build attribution-safe enrichment overlay for the catalog.")
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
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

    catalog_ids = _load_catalog_ids(args.catalog)
    overlay, counters = _build_overlay(
        catalog_ids=catalog_ids,
        sec_file=args.sec,
        gleif_file=args.gleif,
        wikidata_file=args.wikidata,
        registry_files=args.registry,
        registry_licenses=args.registry_license,
    )

    payload = {
        "schemaVersion": 1,
        "generatedAt": _now_utc(),
        "sources": {
            "sec": str(args.sec) if args.sec else "",
            "gleif": str(args.gleif) if args.gleif else "",
            "wikidata": str(args.wikidata) if args.wikidata else "",
            "registries": [str(path) for path in args.registry],
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
