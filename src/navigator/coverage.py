from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import re
from typing import Any, Literal

Truth = Literal["true", "false", "unknown"]


@dataclass(frozen=True)
class PredicateDecision:
    predicate: str
    result: Truth
    reason: str
    facts_used: dict[str, Any]


@dataclass(frozen=True)
class CoverageDecision:
    result: Truth
    predicates: tuple[PredicateDecision, ...]


def _units(facts: dict[str, Any]) -> tuple[int | None, int | None]:
    exact = facts.get("units")
    if isinstance(exact, int) and exact > 0:
        return exact, exact
    value = facts.get("units_range")
    if isinstance(value, (list, tuple)) and len(value) == 2:
        low, high = value
        return (int(low) if low is not None else None, int(high) if high is not None else None)
    return None, None


def _year(facts: dict[str, Any]) -> int | None:
    value = facts.get("year_built")
    return int(value) if isinstance(value, (int, float)) and value > 0 else None


def _decision(kind: str, result: Truth, reason: str, **facts: Any) -> PredicateDecision:
    return PredicateDecision(kind, result, reason, facts)


def _predicate_date(value: Any) -> date:
    """Accept the internal date precision allowed for rule fields (YYYY[-MM][-DD])."""
    text = str(value)
    if re.fullmatch(r"\d{4}", text):
        return date(int(text), 1, 1)
    if re.fullmatch(r"\d{4}-\d{2}", text):
        return date.fromisoformat(text + "-01")
    return date.fromisoformat(text)


def evaluate_predicate(predicate: dict[str, Any], facts: dict[str, Any], as_of: date) -> PredicateDecision:
    kind = predicate.get("type", "")
    params = predicate.get("parameters") or {}
    year = _year(facts)
    low, high = _units(facts)

    if kind in {"built_on_or_before", "built_after"}:
        cutoff = _predicate_date(params["date"])
        if year is None:
            return _decision(kind, "unknown", "the construction year is missing", year_built=None, cutoff=params["date"])
        if year == cutoff.year and params.get("basis") == "certificate_of_occupancy":
            return _decision(kind, "unknown", "the year matches the cutoff, but the certificate-of-occupancy date is unknown", year_built=year, cutoff=params["date"])
        if kind == "built_on_or_before":
            result = "true" if year <= cutoff.year else "false"
        else:
            result = "true" if year > cutoff.year else "false"
        return _decision(kind, result, f"the recorded construction year is {year}", year_built=year, cutoff=params["date"])

    if kind == "rolling_new_construction_exempt_years":
        years = int(params["n"])
        boundary = as_of.year - years
        if year is None:
            return _decision(kind, "unknown", "the construction year needed for the rolling exemption is missing", year_built=None, boundary_year=boundary)
        if year == boundary:
            return _decision(kind, "unknown", "the building is in the rolling-window edge year", year_built=year, boundary_year=boundary)
        if year > boundary:
            if params.get("filing_required"):
                return _decision(kind, "unknown", "the building is within the exemption window, but the required owner filing is unknown", year_built=year, boundary_year=boundary)
            return _decision(kind, "false", "the building is within the new-construction exemption window", year_built=year, boundary_year=boundary)
        return _decision(kind, "true", "the building predates the rolling exemption window", year_built=year, boundary_year=boundary)

    if kind == "min_units":
        n = int(params["n"])
        if low is not None and low >= n:
            return _decision(kind, "true", f"the building has at least {n} units", units_range=[low, high], threshold=n)
        if high is not None and high < n:
            return _decision(kind, "false", f"the building has fewer than {n} units", units_range=[low, high], threshold=n)
        if low is None and high is None:
            return _decision(kind, "unknown", "the unit count is missing", units_range=[low, high], threshold=n)
        return _decision(kind, "unknown", "the estimated unit range crosses the threshold", units_range=[low, high], threshold=n)

    if kind == "max_units":
        n = int(params["n"])
        if high is not None and high <= n:
            return _decision(kind, "true", f"the building has no more than {n} units", units_range=[low, high], threshold=n)
        if low is not None and low > n:
            return _decision(kind, "false", f"the building has more than {n} units", units_range=[low, high], threshold=n)
        if low is None and high is None:
            return _decision(kind, "unknown", "the unit count is missing", units_range=[low, high], threshold=n)
        return _decision(kind, "unknown", "the estimated unit range crosses the threshold", units_range=[low, high], threshold=n)

    if kind == "owner_occupied_exempt_max_units":
        n = int(params["n"])
        if low is not None and low > n:
            return _decision(kind, "true", "the unit count rules out the small owner-occupied exemption", units_range=[low, high], exemption_max_units=n)
        return _decision(kind, "unknown", "owner occupancy is not in the address data", units_range=[low, high], exemption_max_units=n)

    if kind == "owner_type":
        n = params.get("max_units_if_small_landlord")
        # Every owner-type exception represented in this corpus is limited to
        # an individual unit or a one-to-four-unit property.  Five verified
        # units therefore make the exception impossible even when extraction
        # did not repeat the numerical cap in the predicate parameters.
        if low is not None and low >= 5:
            return _decision(
                kind,
                "true",
                "5+ unit building, so the owner-type exemption can't apply",
                units_range=[low, high],
            )
        if n is not None and low is not None and low > int(n):
            return _decision(kind, "true", "the unit count rules out the small-landlord exception", units_range=[low, high], exception_max_units=int(n))
        return _decision(kind, "unknown", "owner type is not in the address data", units_range=[low, high])

    if kind == "special_status_exemptions":
        flags = {str(flag).lower() for flag in (facts.get("flags") or [])}
        text = " ".join(str(item).lower() for item in params.get("text", [])) if isinstance(params.get("text"), list) else str(params.get("text", "")).lower()
        if "covers only" in text:
            return _decision(
                kind,
                "unknown",
                "DND funding or IDP income-restriction status is not in the address data",
                flags=sorted(flags),
            )
        triggered = sorted(flag for flag in flags if flag and flag in text)
        if triggered:
            return _decision(kind, "unknown", f"a possible special-status exemption is flagged: {', '.join(triggered)}", flags=sorted(flags))
        return _decision(kind, "true", "no special-status exemption is flagged in the supplied facts", flags=sorted(flags))

    if kind == "tenant_level_conditions":
        return _decision(kind, "true", "tenant-level conditions do not block an address-level result")

    return _decision(kind, "unknown", f"unsupported predicate: {kind}")


def evaluate_coverage(rule: dict[str, Any], facts: dict[str, Any], as_of: date) -> CoverageDecision:
    conditions = rule.get("coverage_conditions") or {}
    decisions = tuple(evaluate_predicate(item, facts, as_of) for item in conditions.get("predicates", []))
    if any(item.result == "false" for item in decisions):
        result: Truth = "false"
    elif any(item.result == "unknown" for item in decisions):
        result = "unknown"
    else:
        result = "true"
    return CoverageDecision(result, decisions)
