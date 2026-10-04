# Rental Housing Law Navigator

Rental Housing Law Navigator turns a supplied corpus of housing-law materials into an auditable, date-specific answer for every address in the organizer dataset. It covers selected California, New Jersey, and Massachusetts state and local rules. It is a research prototype, **not legal advice**.

Live demo: [tokha-t.github.io/velio](https://tokha-t.github.io/velio/).

## Run it

The starter pack is intentionally not redistributed. Put the organizer-supplied `starter_pack/` beside this README. Optional human-saved link-only research belongs in `research/link_only/` using that directory's documented format.

```bash
uv sync
python -m navigator all
```

`all` uses the committed extraction cache when it is warm. Individual stages are available as `extract`, `merge`, `lookup`, `changes`, `no-rule-findings`, and `validate`.

To run the static viewer locally:

```bash
cd web
npm install
npm run dev
```

## How it works

```text
source texts + saved research copies
              │
   cached, quote-verified extraction
              │
 merge + source/date/status normalization
              │
 deterministic coverage and precedence engine
              │
 lookups, changes, no-rule findings, validation, static viewer
```

The model is used only to propose structured records from source text. Every supporting quote is normalized and checked against its source; status, effective dates, coverage, precedence, explanations, and validation are deterministic Python code. The output retains source identifiers, quote ranges, and audit data so an answer can be traced back to the text that supported it.

## Outputs

| File | Purpose |
| --- | --- |
| `submission/rules.json` | Public rule records, schema-validated and sorted. |
| `submission/lookups.json` | All 500 address lookups as of 2026-10-01. |
| `submission/changes.json` | Differences across the four required dates. |
| `submission/no_rule_findings.json` | Explicit no-rule findings; the system does not fill gaps with invented law. |
| `submission/conflict_notes.json` | Human-review notes for source or rule conflicts. |
| `submission/validation_report.md` | Validation, recall, and reproducibility results. |

The completed run contains 71 merged rules with 100% quote verification and 500 dated lookups. CP3/CP4 checks are green: T1 250/0, T2 90/0, T3 140/90, T4 110/0, and T5 0/0. The validation report also records citation coverage and the extraction recall checklist.

## Limits and guardrails

- This covers only the supplied documents and explicitly saved link-only research copies; absence of a rule is reported as a finding, not a legal conclusion.
- A result can be `unknown` when a required fact (for example, construction year or owner status) is missing. It is never silently omitted.
- Pending, failed, and not-yet-effective laws remain visible but are not represented as current law.
- Conflicting sources are flagged for human review. Link-only material is labeled separately from supplied-corpus material.
- The static viewer has no backend and no browser API key.

## Scope and extension

Adding a city is deliberately mundane: add the relevant texts to the corpus, add resolved address facts if any, and rerun the same pipeline. Santa Ana is already an example of an extracted jurisdiction with zero addresses. See the one-page [method note](submission/METHOD.md) for the full pipeline and validation approach.

The project is released under the [MIT License](LICENSE).
