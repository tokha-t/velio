from __future__ import annotations

import copy
import json
import re
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator

from .corpus import load_documents, load_research_documents, normalize
from .paths import BUILD_ROOT, ROOT
from .status import base_status, effective_date_for_record, enactment_from_source, status_at

AS_OF = date(2026, 10, 1)
CONFIG_PATH = ROOT / "config" / "test_rule_map.yaml"
SCHEMA_PATH = ROOT / "starter_pack" / "schema" / "rule_record.schema.json"
SUBMISSION_PATH = ROOT / "submission" / "rules.json"

RECALL_CHECKLIST = {
    "CA Civ 1947.12": r"1947\.12",
    "CA Civ 1946.2": r"1946\.2",
    "CA Civ 1950.5": r"1950\.5",
    "CA Civ 1950.6": r"1950\.6",
    "CA Gov 12955": r"12955",
    "CA AB 325": r"AB\s*325|16729",
    "SF ch. 37": r"S\.F\..*(?:ch\.?\s*37|37\.10C)|37\.10C",
    "LA RSO": r"L\.A\..*RSO|Rent Stabilization Ordinance",
    "San Diego 98.1101-98.1104": r"98\.110[1-4]",
    "Berkeley 13.63": r"13\.63",
    "Santa Ana NS-3090": r"NS-3090",
    "NJ 2A:18-61.1": r"2A:18-61\.1",
    "NJ 46:8-21.2": r"46:8-21\.2",
    "NJ P.L.2025 c.405": r"2025,?\s*c\.?\s*405",
    "NJ Fair Chance P.L.2021 c.110": r"2021,?\s*c\.?\s*110",
    "NJ FAIR P.L.2026 c.43": r"2026,?\s*c\.?\s*43|FAIR",
    "JC 218-12": r"218-12|Jersey City.*algorithm",
    "Hoboken ch. 158 Art. II": r"Hoboken.*158|158.*Hoboken",
    "MA c.40P": r"40P",
    "MA c.186 15B": r"186.*15B|15B",
    "MA c.112 87DDD": r"112.*87DDD|87DDD",
    "MA S.2983": r"S\.?\s*2983",
    "MA H.5222": r"H\.?\s*5222",
}


def _normalized_citation(citation: str) -> str:
    return normalize(citation).lower()


def _source_rank(record: dict[str, Any]) -> tuple[int, float, str, str]:
    # The required preference is official sources, then confidence. The final
    # fields make equal candidates deterministic without encoding any law.
    return (
        1 if record.get("source_tier") == "official" else 0,
        float(record.get("confidence") or 0),
        record.get("source_doc_id", ""),
        record.get("citation", ""),
    )


def _load_test_patterns() -> dict[str, list[str]]:
    payload = yaml.safe_load(CONFIG_PATH.read_text()) or {}
    return payload.get("test_rule_ids", {})


def _test_rule_ids(record: dict[str, Any], patterns: dict[str, list[str]]) -> list[str]:
    searchable = f"{record.get('citation', '')}\n{record.get('title', '')}"
    return sorted(
        test_id
        for test_id, expressions in patterns.items()
        if any(re.search(expression, searchable, re.IGNORECASE) for expression in expressions)
    )


def _source_texts() -> dict[str, str]:
    return {document.doc_id: document.raw_text for document in load_documents() + load_research_documents()}


def _merge_group(records: list[dict[str, Any]], source_texts: dict[str, str], patterns: dict[str, list[str]]) -> dict[str, Any] | None:
    primary = sorted(records, key=_source_rank, reverse=True)[0]
    if primary.get("doc_kind") == "motion":
        return None
    result = copy.deepcopy(primary)
    documents = sorted({record["source_doc_id"] for record in records})
    result["also_in_docs"] = [doc_id for doc_id in documents if doc_id != primary["source_doc_id"]]
    result["exemptions"] = sorted({item.strip() for record in records for item in record.get("exemptions", []) if item.strip()})
    result["effective_rule_text"] = result.get("effective_rule_text") or result.get("effective_date_text")
    source_text = source_texts.get(primary["source_doc_id"])
    if source_text is None:
        raise KeyError(f"No source text loaded for {primary['source_doc_id']}")
    enacted, enacted_date = enactment_from_source(source_text)
    result["enacted_date"] = enacted_date.isoformat() if enacted_date else None
    effective_date = effective_date_for_record(result, enacted_date=enacted_date, enacted=enacted)
    result["effective_date"] = effective_date.isoformat() if effective_date else None
    result["base_status"] = base_status(
        doc_kind=result["doc_kind"],
        citation=result["citation"],
        title=result.get("title", ""),
        enacted=enacted,
    )
    result["status"] = status_at(base=result["base_status"], effective_date=effective_date, as_of=AS_OF)
    result["test_rule_ids"] = _test_rule_ids(result, patterns)
    return result


def _coverage_predicates(record: dict[str, Any]) -> list[dict[str, Any]]:
    # Tenant-level predicates are informative but never decide whether a rule
    # reaches an address.  A record containing only those is a companion page
    # with no address-coverage predicates.
    return [
        predicate
        for predicate in (record.get("coverage_conditions") or {}).get("predicates", [])
        if predicate.get("type") != "tenant_level_conditions"
    ]


def _same_law_markers(record: dict[str, Any]) -> set[str]:
    """Extract conservative law identifiers from a citation/title pair."""
    text = f"{record.get('citation', '')} {record.get('title', '')}"
    markers = {
        f"chapter:{value}"
        for value in re.findall(r"\bch(?:apter)?\.?\s*(\d+(?:\.\d+)*)\b", text, re.IGNORECASE)
    }
    markers.update(
        f"acronym:{value.lower()}"
        for value in re.findall(r"\(([A-Z][A-Z0-9]{1,})\)", text)
    )
    return markers


def _merge_same_law_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Fold a predicate-less companion page into the covered version of a law."""
    covered = [copy.deepcopy(record) for record in records if _coverage_predicates(record)]
    companions = [record for record in records if not _coverage_predicates(record)]
    retained = covered[:]
    for companion in companions:
        markers = _same_law_markers(companion)
        candidates = [record for record in retained if markers & _same_law_markers(record)]
        if not candidates:
            retained.append(copy.deepcopy(companion))
            continue
        target = sorted(candidates, key=_source_rank, reverse=True)[0]
        documents = {
            target.get("source_doc_id"),
            companion.get("source_doc_id"),
            *(target.get("also_in_docs") or []),
            *(companion.get("also_in_docs") or []),
        }
        target["also_in_docs"] = sorted(
            document for document in documents if document and document != target.get("source_doc_id")
        )
        target["exemptions"] = sorted({
            item.strip()
            for record in (target, companion)
            for item in (record.get("exemptions") or [])
            if item.strip()
        })
        for field in ("key_value", "requirement"):
            if not target.get(field) and companion.get(field):
                target[field] = companion[field]
    return retained


def merge_records(records: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], int]:
    patterns = _load_test_patterns()
    source_texts = _source_texts()
    groups: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        if not record.get("quote_verified"):
            raise ValueError(f"Unverified quote in {record.get('source_doc_id')} {record.get('citation')}")
        key = (record["jurisdiction"], record["category"], _normalized_citation(record["citation"]))
        groups[key].append(record)
    merged: list[dict[str, Any]] = []
    dropped_motions = 0
    for key in sorted(groups):
        item = _merge_group(groups[key], source_texts, patterns)
        if item is None:
            dropped_motions += 1
        else:
            merged.append(item)
    merged = _merge_same_law_records(merged)
    for item in merged:
        item["test_rule_ids"] = _test_rule_ids(item, patterns)
    merged.sort(key=lambda item: (item["jurisdiction"], item["category"], item["citation"]))
    for index, item in enumerate(merged, start=1):
        item["team_rule_id"] = f"r-{index:04d}"
    return merged, dropped_motions


def _submission_record(record: dict[str, Any]) -> dict[str, Any]:
    output = copy.deepcopy(record)
    output["exemptions"] = "; ".join(output.get("exemptions", [])) or None
    return output


def validate_submission(records: list[dict[str, Any]]) -> None:
    validator = Draft202012Validator(json.loads(SCHEMA_PATH.read_text()))
    errors = []
    for record in records:
        errors.extend(f"{record['team_rule_id']}: {error.message}" for error in validator.iter_errors(record))
    if errors:
        raise ValueError("rules.json schema validation failed:\n" + "\n".join(errors))


def _print_cp1(rules: list[dict[str, Any]], dropped_motions: int) -> None:
    by_jurisdiction_category = Counter((item["jurisdiction"], item["category"]) for item in rules)
    print("CP1 rules per jurisdiction × category")
    for (jurisdiction, category), count in sorted(by_jurisdiction_category.items()):
        print(f"  {jurisdiction}\t{category}\t{count}")
    print("CP1 statuses")
    for status, count in sorted(Counter(item["status"] for item in rules).items()):
        print(f"  {status}\t{count}")
    quote_rate = 100 * sum(bool(item.get("quote_verified")) for item in rules) / len(rules) if rules else 0
    print(f"CP1 quote verification\t{quote_rate:.1f}%")
    print(f"CP1 dropped motions\t{dropped_motions}")
    print("CP1 recall checklist")
    citations = "\n".join(f"{item['citation']}\n{item['title']}" for item in rules)
    for name, expression in RECALL_CHECKLIST.items():
        print(f"  {name}\t{'found' if re.search(expression, citations, re.IGNORECASE) else 'missing'}")
    print("CP1 anchors")
    for test_id in ("CA-ALG-01", "NJ-ALG-01", "MA-ALG-P1", "MA-ALG-P2"):
        matches = [item for item in rules if test_id in item["test_rule_ids"]]
        summary = ", ".join(f"{item['team_rule_id']} eff={item['effective_date']} status={item['status']}" for item in matches) or "missing"
        print(f"  {test_id}\t{summary}")
    c40p = [item for item in rules if re.search(r"40P", item["citation"], re.IGNORECASE)]
    summary = ", ".join(f"{item['team_rule_id']} status={item['status']}" for item in c40p) or "missing"
    print(f"  c.40P\t{summary}")


def run() -> list[dict[str, Any]]:
    source = BUILD_ROOT / "extracted_records.json"
    if not source.exists():
        raise FileNotFoundError(f"Missing {source}; run navigator extract first")
    payload = json.loads(source.read_text())
    raw_records = payload.get("rules", payload)
    rules, dropped_motions = merge_records(raw_records)
    internal = {"rules": rules}
    BUILD_ROOT.mkdir(parents=True, exist_ok=True)
    (BUILD_ROOT / "rules_internal.json").write_text(json.dumps(internal, indent=2, sort_keys=True) + "\n")
    submission = [_submission_record(rule) for rule in rules]
    validate_submission(submission)
    SUBMISSION_PATH.parent.mkdir(parents=True, exist_ok=True)
    SUBMISSION_PATH.write_text(json.dumps({"rules": submission}, indent=2, sort_keys=True) + "\n")
    _print_cp1(rules, dropped_motions)
    return rules
