from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

Category = Literal["rent_increase_limits", "just_cause_eviction", "security_deposits", "application_screening_fees", "screening_restrictions", "algorithmic_rent_setting"]
DocKind = Literal["statute", "ordinance", "regulation", "bill", "motion", "ballot_measure", "agency_guidance", "news"]


class Predicate(BaseModel):
    type: Literal["built_on_or_before", "built_after", "rolling_new_construction_exempt_years", "min_units", "max_units", "owner_occupied_exempt_max_units", "owner_type", "special_status_exemptions", "tenant_level_conditions"]
    parameters: dict[str, Any] = Field(default_factory=dict)


class CoverageConditions(BaseModel):
    text: str
    predicates: list[Predicate] = Field(default_factory=list)


class ExtractedRule(BaseModel):
    jurisdiction: str
    level: Literal["state", "city"]
    category: Category
    title: str
    requirement: str
    citation: str
    quoted_span: str = Field(min_length=20, max_length=400)
    doc_kind: DocKind
    enacted_date: str | None = None
    effective_date_text: str | None = None
    key_value: str | None = None
    exemptions: list[str] = Field(default_factory=list)
    yields_to_local: bool = False
    coverage_conditions: CoverageConditions
    confidence: float = Field(ge=0, le=1)


class ExtractionResponse(BaseModel):
    rules: list[ExtractedRule] = Field(default_factory=list)
    no_rule_reason: str | None = None
