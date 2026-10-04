# Rental Housing Law Navigator

Rental Housing Law Navigator turns a supplied corpus of housing-law materials into auditable, date-specific research results for every address in the organizer dataset. It covers selected California, New Jersey, and Massachusetts state and local rules. This is a research prototype, **not legal advice**.

## Live site

- [Production viewer on Vercel](https://web-seven-rho-19.vercel.app/)

## What it does

- Resolves the legal jurisdiction for 500 supplied rental addresses.
- Extracts quote-backed rules from the supplied corpus and normalized saved research.
- Produces deterministic coverage, effective-date, precedence, conflict, and change-test results.
- Serves those exports through a static Vite viewer with no backend, keys, or browser-side API calls.

## Requirements

- Python 3.12 or later
- [uv](https://docs.astral.sh/uv/)
- Node.js 22 or later for the static viewer
- The organizer-supplied **starter_pack/** placed beside this README. It is intentionally not redistributed.

## Quick start

~~~bash
uv sync
uv run python -m navigator all
~~~

The full pipeline uses the committed extraction cache when it is warm. Optional human-saved link-only research belongs in [research/link_only/](research/link_only/README.md) and follows that directory's documented format.

## Static viewer

Regenerate the browser-ready exports, then start Vite:

~~~bash
uv run python -m navigator export-web
cd web
npm ci
npm run dev
~~~

For a production build:

~~~bash
cd web
npm run build
~~~

## Commands

| Command | Purpose |
| --- | --- |
| uv run python -m navigator extract | Extract quote-verified candidate records from source text. |
| uv run python -m navigator resolve | Resolve addresses and jurisdiction facts. |
| uv run python -m navigator merge | Normalize and merge extracted records. |
| uv run python -m navigator lookup | Create date-specific address lookups. |
| uv run python -m navigator changes | Calculate T1 through T5 change-test outputs. |
| uv run python -m navigator no-rule-findings | Record explicit no-rule findings rather than inferring coverage. |
| uv run python -m navigator validate | Run deterministic validation and write the report. |
| uv run python -m navigator export-web | Copy current public artifacts into web/public/data/. |
| uv run python -m navigator all | Run the complete pipeline. |
| uv run pytest | Run the Python test suite. |
| cd web && npm run build | Type-check and build the static viewer. |

## Architecture

~~~text
supplied source texts + saved link-only research
                    |
       cached, quote-verified extraction
                    |
      merge + source/date/status normalization
                    |
deterministic coverage, precedence, and conflict engine
                    |
lookups + change tests + no-rule findings + validation
                    |
      versioned public exports + static Vite viewer
~~~

The model only proposes structured records from source text. Supporting quotes are normalized and checked against their sources; status, effective dates, coverage, precedence, explanations, and validation are deterministic Python logic. Outputs retain source identifiers, quote ranges, and audit data so a result can be traced to its supporting text.

## Repository layout

| Path | Contents |
| --- | --- |
| [src/navigator/](src/navigator/) | Extraction, jurisdiction, coverage, change-test, validation, and web-export code. |
| [research/](research/) | Saved source material and normalized link-only research. |
| [build/](build/) | Intermediate deterministic artifacts. |
| [submission/](submission/) | Public rule, lookup, change, finding, and validation outputs. |
| [web/](web/) | Vite static viewer and the exported browser data. |

## Outputs

| File | Purpose |
| --- | --- |
| submission/rules.json | Public rule records, schema-validated and sorted. |
| submission/lookups.json | Address lookups as of 2026-10-01. |
| submission/changes.json | Differences across the four required dates. |
| submission/no_rule_findings.json | Explicit no-rule findings; the system does not invent missing law. |
| submission/conflict_notes.json | Human-review notes for source or rule conflicts. |
| submission/validation_report.md | Validation, recall, and reproducibility results. |

The completed run contains 71 merged rules with quote verification and 500 dated lookups. CP3 and CP4 checks are green: T1 250/0, T2 90/0, T3 140/90, T4 110/0, and T5 0/0.

## Limits and guardrails

- Coverage is limited to supplied documents and explicitly saved link-only research. An absent rule is a finding, not a legal conclusion.
- Results can be **unknown** when a required fact, such as construction year or owner status, is missing. They are never silently omitted.
- Pending, failed, and not-yet-effective laws remain visible but are not represented as current law.
- Conflicting sources are flagged for human review. Link-only material is labeled separately from supplied-corpus material.
- The static viewer has no backend and no browser API key.

## Extending the corpus

Adding a city is deliberately ordinary: add relevant source text to the corpus, add resolved address facts if available, and rerun the same pipeline. Santa Ana is already an example of an extracted jurisdiction with zero addresses. Read the one-page [method note](submission/METHOD.md) for the pipeline and validation approach.

## License

Released under the [MIT License](LICENSE).
