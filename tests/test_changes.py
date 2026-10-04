from __future__ import annotations

import json

from navigator import changes

from test_golden import address, rule


def test_boundary_test_does_not_claim_t3_preemption_conflicts(tmp_path, monkeypatch):
    build = tmp_path / "build"
    submission = tmp_path / "submission"
    build.mkdir()
    fair = rule(
        "fair",
        "NJ",
        "algorithmic_rent_setting",
        citation="P.L.2026, c.43",
        effective_date="2027-07-01",
        test_rule_ids=["NJ-ALG-01"],
    )
    hoboken = rule(
        "hoboken-ban",
        "Hoboken, NJ",
        "algorithmic_rent_setting",
        test_rule_ids=["HOB-ALG-01"],
    )
    (build / "rules_internal.json").write_text(json.dumps({"rules": [fair, hoboken]}))
    (build / "addresses_resolved.json").write_text(
        json.dumps([address("H", ["NJ", "Hoboken, NJ"])])
    )
    tests = [
        {"test_id": "T2", "type": "boundary", "rule_ids": ["HOB-ALG-01"], "as_of": "2026-10-01"},
        {
            "test_id": "T3",
            "type": "as_of",
            "rule_ids": ["NJ-ALG-01"],
            "as_of_before": "2026-10-01",
            "as_of_after": "2027-07-02",
            "conflict_with": ["HOB-ALG-01"],
        },
    ]
    tests_path = tmp_path / "change_tests.json"
    tests_path.write_text(json.dumps(tests))
    monkeypatch.setattr(changes, "BUILD_ROOT", build)
    monkeypatch.setattr(changes, "SUBMISSION", submission)
    monkeypatch.setattr(changes, "CHANGE_TESTS", tests_path)

    result = changes.run()

    assert result["T2"]["conflict_flag_address_ids"] == []
    assert result["T3"]["conflict_flag_address_ids"] == ["H"]
