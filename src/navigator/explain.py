from __future__ import annotations

from datetime import date

from .coverage import CoverageDecision


def explain(rule: dict, result: str, coverage: CoverageDecision | None, as_of: date) -> str:
    title = rule.get("title") or rule.get("citation") or rule["team_rule_id"]
    if result == "pending":
        message = f"Pending: {title} has not been enacted."
    elif result == "not_yet_effective":
        effective = rule.get("effective_date")
        message = f"Not yet effective: {title}" + (f" takes effect on {effective}." if effective else " has a future effective date.")
    elif result == "superseded":
        message = f"Superseded: {title} covers this address, but a more protective local rule governs."
    elif result == "unknown":
        reasons = [item.reason for item in (coverage.predicates if coverage else ()) if item.result == "unknown"]
        message = f"Unknown: {title} may cover this address, but " + ("; ".join(reasons) if reasons else "a required fact is missing") + "."
    else:
        reasons = [item.reason for item in (coverage.predicates if coverage else ()) if item.result == "true"]
        message = f"Applies: {title} covers this address" + (f" because {'; '.join(reasons)}." if reasons else ".")
    return f"{message} As of {as_of.isoformat()}. Not legal advice."
