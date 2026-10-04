from datetime import date

from navigator.status import (
    effective_date_for_record,
    enactment_from_source,
    resolve_relative_effective_date,
)


def test_fair_effective_date():
    assert resolve_relative_effective_date("first day of the twelfth month next following the date of enactment", date(2026, 7, 20)) == date(2027, 7, 1)


def test_application_fee_effective_date():
    assert resolve_relative_effective_date("first day of the fourth month next following the date of enactment", date(2026, 1, 20)) == date(2026, 5, 1)


def test_chaptered_bill_is_enacted_with_source_approval_date():
    enacted, enacted_date = enactment_from_source("CHAPTER 43\napproved July 20, 2026")
    assert enacted is True
    assert enacted_date == date(2026, 7, 20)


def test_chaptered_history_date_is_used_when_approval_is_tabular():
    enacted, enacted_date = enactment_from_source("10/06/25 - Chaptered")
    assert enacted is True
    assert enacted_date == date(2025, 10, 6)


def test_explicit_effective_date_beats_california_default():
    record = {
        "jurisdiction": "CA",
        "level": "state",
        "effective_rule_text": "This section went into effect on October 14, 2024.",
    }
    assert effective_date_for_record(record, enacted_date=date(2025, 10, 6), enacted=True) == date(2024, 10, 14)


def test_california_enacted_law_defaults_to_next_january_first_when_text_has_no_date():
    record = {"jurisdiction": "CA", "level": "state", "effective_rule_text": None}
    assert effective_date_for_record(record, enacted_date=date(2025, 10, 6), enacted=True) == date(2026, 1, 1)
