# Method

Rental Housing Law Navigator is a reproducible research pipeline for answering which supplied rental-housing rules may affect a known address on a given date. It is not legal advice and does not substitute for counsel or a current official code search.

## Pipeline

The input is the organizer-supplied corpus plus optional pages saved by a human into `research/link_only/`. The latter are retained as `link_only_research` and `corpus_text=false`, so they can be distinguished from the supplied corpus throughout the outputs.

Documents are section-chunked. A cached extraction prompt proposes one structured record per jurisdiction, category, and law. The program verifies each supporting quote after normalizing whitespace, quotes, and dashes; a failed quote is retried once and then dropped or snapped only to a sufficiently similar source substring. The extraction cache is keyed by both source content and document identity, and outputs are sorted before writing.

Merge deduplicates on jurisdiction, category, and normalized citation, preferring official material and then higher-confidence records. It unions exemptions, preserves contributing documents, computes enacted/pending/failed status and effective dates, assigns stable `r-####` identifiers, and validates each public record against the provided JSON schema.

The lookup engine is deterministic. For each address/date pair it evaluates the address's state and legal-city stack, date status, coverage predicates, and explicitly encoded state precedence. It emits `applies`, `unknown`, `pending`, `not_yet_effective`, or `superseded` as appropriate. Explanations are fixed templates built from the predicates that made the decision.

## Guardrails and uncertainty

The model never decides a lookup result. It only proposes source-backed records; quote verification, effective-date resolution, coverage, conflicts, and explanations run in code. Missing facts result in `unknown`, not a silent absence. Pending and failed measures never apply. No-rule findings are emitted for every in-scope jurisdiction/category without an in-force rule. Four known open issues are carried into `conflict_notes.json` for human review rather than resolved by assertion. Link-only material remains labeled in the rules and citation-coverage reporting.

## Validation and results

The completed CP3/CP4 run has 71 merged, schema-valid rules and 100% verified quotes. It produces all 500 required lookups and passes T1 250/0, T2 90/0, T3 140/90, T4 110/0, and T5 0/0. Validation checks schema conformance, quotes, citation coverage, lookup completeness, expected counts, jurisdiction and status invariants, explanations, golden cases, and the recall checklist. Warm-cache reruns compare submission JSON byte-for-byte.

## Scalability

Adding a city requires dropping its texts into the corpus, adding any resolved address facts, and rerunning the unchanged pipeline. There is no city-specific manual answer table. Santa Ana demonstrates this path: its rules are extracted although the address dataset contains no Santa Ana rows. Cache identity, sorted writes, stable identifiers, and audit artifacts keep additions repeatable and reviewable.
