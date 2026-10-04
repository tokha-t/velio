from __future__ import annotations

import json
import subprocess
from datetime import date
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .coverage import CoverageDecision, PredicateDecision, evaluate_coverage
from .explain import explain
from .paths import BUILD_ROOT, LOG_ROOT, ROOT

SUBMISSION_ROOT = ROOT / "submission"


def _rule_status(rule: dict[str, Any], as_of: date) -> str:
    status = rule.get("base_status") or rule.get("status", "in_force")
    if status in {"pending", "failed"}:
        return status
    value = rule.get("effective_date")
    if value:
        effective = date.fromisoformat(value[:10] if len(value) >= 10 else value + ("-01-01" if len(value) == 4 else "-01"))
        return "not_yet_effective" if effective > as_of else "in_force"
    return status


def _is_fair(rule: dict[str, Any]) -> bool:
    citation = rule.get("citation", "").replace(" ", "").lower()
    return rule.get("jurisdiction") == "NJ" and rule.get("category") == "algorithmic_rent_setting" and "p.l.2026,c.43" in citation


def _conflict_note(rule: dict[str, Any], address: dict[str, Any], rules: list[dict[str, Any]]) -> str | None:
    citation = rule.get("citation", "").lower()
    jurisdiction = rule.get("jurisdiction")
    city = address.get("legal_city")
    if rule.get("category") == "algorithmic_rent_setting" and city in {"Jersey City, NJ", "Hoboken, NJ"}:
        fair_present = any(_is_fair(item) for item in rules)
        is_local = jurisdiction == city
        if fair_present and (_is_fair(rule) or is_local):
            return "Possible conflict — human review: the FAIR Act bars municipalities from enacting conflicting ordinances but does not name or void the existing local ban."
    if jurisdiction == "Berkeley, CA" and "13.63" in citation:
        return "Source conflict — human review: the ordinance says March 1, 2026, while a secondary alert says January 2026."
    if jurisdiction == "Los Angeles, CA" and rule.get("category") == "rent_increase_limits":
        return "Source conflict — human review: official sources give February 2, 2026 for the new RSO formula; a landlord-association source gives January 24, 2026."
    if rule.get("jurisdiction") == "CA" and "1950.6" in citation:
        return "Source conflict — human review: the corpus provides a statutory formula but no single official 2026 screening-fee amount."
    return None


def _entry(rule: dict[str, Any], result: str, coverage: CoverageDecision | None, as_of: date, conflict_note: str | None) -> dict[str, Any]:
    item = {
        "team_rule_id": rule["team_rule_id"],
        "result": result,
        "explanation": explain(rule, result, coverage, as_of),
        "conflict_flag": conflict_note is not None,
    }
    if conflict_note:
        item["conflict_note"] = conflict_note
    return item


def _supersede(address: dict[str, Any], rules_by_id: dict[str, dict[str, Any]], entries: dict[str, dict[str, Any]], coverage: dict[str, CoverageDecision], as_of: date) -> None:
    local_results: dict[str, list[str]] = {}
    for rule_id, item in entries.items():
        rule = rules_by_id[rule_id]
        if rule.get("level") == "city":
            local_results.setdefault(rule.get("category", ""), []).append(item["result"])
    for rule_id, item in entries.items():
        rule = rules_by_id[rule_id]
        if rule.get("jurisdiction") != "CA" or rule.get("level") != "state" or item["result"] != "applies":
            continue
        citation = rule.get("citation", "")
        yields = (rule.get("category") == "rent_increase_limits" and "1947.12" in citation) or (rule.get("category") == "just_cause_eviction" and rule.get("yields_to_local"))
        if not yields:
            continue
        results = local_results.get(rule.get("category", ""), [])
        if "applies" in results:
            item["result"] = "superseded"
            item["explanation"] = explain(rule, "superseded", coverage.get(rule_id), as_of)
        elif "unknown" in results:
            item["result"] = "unknown"
            local_unknown = CoverageDecision("unknown", ())
            item["explanation"] = explain(rule, "unknown", local_unknown, as_of).replace("a required fact is missing", "the more protective local rule's coverage is unknown")


def evaluate_lookups(addresses: list[dict[str, Any]], rules: list[dict[str, Any]], as_of: date, trace_dir: Path | None = None) -> dict[str, list[dict[str, Any]]]:
    ordered_rules = sorted(rules, key=lambda item: item["team_rule_id"])
    rules_by_id = {item["team_rule_id"]: item for item in ordered_rules}
    output: dict[str, list[dict[str, Any]]] = {}
    if trace_dir:
        trace_dir.mkdir(parents=True, exist_ok=True)
    for address in sorted(addresses, key=lambda item: item["address_id"]):
        entries: dict[str, dict[str, Any]] = {}
        decisions: dict[str, CoverageDecision] = {}
        trace: list[dict[str, Any]] = []
        stack = address.get("stack") or [address.get("state")]
        for rule in ordered_rules:
            rule_id = rule["team_rule_id"]
            step: dict[str, Any] = {"team_rule_id": rule_id, "jurisdiction": rule.get("jurisdiction")}
            if rule.get("jurisdiction") not in stack:
                step.update({"included": False, "reason": "jurisdiction_not_in_stack"})
                trace.append(step)
                continue
            status = _rule_status(rule, as_of)
            step["status"] = status
            if status == "failed":
                step.update({"included": False, "reason": "failed"})
                trace.append(step)
                continue
            conflict = _conflict_note(rule, address, ordered_rules)
            if status in {"pending", "not_yet_effective"}:
                entries[rule_id] = _entry(rule, status, None, as_of, conflict)
                step.update({"included": True, "result": status, "predicates": []})
                trace.append(step)
                continue
            decision = evaluate_coverage(rule, address.get("facts") or {}, as_of)
            if rule.get("level") == "city" and address.get("jurisdiction_confidence") == "low":
                decision = CoverageDecision("unknown", decision.predicates + (
                    PredicateDecision("jurisdiction_confidence", "unknown", "the legal city is based only on a low-confidence dataset fallback", {"legal_city": address.get("legal_city")}),
                ))
            decisions[rule_id] = decision
            step["predicates"] = [item.__dict__ for item in decision.predicates]
            if decision.result == "false":
                step.update({"included": False, "reason": "coverage_false"})
            else:
                result = "applies" if decision.result == "true" else "unknown"
                entries[rule_id] = _entry(rule, result, decision, as_of, conflict)
                step.update({"included": True, "result": result})
            trace.append(step)
        _supersede(address, rules_by_id, entries, decisions, as_of)
        output[address["address_id"]] = [entries[key] for key in sorted(entries)]
        if trace_dir:
            payload = {"address_id": address["address_id"], "as_of": as_of.isoformat(), "facts": address.get("facts") or {}, "evaluations": trace, "results": output[address["address_id"]], "notes": "Not legal advice."}
            (trace_dir / f"{address['address_id']}.json").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return output


def _load_rules(path: Path | None = None) -> list[dict[str, Any]]:
    if path is None:
        errors_path = BUILD_ROOT / "extract_errors.json"
        if errors_path.exists() and json.loads(errors_path.read_text()).get("errors"):
            raise RuntimeError(
                "Production lookups are blocked: extraction has retry-exhausted chunks in "
                f"{errors_path}. Resume P1 from cache before generating submission outputs."
            )
    source = path or BUILD_ROOT / "rules_internal.json"
    if not source.exists():
        raise FileNotFoundError(f"P2 requires {source}; finish P1 extraction and merge before generating production lookups")
    payload = json.loads(source.read_text())
    return payload.get("rules", payload) if isinstance(payload, dict) else payload


def _log_run(as_of: str, address_count: int) -> None:
    LOG_ROOT.mkdir(parents=True, exist_ok=True)
    manifest_path = BUILD_ROOT / "corpus_manifest.json"
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else []
    git_sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, capture_output=True, check=False).stdout.strip() or None
    record = {
        "event": "lookup_run",
        "at": datetime.now(timezone.utc).isoformat(),
        "as_of": as_of,
        "address_count": address_count,
        "git_sha": git_sha,
        "corpus_hashes": {item["doc_id"]: item["text_sha256"] for item in manifest},
    }
    with (LOG_ROOT / "audit.jsonl").open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, sort_keys=True) + "\n")


def run(*, as_of: str, address_id: str | None = None) -> dict[str, Any]:
    query_date = date.fromisoformat(as_of)
    addresses = json.loads((BUILD_ROOT / "addresses_resolved.json").read_text())
    if address_id:
        addresses = [item for item in addresses if item["address_id"] == address_id]
        if not addresses:
            raise KeyError(f"Unknown address ID: {address_id}")
    lookups = evaluate_lookups(addresses, _load_rules(), query_date, BUILD_ROOT / "traces")
    payload = {"as_of": as_of, "lookups": lookups}
    if address_id:
        print(json.dumps(payload, indent=2, sort_keys=True))
        return payload
    if as_of == "2026-10-01":
        SUBMISSION_ROOT.mkdir(parents=True, exist_ok=True)
        destination = SUBMISSION_ROOT / "lookups.json"
    else:
        destination = BUILD_ROOT / f"lookups_{as_of}.json"
    destination.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    _log_run(as_of, len(addresses))
    return payload


def run_required_dates() -> None:
    for value in ("2025-12-31", "2026-01-02", "2026-10-01", "2027-07-02"):
        run(as_of=value)
