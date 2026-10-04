from navigator.merge import _load_test_patterns, _test_rule_ids


def test_fair_act_mapping_does_not_match_fair_chance_rules():
    patterns = _load_test_patterns()
    assert "NJ-ALG-01" not in _test_rule_ids(
        {"citation": "P.L.2021, c.110", "title": "New Jersey Fair Chance in Housing Act"},
        patterns,
    )
    assert _test_rule_ids(
        {"citation": "P.L.2026, c.43", "title": "Forbidding the Algorithmic Inflation of Rent (FAIR) Act"},
        patterns,
    ) == ["NJ-ALG-01"]
