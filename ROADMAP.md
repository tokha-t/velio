# ROADMAP — Rental Housing Law Navigator (deadline 18:00 Almaty)

Agents: update the **Status** block when you finish a step: tick it, add one line of notes. All times are Asia/Almaty (UTC+5), Sun 4 Oct 2026.

## Status

- Current phase: **1 — Module A extraction (pilot)**
- Last checkpoint passed: **P0 local setup** (tests, CLI, cache, corpus manifest)
- Blockers: Vercel login remains a Human H1 task; no `.env` API key, so the documented cached `claude_cli` fallback is active.
- Notes: 10:10 — Read CLAUDE.md and ROADMAP.md fully; confirmed a fresh repo and began Lane A P0.
- Notes: 10:14 — Python 3.12 pinned; 6 tests pass; CLI works; Claude smoke response cached; 54 source-text hashes recorded. Creating/pushing private GitHub repo `velio`.
- Notes: 10:18 — Lane B P1b complete: 500 resolved rows, 97.0% Census matches, 99.8% place/confident fallback; CP2 passed.

## Lanes

| Lane | Who | Owns |
|---|---|---|
| **A — Core** | Claude Code session in the repo root | Module A, the engine and the outputs: `corpus, extract, verify, status, merge, coverage, lookup, changes, explain, validate` (.py), `prompts/`, `config/`, `submission/` |
| **B — Edges** | Second agent (Codex or another Claude Code) in a git worktree: `git worktree add ../hn-laneb -b lane-b` | `geocode.py`, `facts.py`, `export_web.py`, `web/`. Merges into `main` at CP2 and CP5 |
| **H — Human** | Tokha | Keys, link-only page saving, review, videos, submission |

## Timeline

| Time | Lane A | Lane B | Human |
|---|---|---|---|
| 08:45–09:15 | **P0** setup | — | H1 keys, GitHub, Vercel |
| 09:15–11:45 | **P1** Module A extraction → **CP1** | **P1b** geocode + facts (09:15–10:45) → **CP2** | H2 save link-only pages (09:30–10:00); review pilot (10:15) |
| 11:45–13:45 | **P2** coverage engine + lookups → **CP3** | **P4a** web UI on mock data (10:45–12:45) | spot-check the jurisdiction report |
| 13:45–14:45 | **P3** Module C + validation → **CP4** | **P4b** real data + Vercel deploy (12:45–15:15) → **CP5** | review UI and report |
| 14:45–16:00 | **P5** findings, notes, stretch, README, METHOD | polish, mobile check | draft video scripts |
| 16:00–16:30 | **P6** freeze: clean rerun, validate, push public → **CP6** | final deploy | test demo in incognito |
| 16:30–17:30 | — | — | **H3** record 3 videos, team photo |
| 17:30–17:50 | — | — | **H4** submit HackOS + Google Form |
| 17:50–18:00 | buffer | buffer | optional: LinkedIn post tagging Hack-Nation (Go Viral award, deadline 18:00) |

---

## P0 — Setup (Lane A + Human), 30 min

- [x] H1: put the LLM key in `.env`. *(Fallback selected: authenticated `claude_cli`; no secret file needed.)*
  - `ANTHROPIC_API_KEY=...` and `NAV_LLM_BACKEND=anthropic`.
  - No key? Use `NAV_LLM_BACKEND=claude_cli` (headless `claude -p`).
  - Also set `NAV_MODEL=claude-sonnet-5-5`.
- [ ] H1: create the GitHub repo (it can start private; it must be public by 16:30) and log in to Vercel. *(Agent is creating private `velio`; Vercel login remains.)*
- [x] `git init`; add the MIT `LICENSE`; `uv init` with Python 3.12; install the dependencies from CLAUDE.md §10.
- [x] Scaffold `src/navigator/` with the CLI stubs from CLAUDE.md §6. `python -m navigator --help` works.
- [x] LLM smoke test: one cached call through `llm.py` on both backends if available. *(Claude CLI available and cached; Anthropic unavailable without a key.)*
- [x] Load the corpus, record our own sha256 per text file (the manifest hashes the original PDF/HTML, so it never matches), print the doc table.

**Done when** `pytest -q` passes, the smoke call is cached under `cache/llm/`, and the first commit is pushed.

## P1 — Module A extraction (Lane A), 09:15–11:45

- [ ] `corpus.py`: load the manifest and texts, strip the 2-line header into metadata, build the normalization map, chunk by section, attach definitions to each chunk.
- [ ] `verify.py`: normalized exact match → retry → `rapidfuzz` snap (≥ 95) → drop. Unit tests with nasty whitespace and curly quotes.
- [ ] `extract.py` + `prompts/extract_v1.md`: pydantic output model with the CLAUDE.md §6.1 fields and predicate vocabulary.
  - The prompt lists the 6 categories, the citation style (§7.8), "only rules stated in this text", and the `doc_kind` labels.
- [ ] **Pilot** on D024 (AB 1482), D069 (FAIR), D036 (JC), D045 (H.5222), D009 (Berkeley coverage). Print the records. **The human reviews for 5 min at ~10:15.**
- [ ] `status.py`: doc kind → status; bill session logic (193rd dead, 194th pending); relative effective-date resolver. Unit test: FAIR → 2027-07-01.
- [ ] Full run on all 54 docs, plus `research/link_only/*.txt` once saved (`corpus_text=false`).
- [ ] `merge.py`: dedupe on (jurisdiction, category, citation), prefer official sources, deterministic sort, `r-0001` IDs, `config/test_rule_map.yaml` by citation pattern.
- [ ] Write `submission/rules.json` and `build/rules_internal.json`. Print stats: rules per jurisdiction × category, quote verification rate, recall checklist.

**CP1 (11:45)**
- `rules.json` validates against the schema.
- 100% of corpus quotes verified; roughly 50–70 records.
- Recall checklist ≥ 80% (of the items with corpus text).
- AB 325, FAIR, S.2983, H.5222, c.40P present with the correct status/date.
- HOB + JC bans present if H2 delivered their pages.

## P1b — Resolve + facts (Lane B), 09:15–10:45

- [x] `geocode.py`: Census one-line geographies (`layers=all`), 6–8 threads, cache → `cache/geocode/`. Retry with the component endpoint. Fallbacks per CLAUDE.md §7.1.
- [x] `facts.py`:
  - year; units; `units_range` from use code/description (NJ `(\d+)\s*U`, class 4C ≥ 5, Boston/SF/Cambridge code ranges);
  - flags (`subsidized` for A/125, `elderly` for A/118, `affordable` from the NJ description);
  - the A0227 fix.
- [x] Write `build/addresses_resolved.json` (500 rows, shape in CLAUDE.md §6.2) and `build/jurisdiction_report.md` (match rate, postal ≠ legal rows, unincorporated rows, low-confidence rows).

**CP2 (10:45):** 500 rows; ≥ 95% geocoded with a place or a confident dataset fallback; the report lists every postal ≠ legal case. Merge `lane-b` → `main`.

## H2 — Save link-only pages (Human), 09:30–10:00

Open each URL in your browser, select all, copy, and paste into `research/link_only/<doc_id>.txt` using the header in `research/link_only/README.md`. Single pages only; no scripts against ecode360.

Must have (T2/T3):
- [ ] D032, D033, D034 Hoboken (ecode360 15252438, 15252470, 46833413). Find which one is ch. 158 Art. II (the algorithmic ban) and which is rent control.
- [ ] D035 Jersey City ban (hudsoncountyview). If Jersey City Code §218-12 is reachable as an official page, save that too, as `D035b.txt`.

Nice to have:
- [ ] D070–D072 Newark (ecode360).
- [ ] D059 WBUR (IP 25-21 struck).
- [ ] D074 SD §98.1103.

## P2 — Coverage engine + lookups (Lane A), 11:45–13:45

- [ ] `coverage.py`: three-valued evaluation of each predicate (CLAUDE.md §6.1), including the year-edge rule and the rolling window from `as_of`.
- [ ] `lookup.py`:
  - stack match → status at date → coverage → supersession (§7.4) → conflict flags (§7.5);
  - decision table §7.3;
  - one trace per address in `build/traces/`.
- [ ] `explain.py`: plain-language templates; every string ends "As of {date}. Not legal advice."
- [ ] Write `submission/lookups.json` (as_of 2026-10-01, all 500), plus `build/lookups_{2025-12-31,2026-01-02,2027-07-02}.json`.
- [ ] `tests/test_golden.py` from the CLAUDE.md §8 expected behaviors.

**CP3 (13:45):** all 500 addresses present; golden tests pass; invariants pass (city rules stay in their city; no MA rent cap; Santa Ana absent; pending/failed never `applies`).

## P3 — Module C + validation (Lane A), 13:45–14:45

- [ ] `changes.py`: T1–T5 per CLAUDE.md §5. Every test always has all three keys. Notes name our rule IDs, the key rule IDs and the dates. Per-rule split goes to `submission/changes_detail.json`.
- [ ] `lookup --as-of <any date> [--address ID]` works from the CLI (the as-of query requirement).
- [ ] `validate.py` covers all 8 checks in CLAUDE.md §9 → `submission/validation_report.md` + `web/data/validation.json`.

**CP4 (14:45)**
- T1 250 · T2 90 (HOB 40 / JC 50 / Newark 0) · T3 140 + 90 flagged · T4 110 · T5 0.
- Validation report all green, or every red item explained.

## P4 — Demo web app (Lane B)

**P4a (10:45–12:45), mock data matching the contract:**
- [ ] Persistent banner: **"Not legal advice. Prototype for a hackathon."**
- [ ] As-of selector: 2025-12-31 · 2026-01-02 · **2026-10-01** · 2027-07-02.
- [ ] Address search over all 500 (street or ID).
- [ ] Jurisdiction stack card: postal city vs legal city, geocode method, confidence.
- [ ] Rules grouped by the 6 categories:
  - result badge, plain-language explanation, key value, citation;
  - expandable verbatim quote, source link, retrieval date, conflict icon + note;
  - "research copy, not corpus" tag;
  - "No rule found at this level" rows from `no_rule_findings.json`.
- [ ] Tab **Change tests**: T1–T5 cards with before/after, counts, and affected address lists.
- [ ] Tab **Pipeline & audit**: rules table with filters, extraction stats, validation report.

**P4b (12:45–15:15)**
- [ ] `export_web.py` writes the real `web/data/*.json` (rules, addresses_resolved, lookups for the 4 dates, changes, no_rule_findings, validation).
- [ ] Deploy to Vercel and test on a phone.

**CP5 (15:15):** the public URL loads with real data in under 3 s on a fresh browser. Merge `lane-b` → `main`.

## P5 — Findings, docs, stretch (Lane A), 14:45–16:00

- [ ] `submission/no_rule_findings.json` (§7.7).
- [ ] Conflict notes for the four open questions (§7.5).
- [ ] `README.md`: what it does, how to run (`uv sync && python -m navigator all`), where the starter pack goes, architecture diagram, outputs, validation numbers, limitations, not legal advice.
- [ ] `submission/METHOD.md`, one page: pipeline, guardrails, uncertainty handling, validation numbers, scalability path (adding a city = drop texts into the corpus, rerun the same pipeline; Santa Ana proves it with zero addresses).
- [ ] Stretch, only if CP4 is green:
  1. Confidence per answer = f(quote verified, source tier, date certainty, fact completeness).
  2. Spanish templates.
  3. Arbitrary-date picker computed client-side.

## P6 — Freeze and reproduce (Lane A + B), 16:00–16:30

- [ ] Fresh clone → `uv sync` → `python -m navigator all` with warm caches → `git diff --exit-code submission/` passes.
- [ ] `pytest -q` and `validate` are green. No secrets in the repo (`git grep -i "sk-ant"` is empty).
- [ ] Repo **public**, MIT `LICENSE` present, README links the demo.

**CP6 (16:30):** feature freeze. After this, only video and submission work.

## H3 — Videos (≤ 60 s each, MP4/MOV) + photo, 16:30–17:30

**1. Team intro**
- Who you are: CS student at Coventry University Kazakhstan, ICPC competitor, solo builder.
- Why this problem: housing law is layered; the answer depends on one address and one date.
- What you built, in one line.

**2. Product demo, real UI, no slides**
- Pick an SF 1960s building: SF rent control applies, AB 1482 superseded; open a verbatim quote with its source and retrieval date.
- Switch to a Hoboken address: local ban + FAIR Act conflict flag.
- Flip the as-of date to 2027-07-02: FAIR applies.
- Open a Boston address: no rent cap (c.40P), bills pending, ballot question failed.

**3. Tech walkthrough**
- The pipeline diagram.
- "The LLM only extracts; code verifies every quote and computes every date and status."
- Show the validation report:
  - schema ✓;
  - quote verification %;
  - T1–T5 counts;
  - citation share with and without the research copies.
- Limits: link-only texts, owner data, certificate-of-occupancy dates.

Photo: JPG/PNG/WebP ≤ 10 MB.

## H4 — Submit, 17:30–17:50 (both are required)

- [ ] **HackOS** project page:
  - Name; challenge "02 - Realpage: Rental Housing Law Navigator"; GitHub URL; live URL;
  - photo and the 3 videos;
  - **Submit project**.
- [ ] **Google Form** `forms.gle/VS65tsovASMuBwEn9`:
  - Solo; name and email; affiliation; challenge "2. RealPage";
  - 3 video uploads; GitHub URL; demo URL; photo link;
  - agree to the MIT terms → **Submit**. There are no re-submissions.
- [ ] The repo contains `submission/rules.json`, `lookups.json`, `changes.json` and `METHOD.md`.

## Cut lines (drop from the top when behind)

1. Spanish view.
2. Confidence scores.
3. Arbitrary-date picker in the UI (the CLI still covers it).
4. Pipeline & audit tab (keep the validation report in the README).
5. Nice-to-have link-only pages (Newark, WBUR, SD).
6. Web polish: ship a plain table UI rather than miss CP5.

**Never cut:**
- A + B on all 500 addresses.
- Verified quotes.
- T1–T5.
- "Not legal advice" everywhere.
- Both submissions.

**Fallbacks**
- Geocoder down or slow: dataset-based jurisdiction with low confidence and `unknown` city rules for county datasets (CLAUDE.md §7.1).
- LLM backend failing: switch `NAV_LLM_BACKEND`.
- Running late at 12:30: freeze extraction as-is and move on to P2.

---

## Kickoff prompts (paste one into the matching agent session)

**Lane A — P0+P1:**
> Read CLAUDE.md and ROADMAP.md fully. Do P0, then P1 exactly as written. Stop after the pilot (5 docs) and show me the records before the full run. Keep everything deterministic and cached. Update the ROADMAP Status block as you go.

**Lane B — P1b:**
> Read CLAUDE.md and ROADMAP.md fully. You are Lane B in a git worktree on branch `lane-b`. Do P1b only: `geocode.py` and `facts.py` → `build/addresses_resolved.json` + `build/jurisdiction_report.md`. Don't touch Lane A files. Show me the report, then stop.

**Lane A — P2:**
> Do P2 from ROADMAP.md. Follow CLAUDE.md §6.1, §7.3–7.6 exactly. Write `tests/test_golden.py` from §8 first, then make it pass. Report the CP3 checks.

**Lane A — P3:**
> Do P3. Produce `changes.json` per CLAUDE.md §5 and the full validation report per §9. Report the CP4 numbers.

**Lane B — P4a/P4b:**
> Do P4a with mock data that exactly matches the JSON shapes in CLAUDE.md §3.1, §6.1, §6.2. Then P4b: wire `export_web.py` and deploy to Vercel. Static only, no backend, no keys in the browser.

**Lane A — P5/P6:**
> Do P5 (docs first, stretch only if CP4 is green), then P6. Show me README.md and METHOD.md before pushing public.
