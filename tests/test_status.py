from datetime import date

from navigator.status import resolve_relative_effective_date


def test_fair_effective_date():
    assert resolve_relative_effective_date("first day of the twelfth month next following the date of enactment", date(2026, 7, 20)) == date(2027, 7, 1)


def test_application_fee_effective_date():
    assert resolve_relative_effective_date("first day of the fourth month next following the date of enactment", date(2026, 1, 20)) == date(2026, 5, 1)
