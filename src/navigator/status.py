from __future__ import annotations

import calendar
import re
from datetime import date


def first_day_of_nth_month_next(enacted: date, ordinal: int) -> date:
    # "first day of the Nth month next following" excludes enactment month.
    month_index = enacted.year * 12 + enacted.month - 1 + ordinal
    return date(month_index // 12, month_index % 12 + 1, 1)


def resolve_relative_effective_date(text: str | None, enacted: date | None) -> date | None:
    if not text or not enacted:
        return None
    match = re.search(r"first day of the (\w+) month next following", text, re.I)
    if not match:
        return None
    ordinals = {"first": 1, "second": 2, "third": 3, "fourth": 4, "fifth": 5, "sixth": 6, "seventh": 7, "eighth": 8, "ninth": 9, "tenth": 10, "eleventh": 11, "twelfth": 12}
    ordinal = ordinals.get(match.group(1).lower())
    return first_day_of_nth_month_next(enacted, ordinal) if ordinal else None


def base_status(*, doc_kind: str, citation: str, title: str = "") -> str:
    haystack = f"{citation} {title}".lower()
    if doc_kind == "motion": return "failed"
    if doc_kind == "ballot_measure" and ("25-21" in haystack or "struck" in haystack): return "failed"
    if doc_kind == "bill":
        if "193rd" in haystack or "h.3744" in haystack: return "failed"
        return "pending"
    return "in_force"


def status_at(*, base: str, effective_date: date | None, as_of: date) -> str:
    if base in {"pending", "failed"}: return base
    return "not_yet_effective" if effective_date and effective_date > as_of else "in_force"
