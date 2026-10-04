from __future__ import annotations

import re
from datetime import date

from dateutil import parser as date_parser


APPROVAL_DATE_RE = re.compile(
    r"\bapproved(?:\s+by\s+the\s+governor)?\s+"
    r"(?P<month>January|February|March|April|May|June|July|August|September|October|November|December)\s+"
    r"(?P<day>\d{1,2}),\s*(?P<year>\d{4})\b",
    re.IGNORECASE,
)
CHAPTERED_HISTORY_DATE_RE = re.compile(
    r"\b(?P<month>\d{1,2})/(?P<day>\d{1,2})/(?P<year>\d{2,4})\s*-\s*chaptered\b",
    re.IGNORECASE,
)
ENACTED_RE = re.compile(
    r"\b(?:chapter\s+\d+|chaptered|approved\s+by\s+governor|"
    r"approved\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},\s*\d{4}|"
    r"p\.?\s*l\.?\s*\d{4},?\s*c\.?\s*\d+)\b",
    re.IGNORECASE,
)
EXPLICIT_DATE_RE = re.compile(
    r"\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},\s*\d{4}\b",
    re.IGNORECASE,
)


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


def enactment_from_source(source_text: str) -> tuple[bool, date | None]:
    """Determine enactment only from the supplied source text, never LLM output."""
    approved = APPROVAL_DATE_RE.search(source_text)
    approved_date = None
    if approved:
        approved_date = date_parser.parse(approved.group(0).removeprefix("approved").strip(), fuzzy=True).date()
    chaptered_history = CHAPTERED_HISTORY_DATE_RE.search(source_text)
    if approved_date is None and chaptered_history:
        approved_date = date_parser.parse(chaptered_history.group(0).split("-")[0].strip(), dayfirst=False).date()
    return bool(ENACTED_RE.search(source_text)), approved_date


def explicit_effective_date(text: str | None) -> date | None:
    if not text:
        return None
    match = EXPLICIT_DATE_RE.search(text)
    return date_parser.parse(match.group(0)).date() if match else None


def effective_date_for_record(record: dict, *, enacted_date: date | None, enacted: bool) -> date | None:
    """Apply statutory date rules in their required precedence order."""
    rule_text = record.get("effective_rule_text") or record.get("effective_date_text")
    relative = resolve_relative_effective_date(rule_text, enacted_date)
    if relative:
        return relative
    explicit = explicit_effective_date(rule_text)
    if explicit:
        return explicit
    if enacted and enacted_date and record.get("jurisdiction") == "CA" and record.get("level") == "state":
        # Cal. Const. art. IV §8(c): enacted state statutes without a stated
        # operative date take effect on January 1 of the year after approval.
        return date(enacted_date.year + 1, 1, 1)
    return None


def base_status(*, doc_kind: str, citation: str, title: str = "", enacted: bool = False) -> str:
    haystack = f"{citation} {title}".lower()
    if enacted:
        return "in_force"
    if doc_kind == "motion": return "failed"
    if doc_kind == "ballot_measure" and ("25-21" in haystack or "struck" in haystack): return "failed"
    if doc_kind == "bill":
        if "193rd" in haystack or "h.3744" in haystack: return "failed"
        return "pending"
    return "in_force"


def status_at(*, base: str, effective_date: date | None, as_of: date) -> str:
    if base in {"pending", "failed"}: return base
    return "not_yet_effective" if effective_date and effective_date > as_of else "in_force"
