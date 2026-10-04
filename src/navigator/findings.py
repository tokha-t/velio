"""Deterministic P5 findings derived from the extracted rule and lookup outputs."""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import date
from pathlib import Path
from typing import Any

from .corpus import load_documents, load_research_documents
from .lookup import _rule_status
from .paths import BUILD_ROOT, ROOT

SUBMISSION = ROOT / "submission"
CATEGORIES = (
    "rent_increase_limits",
    "just_cause_eviction",
    "security_deposits",
    "application_screening_fees",
    "screening_restrictions",
    "algorithmic_rent_setting",
)
AS_OF = date(2026, 10, 1)


def _rules() -> list[dict[str, Any]]:
    return json.loads((BUILD_ROOT / "rules_internal.json").read_text())["rules"]


def _addresses() -> list[dict[str, Any]]:
    return json.loads((BUILD_ROOT / "addresses_resolved.json").read_text())


def _scopes(addresses: list[dict[str, Any]]) -> list[str]:
    values = {address["state"] for address in addresses}
    values.update(address["legal_city"] for address in addresses if address.get("legal_city"))
    return sorted(values)


def _docs_by_jurisdiction() -> dict[str, list[str]]:
    values: dict[str, list[str]] = defaultdict(list)
    for document in load_documents() + load_research_documents():
        values[document.jurisdictions].append(document.doc_id)
    return {jurisdiction: sorted(set(doc_ids)) for jurisdiction, doc_ids in values.items()}


def _reason(records: list[dict[str, Any]], state_records: list[dict[str, Any]]) -> str:
    if records:
        pending = sorted({record["citation"] for record in records if _rule_status(record, AS_OF) == "pending"})
        failed = sorted({record["citation"] for record in records if _rule_status(record, AS_OF) == "failed"})
        fragments = ["No in-force rule was extracted at this jurisdiction level."]
        if pending:
            fragments.append(f"Pending: {'; '.join(pending)}.")
        if failed:
            fragments.append(f"Failed: {'; '.join(failed)}.")
        return " ".join(fragments)
    prohibitions = [
        record for record in state_records
        if "no rent cap" in (record.get("key_value") or "").lower()
    ]
    if prohibitions:
        return (
            "No in-force city rent-cap rule was extracted; an in-force state rule in the "
            f"address stack says {'; '.join(sorted(record['citation'] for record in prohibitions))}."
        )
    return "No in-force rule was extracted at this jurisdiction level from the checked documents."


def write_no_rule_findings() -> dict[str, Any]:
    rules = _rules()
    docs = _docs_by_jurisdiction()
    findings: list[dict[str, Any]] = []
    for jurisdiction in _scopes(_addresses()):
        state = jurisdiction if len(jurisdiction) == 2 else jurisdiction.rsplit(", ", 1)[-1]
        for category in CATEGORIES:
            exact = [rule for rule in rules if rule["jurisdiction"] == jurisdiction and rule["category"] == category]
            if any(_rule_status(rule, AS_OF) == "in_force" for rule in exact):
                continue
            state_records = [rule for rule in rules if rule["jurisdiction"] == state and rule["category"] == category]
            findings.append({
                "jurisdiction": jurisdiction,
                "category": category,
                "reason": _reason(exact, state_records),
                "docs_checked": docs.get(jurisdiction, []),
            })
    payload = {"findings": findings, "notes": "Generated from extracted records at 2026-10-01. Not legal advice."}
    SUBMISSION.mkdir(parents=True, exist_ok=True)
    (SUBMISSION / "no_rule_findings.json").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return payload


def write_conflict_notes() -> dict[str, Any]:
    rules_by_id = {rule["team_rule_id"]: rule for rule in _rules()}
    lookups = json.loads((SUBMISSION / "lookups.json").read_text())["lookups"]
    groups: dict[str, dict[str, set[str]]] = {}
    for address_id, entries in lookups.items():
        for entry in entries:
            note = entry.get("conflict_note")
            if not note:
                continue
            group = groups.setdefault(note, {"addresses": set(), "rules": set()})
            group["addresses"].add(address_id)
            rule = rules_by_id[entry["team_rule_id"]]
            group["rules"].add(f"{rule['team_rule_id']} ({rule['citation']})")
    conflicts = [
        {
            "note": note,
            "team_rules": sorted(group["rules"]),
            "affected_address_ids": sorted(group["addresses"]),
        }
        for note, group in sorted(groups.items())
    ]
    payload = {"as_of": AS_OF.isoformat(), "conflicts": conflicts, "notes": "Potential conflicts require human review. Not legal advice."}
    (SUBMISSION / "conflict_notes.json").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return payload


def run() -> dict[str, Any]:
    return {"no_rule_findings": write_no_rule_findings(), "conflict_notes": write_conflict_notes()}
