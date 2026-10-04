from __future__ import annotations

from datetime import date

from navigator.lookup import evaluate_lookups


def rule(rule_id: str, jurisdiction: str, category: str, **overrides):
    data = {
        "team_rule_id": rule_id,
        "jurisdiction": jurisdiction,
        "level": "state" if len(jurisdiction) == 2 else "city",
        "category": category,
        "status": "in_force",
        "title": rule_id,
        "requirement": "Fixture requirement.",
        "citation": rule_id,
        "quoted_span": "Fixture quote long enough for the schema.",
        "coverage_conditions": {"text": "fixture coverage", "predicates": []},
        "yields_to_local": False,
    }
    data.update(overrides)
    return data


def address(address_id: str, stack: list[str], *, year=1962, units=20, flags=None):
    return {
        "address_id": address_id,
        "postal_city": stack[-1].split(",")[0] if len(stack) > 1 else "",
        "state": stack[0],
        "legal_city": stack[-1] if len(stack) > 1 else None,
        "stack": stack,
        "jurisdiction_confidence": "high",
        "facts": {
            "year_built": year,
            "units": units,
            "units_range": [units, units] if units is not None else None,
            "flags": flags or [],
        },
    }


AB1482 = rule(
    "ca-rent", "CA", "rent_increase_limits", citation="Cal. Civ. Code § 1947.12",
    yields_to_local=True,
    coverage_conditions={"text": "15-year rolling exemption", "predicates": [
        {"type": "rolling_new_construction_exempt_years", "parameters": {"n": 15}}
    ]},
)


def results(lookup, address_id):
    return {item["team_rule_id"]: item for item in lookup[address_id]}


def test_sf_golden_case():
    rules = [
        AB1482,
        rule("sf-rent", "San Francisco, CA", "rent_increase_limits"),
        rule("sf-jc", "San Francisco, CA", "just_cause_eviction"),
        rule("ca-deposit", "CA", "security_deposits", coverage_conditions={"text": "owner exception", "predicates": [{"type": "owner_type", "parameters": {"max_units_if_small_landlord": 4}}]}),
        rule("ca-fee", "CA", "application_screening_fees"),
        rule("sf-screen", "San Francisco, CA", "screening_restrictions", citation="S.F. Admin. Code § 37.10C"),
        rule("ca-alg", "CA", "algorithmic_rent_setting"),
    ]
    got = results(evaluate_lookups([address("SF", ["CA", "San Francisco, CA"])], rules, date(2026, 10, 1)), "SF")
    assert got["sf-rent"]["result"] == "applies"
    assert got["ca-rent"]["result"] == "superseded"
    assert all(got[key]["result"] == "applies" for key in ("sf-jc", "ca-deposit", "ca-fee", "sf-screen", "ca-alg"))


def test_la_known_and_cutoff_year():
    local = rule("la-rso", "Los Angeles, CA", "rent_increase_limits", coverage_conditions={"text": "RSO cutoff", "predicates": [
        {"type": "built_on_or_before", "parameters": {"date": "1978-10-01", "basis": "certificate_of_occupancy"}},
        {"type": "min_units", "parameters": {"n": 2}},
    ]})
    lookups = evaluate_lookups([
        address("A0001", ["CA", "Los Angeles, CA"], year=1927, units=32),
        address("A0107", ["CA", "Los Angeles, CA"], year=1978, units=10),
    ], [AB1482, local], date(2026, 10, 1))
    assert results(lookups, "A0001")["la-rso"]["result"] == "applies"
    assert results(lookups, "A0001")["ca-rent"]["result"] == "superseded"
    assert results(lookups, "A0107")["la-rso"]["result"] == "unknown"
    assert results(lookups, "A0107")["ca-rent"]["result"] == "unknown"


def test_rolling_window_and_missing_facts():
    rows = [address("old", ["CA"], year=2010), address("edge", ["CA"], year=2011), address("new", ["CA"], year=2012), address("missing", ["CA"], year=None)]
    got = evaluate_lookups(rows, [AB1482], date(2026, 10, 1))
    assert results(got, "old")["ca-rent"]["result"] == "applies"
    assert results(got, "edge")["ca-rent"]["result"] == "unknown"
    assert "ca-rent" not in results(got, "new")
    assert results(got, "missing")["ca-rent"]["result"] == "unknown"


def test_berkeley_rows_and_date_conflict():
    rent = rule("berk-rent", "Berkeley, CA", "rent_increase_limits", coverage_conditions={"text": "needs build year", "predicates": [{"type": "built_on_or_before", "parameters": {"date": "1980-06-30", "basis": "certificate_of_occupancy"}}]})
    jc = rule("berk-jc", "Berkeley, CA", "just_cause_eviction")
    screening = rule("berk-1363", "Berkeley, CA", "screening_restrictions", citation="Berkeley Mun. Code ch. 13.63")
    got = results(evaluate_lookups([address("B", ["CA", "Berkeley, CA"], year=None, units=8)], [rent, jc, screening], date(2026, 10, 1)), "B")
    assert got["berk-rent"]["result"] == "unknown"
    assert got["berk-jc"]["result"] == "applies"
    assert got["berk-1363"]["result"] == "applies"
    assert got["berk-1363"]["conflict_flag"] is True


def test_san_diego_has_no_local_rent_cap_and_state_is_unknown():
    ban = rule("sd-alg", "San Diego, CA", "algorithmic_rent_setting")
    got = results(evaluate_lookups([address("SD", ["CA", "San Diego, CA"], year=None)], [AB1482, ban], date(2026, 10, 1)), "SD")
    assert got["ca-rent"]["result"] == "unknown"
    assert got["sd-alg"]["result"] == "applies"
    assert set(got) == {"ca-rent", "sd-alg"}


def test_nj_city_bans_fair_conflicts_and_rent_control():
    fair = rule("fair", "NJ", "algorithmic_rent_setting", citation="P.L.2026, c.43", effective_date="2027-07-01")
    jc_ban = rule("jc-ban", "Jersey City, NJ", "algorithmic_rent_setting")
    hob_ban = rule("hob-ban", "Hoboken, NJ", "algorithmic_rent_setting")
    city_rent = rule("jc-rent", "Jersey City, NJ", "rent_increase_limits", coverage_conditions={"text": "5+ and 30-year exemption", "predicates": [
        {"type": "min_units", "parameters": {"n": 5}},
        {"type": "rolling_new_construction_exempt_years", "parameters": {"n": 30, "filing_required": True}},
    ]})
    rows = [address("JC", ["NJ", "Jersey City, NJ"], year=1900), address("JC?", ["NJ", "Jersey City, NJ"], year=None), address("H", ["NJ", "Hoboken, NJ"], year=2005), address("N", ["NJ", "Newark, NJ"], year=1910)]
    got = evaluate_lookups(rows, [fair, jc_ban, hob_ban, city_rent], date(2026, 10, 1))
    assert results(got, "JC")["jc-rent"]["result"] == "applies"
    assert results(got, "JC?")["jc-rent"]["result"] == "unknown"
    for row_id, ban_id in (("JC", "jc-ban"), ("H", "hob-ban")):
        row = results(got, row_id)
        assert row[ban_id]["result"] == "applies" and row[ban_id]["conflict_flag"]
        assert row["fair"]["result"] == "not_yet_effective" and row["fair"]["conflict_flag"]
    assert "jc-ban" not in results(got, "N") and "hob-ban" not in results(got, "N")
    assert results(got, "N")["fair"]["result"] == "not_yet_effective"


def test_ma_has_prohibition_and_pending_bills_but_no_rent_cap():
    rules = [
        rule("ma-40p", "MA", "rent_increase_limits", citation="M.G.L. c. 40P, § 4", key_value="no rent cap — local rent control prohibited"),
        rule("s2983", "MA", "algorithmic_rent_setting", status="pending"),
        rule("h5222", "MA", "algorithmic_rent_setting", status="pending"),
        rule("failed-cap", "MA", "rent_increase_limits", status="failed"),
    ]
    got = results(evaluate_lookups([address("MA", ["MA", "Boston, MA"])], rules, date(2026, 10, 1)), "MA")
    assert got["ma-40p"]["result"] == "applies"
    assert got["s2983"]["result"] == got["h5222"]["result"] == "pending"
    assert "failed-cap" not in got
    assert set(got) == {"ma-40p", "s2983", "h5222"}


def test_pending_and_not_yet_effective_ignore_unknown_coverage():
    predicate = {"text": "missing owner", "predicates": [{"type": "owner_type", "parameters": {}}]}
    rules = [rule("pending", "MA", "algorithmic_rent_setting", status="pending", coverage_conditions=predicate), rule("future", "MA", "algorithmic_rent_setting", effective_date="2027-01-01", coverage_conditions=predicate)]
    got = results(evaluate_lookups([address("A", ["MA"])], rules, date(2026, 10, 1)), "A")
    assert got["pending"]["result"] == "pending"
    assert got["future"]["result"] == "not_yet_effective"
    assert all(item["explanation"].endswith("As of 2026-10-01. Not legal advice.") for item in got.values())


def test_low_confidence_city_and_flagged_special_status_are_unknown():
    city = rule("city", "Los Angeles, CA", "just_cause_eviction")
    special = rule("special", "CA", "screening_restrictions", coverage_conditions={"text": "subsidized exemption", "predicates": [
        {"type": "special_status_exemptions", "parameters": {"text": ["subsidized"]}}
    ]})
    row = address("low", ["CA", "Los Angeles, CA"], flags=["subsidized"])
    row["jurisdiction_confidence"] = "low"
    got = results(evaluate_lookups([row], [city, special], date(2026, 10, 1)), "low")
    assert got["city"]["result"] == "unknown"
    assert got["special"]["result"] == "unknown"


def test_owner_data_is_unknown_unless_units_rule_out_exception():
    owner = rule("owner", "CA", "security_deposits", coverage_conditions={"text": "small landlord", "predicates": [
        {"type": "owner_type", "parameters": {"max_units_if_small_landlord": 4}}
    ]})
    got = evaluate_lookups([address("large", ["CA"], units=20), address("small", ["CA"], units=2)], [owner], date(2026, 10, 1))
    assert results(got, "large")["owner"]["result"] == "applies"
    assert results(got, "small")["owner"]["result"] == "unknown"


def test_open_ended_unit_range_can_satisfy_minimum():
    minimum = rule("minimum", "NJ", "rent_increase_limits", coverage_conditions={"text": "five plus", "predicates": [
        {"type": "min_units", "parameters": {"n": 5}}
    ]})
    row = address("range", ["NJ"], units=None)
    row["facts"]["units_range"] = [5, None]
    assert results(evaluate_lookups([row], [minimum], date(2026, 10, 1)), "range")["minimum"]["result"] == "applies"


def test_cp3_invariants_keep_santa_ana_out_and_nonforceable_rules_nonapplicable():
    rules = [
        rule("santa-ana-rent", "Santa Ana, CA", "rent_increase_limits"),
        rule("failed", "MA", "rent_increase_limits", status="failed"),
        rule("pending", "MA", "algorithmic_rent_setting", status="pending"),
        rule(
            "ma-40p",
            "MA",
            "rent_increase_limits",
            citation="M.G.L. c. 40P, § 4",
            key_value="no rent cap — local rent control prohibited",
        ),
    ]
    got = evaluate_lookups(
        [address("LA", ["CA", "Los Angeles, CA"]), address("MA", ["MA", "Boston, MA"])],
        rules,
        date(2026, 10, 1),
    )

    assert all("santa-ana-rent" not in results(got, address_id) for address_id in got)
    assert "failed" not in results(got, "MA")
    assert results(got, "MA")["pending"]["result"] == "pending"
    assert set(results(got, "MA")) == {"ma-40p", "pending"}
