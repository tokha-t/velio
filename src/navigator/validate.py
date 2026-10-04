from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from .corpus import load_documents, load_research_documents
from .merge import SCHEMA_PATH
from .paths import BUILD_ROOT, ROOT
from .verify import verify_quote

SUBMISSION = ROOT / "submission"
WEB_VALIDATION = ROOT / "web" / "data" / "validation.json"
EXPECTED_CHANGES = {"T1": (250, 0), "T2": (90, 0), "T3": (140, 90), "T4": (110, 0), "T5": (0, 0)}


def _check(name: str, passed: bool, detail: str) -> dict[str, Any]:
    return {"name": name, "passed": passed, "detail": detail}


def _load(path: Path, key: str) -> list[dict[str, Any]]:
    return json.loads(path.read_text())[key]


def run() -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    errors_path = BUILD_ROOT / "extract_errors.json"
    extraction_errors = json.loads(errors_path.read_text()).get("errors", []) if errors_path.exists() else []
    checks.append(_check("extraction_complete", not extraction_errors, f"retry-exhausted chunks: {len(extraction_errors)}"))
    rules_path = SUBMISSION / "rules.json"
    lookups_path = SUBMISSION / "lookups.json"
    changes_path = SUBMISSION / "changes.json"
    if not rules_path.exists():
        checks.append(_check("schema", False, "submission/rules.json is missing"))
        rules: list[dict[str, Any]] = []
    else:
        rules = _load(rules_path, "rules")
        validator = Draft202012Validator(json.loads(SCHEMA_PATH.read_text()))
        errors = [f"{rule.get('team_rule_id')}: {error.message}" for rule in rules for error in validator.iter_errors(rule)]
        checks.append(_check("schema", not errors, "; ".join(errors) or f"{len(rules)} rules validate"))
    source_texts = {doc.doc_id: doc.raw_text for doc in load_documents() + load_research_documents()}
    unverified = [rule["team_rule_id"] for rule in rules if not rule.get("quote_verified") or not source_texts.get(rule.get("source_doc_id")) or verify_quote(rule["quoted_span"], source_texts[rule["source_doc_id"]]) is None]
    checks.append(_check("quote_verification", not unverified, f"unverified: {', '.join(unverified) or 'none'}"))
    if lookups_path.exists():
        lookup_payload = json.loads(lookups_path.read_text())
        lookups = lookup_payload["lookups"]
        checks.append(_check("address_coverage", len(lookups) == 500, f"{len(lookups)} lookup addresses"))
        by_id = {rule["team_rule_id"]: rule for rule in rules}
        entries = [entry for address_entries in lookups.values() for entry in address_entries]
        corpus_applies = sum(entry["result"] == "applies" and by_id.get(entry["team_rule_id"], {}).get("corpus_text") for entry in entries)
        all_applies = sum(entry["result"] == "applies" for entry in entries)
        checks.append(_check("citation_share", True, f"{corpus_applies}/{all_applies or 0} applies backed by corpus text"))
        invalid_city = [entry["team_rule_id"] for address_id, address_entries in lookups.items() for entry in address_entries if by_id.get(entry["team_rule_id"], {}).get("level") == "city" and by_id[entry["team_rule_id"]]["jurisdiction"] not in next(item for item in json.loads((BUILD_ROOT / "addresses_resolved.json").read_text()) if item["address_id"] == address_id)["stack"]]
        bad_states = [entry["team_rule_id"] for address_entries in lookups.values() for entry in address_entries if entry["result"] == "applies" and by_id.get(entry["team_rule_id"], {}).get("status") in {"pending", "failed"}]
        ma_caps = [entry["team_rule_id"] for address_id, address_entries in lookups.items() for entry in address_entries if next(item for item in json.loads((BUILD_ROOT / "addresses_resolved.json").read_text()) if item["address_id"] == address_id)["state"] == "MA" and by_id.get(entry["team_rule_id"], {}).get("category") == "rent_increase_limits" and "40P" not in by_id[entry["team_rule_id"]].get("citation", "")]
        checks.extend([
            _check("city_boundaries", not invalid_city, f"invalid city rules: {invalid_city}"),
            _check("pending_failed_never_apply", not bad_states, f"invalid applies: {bad_states}"),
            _check("no_ma_rent_cap", not ma_caps, f"MA cap rules: {ma_caps}"),
            _check("no_empty_explanations", all(entry.get("explanation") for entry in entries), "all explanations populated"),
        ])
    else:
        checks.append(_check("address_coverage", False, "submission/lookups.json is missing"))
    if changes_path.exists():
        changes = json.loads(changes_path.read_text())
        for test_id, (affected_count, conflict_count) in EXPECTED_CHANGES.items():
            result = changes.get(test_id, {})
            actual = (len(result.get("affected_address_ids", [])), len(result.get("conflict_flag_address_ids", [])))
            checks.append(_check(f"{test_id}_counts", actual == (affected_count, conflict_count), f"actual={actual}; expected={(affected_count, conflict_count)}"))
    else:
        checks.append(_check("change_tests", False, "submission/changes.json is missing"))
    payload = {"checks": checks, "passed": all(check["passed"] for check in checks), "notes": "Not legal advice."}
    SUBMISSION.mkdir(parents=True, exist_ok=True)
    WEB_VALIDATION.parent.mkdir(parents=True, exist_ok=True)
    WEB_VALIDATION.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    lines = ["# Validation report", "", f"Overall: {'PASS' if payload['passed'] else 'INCOMPLETE / FAIL'}", ""]
    lines.extend(f"- [{'x' if check['passed'] else ' '}] {check['name']}: {check['detail']}" for check in checks)
    lines.extend(["", "Not legal advice."])
    (SUBMISSION / "validation_report.md").write_text("\n".join(lines) + "\n")
    return payload
