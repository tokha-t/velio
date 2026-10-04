from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

from .lookup import evaluate_lookups
from .paths import BUILD_ROOT, ROOT

CHANGE_TESTS = ROOT / "starter_pack" / "dev" / "change_tests.json"
SUBMISSION = ROOT / "submission"


def _load_rules() -> list[dict[str, Any]]:
    return json.loads((BUILD_ROOT / "rules_internal.json").read_text())["rules"]


def _load_addresses() -> list[dict[str, Any]]:
    return json.loads((BUILD_ROOT / "addresses_resolved.json").read_text())


def _entries_by_rule(lookups: dict[str, list[dict[str, Any]]], address_id: str) -> dict[str, dict[str, Any]]:
    return {entry["team_rule_id"]: entry for entry in lookups[address_id]}


def _mapping(rules: list[dict[str, Any]]) -> dict[str, list[str]]:
    mapped: dict[str, list[str]] = {}
    for rule in rules:
        for test_id in rule.get("test_rule_ids", []):
            mapped.setdefault(test_id, []).append(rule["team_rule_id"])
    return {test_id: sorted(rule_ids) for test_id, rule_ids in mapped.items()}


def _notes(test: dict[str, Any], mapping: dict[str, list[str]]) -> str:
    pairs = "; ".join(
        f"{test_id} -> {', '.join(mapping.get(test_id, [])) or 'missing'}"
        for test_id in test["rule_ids"]
    )
    dates = ", ".join(value for key, value in sorted(test.items()) if key.startswith("as_of"))
    return f"Key-to-team mapping: {pairs}. Dates: {dates or test.get('as_of', '2026-10-01')}. Deterministic lookup comparison. Not legal advice."


def _affected_by_date_change(
    addresses: list[dict[str, Any]], before: dict[str, list[dict[str, Any]]], after: dict[str, list[dict[str, Any]]], rule_ids: list[str]
) -> list[str]:
    affected = []
    for address in addresses:
        address_id = address["address_id"]
        old = _entries_by_rule(before, address_id)
        new = _entries_by_rule(after, address_id)
        if any((old.get(rule_id) or {}).get("result") != (new.get(rule_id) or {}).get("result") for rule_id in rule_ids):
            affected.append(address_id)
    return sorted(affected)


def _reached_addresses(addresses: list[dict[str, Any]], lookups: dict[str, list[dict[str, Any]]], rule_ids: list[str]) -> list[str]:
    return sorted(
        address["address_id"]
        for address in addresses
        if any(rule_id in _entries_by_rule(lookups, address["address_id"]) for rule_id in rule_ids)
    )


def run() -> dict[str, Any]:
    rules = _load_rules()
    addresses = _load_addresses()
    tests = json.loads(CHANGE_TESTS.read_text())
    mapping = _mapping(rules)
    dates = {"2025-12-31", "2026-01-02", "2026-10-01", "2027-07-02"}
    lookups = {value: evaluate_lookups(addresses, rules, date.fromisoformat(value)) for value in dates}
    changes: dict[str, Any] = {}
    detail: dict[str, Any] = {}
    for test in tests:
        test_id = test["test_id"]
        key_ids = test["rule_ids"]
        team_ids = [rule_id for key_id in key_ids for rule_id in mapping.get(key_id, [])]
        current = lookups[test.get("as_of", "2026-10-01")]
        if test["type"] == "as_of":
            affected = _affected_by_date_change(addresses, lookups[test["as_of_before"]], lookups[test["as_of_after"]], team_ids)
        elif test["type"] == "pending":
            affected = _reached_addresses(addresses, current, team_ids)
        elif test["type"] == "negative":
            affected = []
        else:
            affected = _reached_addresses(addresses, current, team_ids)
        # Only tests which explicitly name a conflicting rule pair report a
        # conflict set.  T2 is a jurisdiction-boundary check; T3 owns the
        # FAIR/local-ban preemption question and evaluates it after FAIR's
        # effective date.
        conflict_team_ids = [
            rule_id
            for key_id in test.get("conflict_with", [])
            for rule_id in mapping.get(key_id, [])
        ]
        conflict_lookups = lookups[test.get("as_of_after", test.get("as_of", "2026-10-01"))]
        conflicts = sorted(
            address["address_id"]
            for address in addresses
            if any(
                entry.get("conflict_flag")
                for rule_id, entry in _entries_by_rule(conflict_lookups, address["address_id"]).items()
                if rule_id in conflict_team_ids
            )
        )
        changes[test_id] = {
            "affected_address_ids": affected,
            "conflict_flag_address_ids": conflicts,
            "notes": _notes(test, mapping),
        }
        detail[test_id] = {
            "rules": {
                key_id: {
                    "team_rule_ids": mapping.get(key_id, []),
                    "affected_address_ids": _reached_addresses(addresses, current, mapping.get(key_id, [])),
                }
                for key_id in key_ids
            }
        }
    SUBMISSION.mkdir(parents=True, exist_ok=True)
    (SUBMISSION / "changes.json").write_text(json.dumps(changes, indent=2, sort_keys=True) + "\n")
    (SUBMISSION / "changes_detail.json").write_text(json.dumps(detail, indent=2, sort_keys=True) + "\n")
    return changes
