"""Resolve sample addresses to legal places with cached Census geocoding."""

from __future__ import annotations

import argparse
import csv
import json
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Mapping

import requests

from .facts import derive_facts


BASE_URL = "https://geocoding.geo.census.gov/geocoder/geographies"
COMMON_PARAMS = {
    "benchmark": "Public_AR_Current",
    "vintage": "Current_Current",
    "layers": "all",
    "format": "json",
}
STATE_NAMES = {"CA": "California", "NJ": "New Jersey", "MA": "Massachusetts"}
CITY_ONLY_DATASETS = ("DataSF", "Boston assessor", "Cambridge assessor", "NJOGIS")
BOSTON_NEIGHBORHOODS = {
    "Allston",
    "Brighton",
    "Dorchester",
    "East Boston",
    "Hyde Park",
    "Jamaica Plain",
    "Mattapan",
    "Roxbury",
    "South Boston",
}


def _canonical_place(name: str) -> str:
    for suffix in (" city", " town", " borough", " village"):
        if name.lower().endswith(suffix):
            return name[: -len(suffix)]
    return name


def _dataset_city(row: Mapping[str, str]) -> str:
    postal_city = row["postal_city"].strip()
    if row["state"] == "MA" and postal_city in BOSTON_NEIGHBORHOODS:
        return "Boston"
    if postal_city == "San Ysidro":
        return "San Diego"
    return postal_city


def _request_json(endpoint: str, params: Mapping[str, str], attempts: int = 3) -> dict[str, Any]:
    error: Exception | None = None
    for attempt in range(attempts):
        try:
            response = requests.get(
                f"{BASE_URL}/{endpoint}", params={**COMMON_PARAMS, **params}, timeout=30
            )
            response.raise_for_status()
            return response.json()
        except (requests.RequestException, ValueError) as exc:
            error = exc
            if attempt + 1 < attempts:
                time.sleep(0.5 * (attempt + 1))
    raise RuntimeError(str(error))


def _first_match(data: Mapping[str, Any]) -> Mapping[str, Any] | None:
    matches = data.get("result", {}).get("addressMatches", [])
    return matches[0] if matches else None


def _query(row: Mapping[str, str], endpoint: str) -> dict[str, Any]:
    if endpoint == "onelineaddress":
        params = {
            "address": f"{row['street_address']}, {row['postal_city']}, "
            f"{row['state']} {row['zip']}"
        }
    else:
        params = {
            "street": row["street_address"],
            "city": row["postal_city"],
            "state": row["state"],
            "zip": row["zip"],
        }
    return _request_json(endpoint, params)


def _cache_path(cache_dir: Path, address_id: str) -> Path:
    return cache_dir / f"{address_id}.json"


def geocode_row(row: Mapping[str, str], cache_dir: Path) -> dict[str, Any]:
    """Run the one-line query, then component retry, storing the raw result."""
    cache_file = _cache_path(cache_dir, row["address_id"])
    if cache_file.exists():
        return json.loads(cache_file.read_text(encoding="utf-8"))

    cache_record: dict[str, Any] = {"address_id": row["address_id"], "attempts": []}
    for endpoint, method in (
        ("onelineaddress", "census_oneline"),
        ("address", "census_components"),
    ):
        try:
            data = _query(row, endpoint)
            match = _first_match(data)
            cache_record["attempts"].append({"method": method, "response": data})
            if match:
                cache_record["selected_method"] = method
                break
        except RuntimeError as exc:
            cache_record["attempts"].append({"method": method, "error": str(exc)})

    cache_file.write_text(
        json.dumps(cache_record, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return cache_record


def _selected_match(cache_record: Mapping[str, Any]) -> Mapping[str, Any] | None:
    selected = cache_record.get("selected_method")
    for attempt in cache_record.get("attempts", []):
        if attempt.get("method") == selected:
            return _first_match(attempt.get("response", {}))
    return None


def resolve_row(row: Mapping[str, str], cache_record: Mapping[str, Any]) -> dict[str, Any]:
    match = _selected_match(cache_record)
    dataset_city = _dataset_city(row)
    source_dataset = row["source_dataset"]

    place: Mapping[str, Any] | None = None
    county: Mapping[str, Any] | None = None
    if match:
        geographies = match.get("geographies", {})
        places = geographies.get("Incorporated Places", [])
        counties = geographies.get("Counties", [])
        place = places[0] if places else None
        county = counties[0] if counties else None

    if place:
        legal_city_name: str | None = _canonical_place(str(place["NAME"]))
        confidence = "high"
    elif match:
        legal_city_name = None
        confidence = "high"
    elif source_dataset.startswith(CITY_ONLY_DATASETS):
        legal_city_name = dataset_city
        confidence = "high"
    else:
        legal_city_name = dataset_city
        confidence = "low"

    legal_city = f"{legal_city_name}, {row['state']}" if legal_city_name else None
    stack = [row["state"]] + ([legal_city] if legal_city else [])
    coordinates = match.get("coordinates", {}) if match else {}
    geocode = {
        "matched": bool(match),
        "method": cache_record.get("selected_method", "dataset_fallback"),
        "place_name": place.get("NAME") if place else None,
        "place_geoid": place.get("GEOID") if place else None,
        "county": county.get("NAME") if county else None,
        "lat": coordinates.get("y"),
        "lon": coordinates.get("x"),
    }
    return {
        "address_id": row["address_id"],
        "street_address": row["street_address"],
        "postal_city": row["postal_city"],
        "state": row["state"],
        "zip": row["zip"],
        "geocode": geocode,
        "legal_city": legal_city,
        "stack": stack,
        "jurisdiction_confidence": confidence,
        "facts": derive_facts(row),
    }


def build_report(records: list[dict[str, Any]]) -> str:
    total = len(records)
    matched = [record for record in records if record["geocode"]["matched"]]
    confident = [
        record
        for record in records
        if record["geocode"]["place_name"]
        or record["jurisdiction_confidence"] == "high"
    ]
    mismatches = [
        record
        for record in records
        if record["legal_city"]
        and record["postal_city"] != record["legal_city"].rsplit(", ", 1)[0]
    ]
    unincorporated = [record for record in records if record["legal_city"] is None]
    low_confidence = [
        record for record in records if record["jurisdiction_confidence"] == "low"
    ]
    methods = Counter(record["geocode"]["method"] for record in records)

    lines = [
        "# Jurisdiction resolution report",
        "",
        "As of 2026-10-01. Not legal advice.",
        "",
        "## Summary",
        "",
        f"- Address rows: **{total}**",
        f"- Census address matches: **{len(matched)} / {total} ({len(matched) / total:.1%})**",
        f"- Place match or confident dataset fallback: **{len(confident)} / {total} ({len(confident) / total:.1%})**",
        f"- Postal city differs from legal city: **{len(mismatches)}**",
        f"- No incorporated place (state-only stack): **{len(unincorporated)}**",
        f"- Low-confidence dataset fallback: **{len(low_confidence)}**",
        "- Methods: " + ", ".join(f"`{key}` {methods[key]}" for key in sorted(methods)),
        "",
        "## Postal city differs from legal city",
        "",
        "| Address ID | Street | Postal city | Legal city | Method | Confidence |",
        "|---|---|---|---|---|---|",
    ]
    lines.extend(
        f"| {r['address_id']} | {r['street_address']} | {r['postal_city']} | "
        f"{r['legal_city']} | {r['geocode']['method']} | {r['jurisdiction_confidence']} |"
        for r in mismatches
    )
    if not mismatches:
        lines.append("| — | — | — | — | — | — |")

    for title, rows in (
        ("Unincorporated / state-only rows", unincorporated),
        ("Low-confidence rows", low_confidence),
    ):
        lines.extend(
            [
                "",
                f"## {title}",
                "",
                "| Address ID | Street | Postal city | County | Method |",
                "|---|---|---|---|---|",
            ]
        )
        lines.extend(
            f"| {r['address_id']} | {r['street_address']} | {r['postal_city']} | "
            f"{r['geocode']['county'] or '—'} | {r['geocode']['method']} |"
            for r in rows
        )
        if not rows:
            lines.append("| — | — | — | — | — |")
    return "\n".join(lines) + "\n"


def resolve_all(input_path: Path, output_path: Path, report_path: Path, cache_dir: Path) -> None:
    with input_path.open(newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))
    rows.sort(key=lambda row: row["address_id"])
    cache_dir.mkdir(parents=True, exist_ok=True)

    cache_records: dict[str, dict[str, Any]] = {}
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {executor.submit(geocode_row, row, cache_dir): row for row in rows}
        for future in as_completed(futures):
            row = futures[future]
            cache_records[row["address_id"]] = future.result()

    records = [resolve_row(row, cache_records[row["address_id"]]) for row in rows]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(records, indent=2) + "\n", encoding="utf-8")
    report_path.write_text(build_report(records), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path("starter_pack/data/sample_addresses.csv"))
    parser.add_argument("--output", type=Path, default=Path("build/addresses_resolved.json"))
    parser.add_argument("--report", type=Path, default=Path("build/jurisdiction_report.md"))
    parser.add_argument("--cache-dir", type=Path, default=Path("cache/geocode"))
    args = parser.parse_args()
    resolve_all(args.input, args.output, args.report, args.cache_dir)


if __name__ == "__main__":
    main()
