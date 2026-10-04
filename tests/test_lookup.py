from __future__ import annotations

import json
from datetime import date

from navigator.lookup import evaluate_lookups

from test_golden import address, rule


def test_city_rule_does_not_escape_city_and_trace_is_written(tmp_path):
    addresses = [address("SF", ["CA", "San Francisco, CA"]), address("LA", ["CA", "Los Angeles, CA"])]
    rules = [rule("sf-only", "San Francisco, CA", "just_cause_eviction")]
    got = evaluate_lookups(addresses, rules, date(2026, 10, 1), tmp_path)
    assert [item["team_rule_id"] for item in got["SF"]] == ["sf-only"]
    assert got["LA"] == []
    trace = json.loads((tmp_path / "LA.json").read_text())
    assert trace["evaluations"][0]["reason"] == "jurisdiction_not_in_stack"
    assert trace["notes"] == "Not legal advice."


def test_results_are_sorted_and_explanations_are_never_empty():
    rules = [rule("z", "CA", "security_deposits"), rule("a", "CA", "just_cause_eviction")]
    got = evaluate_lookups([address("A", ["CA"])], rules, date(2026, 10, 1))["A"]
    assert [item["team_rule_id"] for item in got] == ["a", "z"]
    assert all(item["explanation"] for item in got)
    assert all(set(item) == {"team_rule_id", "result", "explanation", "conflict_flag"} for item in got)


def test_year_only_construction_cutoff_is_evaluated_without_a_date_parse_failure():
    cutoff = rule(
        "cutoff",
        "CA",
        "rent_increase_limits",
        coverage_conditions={
            "text": "built before 1980",
            "predicates": [{"type": "built_on_or_before", "parameters": {"date": "1980", "basis": "certificate_of_occupancy"}}],
        },
    )
    got = evaluate_lookups([address("old", ["CA"], year=1979), address("edge", ["CA"], year=1980)], [cutoff], date(2026, 10, 1))
    assert got["old"][0]["result"] == "applies"
    assert got["edge"][0]["result"] == "unknown"
