from navigator.merge import _load_test_patterns, _merge_same_law_records, _test_rule_ids


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


def test_predicateless_rso_companion_merges_into_covered_rso_record():
    covered = {
        "source_doc_id": "D041",
        "source_tier": "official",
        "citation": "L.A. Mun. Code ch. XV (RSO)",
        "title": "Los Angeles Rent Stabilization Ordinance (RSO)",
        "coverage_conditions": {"predicates": [{"type": "min_units", "parameters": {"n": 2}}]},
        "requirement": "Covered requirement",
        "key_value": None,
        "exemptions": [],
    }
    companion = {
        "source_doc_id": "D042",
        "source_tier": "official",
        "citation": "Los Angeles Rent Stabilization Ordinance (RSO)",
        "title": "Los Angeles RSO annual allowable rent increase",
        "coverage_conditions": {"predicates": []},
        "requirement": "Companion requirement",
        "key_value": "Companion key value",
        "exemptions": [],
    }
    result = _merge_same_law_records([covered, companion])
    assert len(result) == 1
    assert result[0]["coverage_conditions"] == covered["coverage_conditions"]
    assert result[0]["also_in_docs"] == ["D042"]
    assert result[0]["key_value"] == "Companion key value"


def test_tenant_level_only_chapter_companion_merges_into_covered_chapter():
    covered = {
        "source_doc_id": "D032",
        "source_tier": "link_only_research",
        "citation": "Hoboken Code ch. 155",
        "title": "Hoboken rent control coverage",
        "coverage_conditions": {"predicates": [{"type": "rolling_new_construction_exempt_years", "parameters": {"n": 30}}]},
        "requirement": "Coverage requirement",
        "key_value": "Coverage key value",
        "exemptions": [],
    }
    companion = {
        "source_doc_id": "D033",
        "source_tier": "link_only_research",
        "citation": "Hoboken Mun. Code ch. 155, §§ 155-4, 155-5",
        "title": "Hoboken annual increase cap",
        "coverage_conditions": {"predicates": [{"type": "tenant_level_conditions", "parameters": {}}]},
        "requirement": "Cap requirement",
        "key_value": None,
        "exemptions": [],
    }
    result = _merge_same_law_records([covered, companion])
    assert len(result) == 1
    assert result[0]["also_in_docs"] == ["D033"]
