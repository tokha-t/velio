# CLAUDE.md — Rental Housing Law Navigator

Hack-Nation 7th Global AI Hackathon · Challenge 02 (RealPage) · solo team "NewMoon" (Tokha) + coding agents.

This file is the single source of truth for every agent in this repo (Codex reads it through AGENTS.md).
Read it fully before writing code. Track progress in `ROADMAP.md`, not here.

---

## 0. Mission and clock

Build an AI system that answers, for each of the 500 sample addresses: **which housing rules apply on the query date, and how do the five supplied change cases affect the answer?**

- **Module A, Extract:** read the supplied corpus and emit one structured rule record per rule (LLM, automated).
- **Module B, Resolve + Apply:** geocode each address to its legal jurisdiction stack, test each rule's coverage against building facts, report every applicable rule with a citation.
- **Module C, Track:** run change tests T1–T5 and support an as-of-date query.

| Time (Asia/Almaty, UTC+5) | Event |
|---|---|
| 16:30 Oct 4 | Feature freeze (our rule) |
| **18:00 Oct 4** | **Submission deadline** (= 13:00 UTC = 09:00 ET) |
| 18:15 Oct 4 | Upload grace period ends |

Default query date: **`2026-10-01`**. Minimum viable entry: Modules A + B on all 500 addresses. Then C. Then stretch.

---

## 1. Non-negotiable rules

1. **Extraction is automated.** Every rule record comes from the pipeline reading a document. Never hand-write rule records, values, dates or quotes. Config may hold vocabularies, prompts, and the test-ID map in §5; it may not hold law.
2. **Quotes are verified by code.** `quoted_span` must be an exact substring of its source text after normalization (§7.8). A record whose quote fails verification is retried, then snapped by fuzzy match, then dropped. Never ship an unverified quote.
3. **The LLM runs only in Module A.** Status, effective dates, jurisdiction, coverage, supersession, conflict flags, lookups, change tests and explanations are deterministic Python. Same inputs → byte-identical outputs.
4. **"unknown" beats guessing.** If a rule's geography matches the address and a needed fact is missing, report `unknown`. Never silently omit it: a missed applicable rule is the costliest error.
5. **"Not legal advice"** on every UI view and in every output's notes. Every answer shows its as-of date. Keep enacted, pending, not-yet-effective and failed law visibly separate.
6. Never suggest ways to avoid or structure around a rule. Never score tenants. No non-public data.
7. No bulk scraping. ecode360, amlegal, Municode, gocodebook: single pages read by a human only (§7.9). Never use BrightData (an event perk) or any unblocker or proxy to get past a site's blocks: that breaks the organizers' "if their terms allow it" condition.
8. `starter_pack/` is read-only input. Never edit it.
9. Secrets live in `.env` only (gitignored). The repo goes public under MIT at submission.

---

## 2. Organizer clarifications (official track chat, Oct 4) — these override older docs

1. **The v5 participant release is current.** `score.py` and the dev answer key will **not** be shared. Older brief/video references to them are stale. Videos must show **our own system output and our own validation** (§9), not score.py.
2. **The hour-16 ordinance is removed.** There are exactly five change tests, **T1–T5**, all defined in `starter_pack/dev/change_tests.json`.
3. **Link-only texts** we save ourselves may be used for research if their terms allow, but they **do not count toward the citation metric** unless organizers add them to the corpus. The citation metric counts only supplied, verifiable corpus text.

`notes/research/*.md` mention T6, score.py and "hour 16". Ignore those parts. Their law findings are research leads only and are never an output source.

---

## 3. Deliverables

### 3.1 Challenge package (v5 brief + participant guide)

| File | Exact shape |
|---|---|
| `submission/rules.json` | `{"rules": [record, ...]}` (template form; the guide also says "a list", so the template wins). Each record validates against `starter_pack/schema/rule_record.schema.json`. |
| `submission/lookups.json` | `{"as_of": "2026-10-01", "lookups": {"A0001": [{"team_rule_id", "result", "explanation", "conflict_flag"}, ...], ...}}`, **all 500 addresses** |
| `submission/changes.json` | `{"T1": {"affected_address_ids": [...], "conflict_flag_address_ids": [...], "notes": "..."}, ... "T5": {...}}`; always include all three keys |
| `submission/METHOD.md` | One-page method note |
| Live demo | Hosted URL (Vercel) |

Schema-required fields: `team_rule_id, jurisdiction, level, category, status, title, requirement, citation, source_url, quoted_span` (quote ≥ 20 chars).

- `jurisdiction`: `"CA" | "NJ" | "MA"` or `"City, ST"`.
- `level`: `state | city` (no county level exists in the schema).
- `category`: `rent_increase_limits | just_cause_eviction | security_deposits | application_screening_fees | screening_restrictions | algorithmic_rent_setting`.
- `status` (as of 2026-10-01): `in_force | not_yet_effective | pending | failed`.
- `effective_date`: `YYYY`, `YYYY-MM` or `YYYY-MM-DD`.

Always fill the optional `source_doc_id`, `effective_date`, `key_value`, `exemptions` and `confidence`. The schema has no `additionalProperties: false`, so extras are allowed; add `retrieved_at`, `quote_verified`, `source_tier`, `corpus_text`, `test_rule_ids`.

**Lookup `result` values:** `applies` (in force, covers address) · `unknown` (coverage depends on missing facts) · `superseded` (covered, but a stricter rule at another level governs) · `not_yet_effective` · `pending`. Rules that don't apply are left out. `failed` rules never appear in lookups.

### 3.2 Hack-Nation package (submit on HackOS **and** the Google Form)

- Three videos, each **≤ 60 s**, MP4/MOV ≤ 1 GB:
  - Team intro.
  - Product demo.
  - Tech walkthrough: what was hard, how we solved it, remaining limits.
- Public GitHub repo with a README (setup + description), the submission JSONs, and an MIT license.
- Hosted demo URL and a team photo (JPG/PNG/WebP ≤ 10 MB).
- Form answers: Solo; challenge "2. RealPage"; affiliation Coventry University Kazakhstan.

How we are judged:
- **Hack-Nation form rubric:** technical depth, communication, innovation — ⅓ each.
- **Challenge scoring:** the earlier brief weighted extraction 25, address coverage 20 (a missed applicable rule cost 2×; "unknown" earned partial credit), citations 15, change tracking 15, plain language 10, responsible design 10, scalability path 5. v5 dropped the published weights. Treat them as the best proxy.

### 3.3 Event perks (claimed on HackOS; codes never go in the repo)

| Perk | Use in this build |
|---|---|
| Anthropic API credits ($25) | HackOS marks the shared pool "All Redeemed". If the credits reached the Console, set `ANTHROPIC_API_KEY` and use `NAV_LLM_BACKEND=anthropic` (fastest, parallel). Otherwise stay on `claude_cli` and run 4–6 `claude -p` calls in parallel. |
| ElevenLabs Creator, 1 month (131k credits) | Optional voice-over for the demo and tech videos. The code comes from the ElevenLabs Discord bot, using the Luma email. The team intro stays in Tokha's own voice. |
| Lovable Pro, 1 month (100 credits) | Fallback for the web UI if Lane B slips. Lovable is an accepted demo host on the submission form. Build from the same JSON contract (§3.1, §6). |
| BrightData ($300) | Not used in this track (rule 7). |

The participation certificate unlocks after 18:00: set the name under HackOS → Certificate.

---

## 4. Inputs (`starter_pack/`)

### 4.1 Corpus

- **87 documents** in `corpus/corpus_manifest.csv` (`doc_id, jurisdictions, url, source_type, capture, retrieved_at, sha256, text_file, status`).
- **54 have text** in `corpus/text/DNNN.txt`. Each file starts with `SOURCE: <url>` / `RETRIEVED: YYYY-MM-DD HH:MM UTC`, then raw page text with navigation boilerplate.
- **33 are link-only** (`corpus/links_only.csv`): 23 secondary, 9 code-publisher "check-terms", plus D056 (MA CORI regulations; official, failed with a 403).
- The manifest `sha256` hashes the **original capture** (PDF/HTML bytes), not the `.txt` file: all 54 differ, as checked. Don't verify text against it. Compute our own sha256 per text file and record it in the run manifest and audit log.

| Jurisdiction | Text docs (citable) | Link-only (not citable) |
|---|---|---|
| CA state | D016 CRD fair housing · D022 **AB 325** bill text · D023 Civ §1946.2 · D024 Civ §1947.12 · D025 Civ §1950.5 · D026 Civ §1950.6 · D027 Gov §12955 | D015, D017–D021 (mirrors of the same codes), D028. **SB 763 has no text anywhere.** |
| Los Angeles | D039 2024 council **motion** (not law) · D040 Just Cause Ordinance · D041 RSO overview · D042 RSO calculator · D043 relocation bulletins | D038 LAMC, D044 deposit interest |
| San Francisco | D078 Fair Chance · D079 just cause · D080 annual increase 3/1/26–2/28/27 · D081 algorithmic-device ban · D082 relocation archive · D083 current rates | — |
| San Diego | D073 SDMC ch. 9 art. 8 div. 7 · D076 algorithmic ordinance **materials (Apr 2025, pre-adoption)** | D074 SDMC §98.1103, D075 source-of-income division, D077 |
| Berkeley | D001 Ord. 7,992-N.S. (ch. 13.63, Dec 2025) · D003 Fair Chance · D004 2026 relocation · D005 screening & fees · D006 Measure BB · D007 deposits · D008 AGA notice · D009 coverage by unit type | D002 |
| Santa Ana (no addresses) | D084 rent stabilization · D085 RSO + just-cause adoption | D086, D087 (algorithmic ban news) |
| NJ state | D065 P.L.2021 c.110 Fair Chance in Housing · D066 P.L.2025 c.405 app-fee cap · D067 DCA *Truth in Renting* (161 KB: Anti-Eviction Act, deposits, rent control…) · D068 DCR know-your-rights · D069 **P.L.2026 c.43 FAIR Act** | D060, D061 N.J.S.A. 10:5-12, D062 2A:18-61.1, D063 46:8-21.2, D064 46:8-26 |
| Jersey City | D036 landlord/tenant page: "Rent Control Ordinance, Chapter 260"; "All 1-4 Unit Properties are exempt from rent control" | **D035, D037: algorithmic ban §218-12** |
| Hoboken | — | **D032–D034** (ecode360: rent control + ch. 158 algorithmic ban) |
| Newark | — | **D070–D072** (ecode360) |
| MA state | D045 **H.5222** · D046 **S.2983** · D047 S.2983 history · D048 **c.40P §4** · D049 c.151B §4 · D050 c.186 §11 · D051 §12 · D052 §15B · D053 §18 · D057 c.112 §87DDD½ · D058 c.186 §31 | D054, D055 (Cella blog), D056, **D059 (ballot question struck)** |
| Boston | D010 Fair Chance Tenant Selection Policy (2017; DND-funded/IDP units only) · D011 **H.3744, 193rd session, sent to study = dead** · D012 fair housing regs · D013 HSNA · D014 HSNA FAQ | — |
| Cambridge | D029 Human Rights Commission · D031 tenant-rights notification ordinance | D030 |

**Consequence:** the T2 rules (Hoboken + Jersey City bans), Hoboken/Newark rent control and the MA ballot question have **no corpus text**. Handle them in the link-only research lane (§7.9).

### 4.2 Sample addresses (`data/sample_addresses.csv`, 500 rows)

Columns: `address_id, street_address, postal_city, state, zip, year_built, units, use_code, use_description, source_dataset, retrieved_at`.

IDs are interleaved across cities; derive the city from the data, never from ID ranges.

| City | n | Source dataset | Year built | Units | Unit range from use code/description | Legal-city certainty |
|---|---|---|---|---|---|---|
| Los Angeles | 80 | LA County eGIS | 74 | 77 | `0500`, `0501`, `050C`, `050V`, `0551` = "Five or more apartments" → ≥5 | County dataset: **geocode** (unincorporated areas use "Los Angeles" mail) |
| San Francisco | 80 | DataSF | 78 | 80 | `A5`, `F5`, `FS5` 5–14 · `A15` ≥15 · `TIC` ≤4 | City-county dataset: certain |
| San Diego | 50 (1 "San Ysidro") | SANDAG | **0** | 50 | landuse 14–16 → ≥5 | County dataset: **geocode** |
| Berkeley | 40 | Alameda County | **0** | **0** | `7200`, `7700`, `7800` → ≥5 | County dataset: **geocode** |
| Jersey City / Hoboken / Newark | 50 / 40 / 50 | NJ MOD-IV | 28 / 4 / 2 | ~0 | Class **4C = apartments, 5+ units**; parse `(\d+)\s*U` from `use_description` (100 of 140 have it) | Municipality-coded: near-certain, verify |
| Boston | 60 (postal Dorchester, Roxbury, East Boston, Brighton, Allston…) | Boston assessor | 52 | **0** | `A/112` 7–30 · `A/120` luxury apt · `A/125` subsidized S-8 · `A/118` elderly home | Boston-only dataset: certain (neighborhood ≠ city) |
| Cambridge | 50 | Cambridge assessor | 50 | 50 | `111` 4–8 · `112` >8 | Certain |

Data quirks:
- **A0227 (Hoboken):** `units=2`, but the description `13B-93U-2C-G` says 93 units in class 4C. Trust class + description, and log it.
- **Edge rows:**
  - LA built 1978: A0107, A0432 (RSO cutoff 1978-10-01 → `unknown`).
  - CA built ≥ 2012: A0022, A0210, A0330, A0492, A0105 (inside AB 1482's 15-year window).
  - LA with no year: A0200, A0235, A0267, A0285, A0353, A0417.
  - SF with no year: A0106, A0257.
- NJ known years: Jersey City 1870–1930; Hoboken 2000–2010 (4 rows); Newark 1900–1910.

---

## 5. Change tests (`starter_pack/dev/change_tests.json`)

Rule IDs in the test file are the answer key's IDs. Map them to our `team_rule_id`s in `config/test_rule_map.yaml` **by citation pattern**, and record the mapping in each test's `notes`.

| Test | Key rule IDs | Our source | Dates | Expected | Affected set |
|---|---|---|---|---|---|
| T1 | CA-ALG-01 | AB 325 (D022) | 2025-12-31 vs 2026-01-02 | `not_yet_effective` → `applies`, every CA address | all **250** CA |
| T2 | HOB-ALG-01, JC-ALG-01 | link-only lane (§7.9) | 2026-10-01 | Hoboken ban only in Hoboken, JC ban only in JC, neither in Newark | **90** = Hoboken 40 ∪ JC 50 (per-rule split in notes + `submission/changes_detail.json`) |
| T3 | NJ-ALG-01 | FAIR Act (D069) | 2026-10-01 vs 2027-07-02 | `not_yet_effective` → `applies`, every NJ address | all **140** NJ; `conflict_flag_address_ids` = JC + Hoboken (**90**) |
| T4 | MA-ALG-P1, MA-ALG-P2 | S.2983 (D046/D047), H.5222 (D045); treat P1 = S.2983, P2 = H.5222 (title order) | 2026-10-01 | `pending`, never in force, every MA address | all **110** MA (if enacted) |
| T5 | MA-RENT-P1 | IP 25-21 (link-only D059/D055) | 2026-10-01 | no rent cap for any Boston/Cambridge address; IP 25-21 recorded as `failed` | **empty** |

"Affected" means addresses whose result for the test rule changes between the two dates (T1, T3), or addresses the rule reaches (T2, T4). Counts assume geocoding confirms the cities. If geocoding moves an address out of a city, follow the geocoder and explain it in notes.

---

## 6. Architecture

```
starter_pack/corpus ─► corpus.py (load, sha256, normalize, chunk by section)
                        └─► extract.py (LLM, structured JSON) ─► verify.py (quote check)
                              └─► status.py (doc kind, dates, status in code) ─► merge.py (dedupe, ids)
                                    └─► build/rules_internal.json ─► submission/rules.json
starter_pack/data ─► geocode.py (Census) + facts.py (units/year ranges) ─► build/addresses_resolved.json
rules + addresses ─► coverage.py (3-valued predicates) ─► lookup.py (stack, supersession, conflicts, explain.py)
                        └─► submission/lookups.json + build/lookups_<date>.json + build/traces/
lookup engine ─► changes.py (T1–T5) ─► submission/changes.json
everything ─► validate.py ─► submission/validation_report.md ; export_web.py ─► web/data/*.json
```

- Package `src/navigator/`, CLI `python -m navigator <cmd>`: `extract`, `resolve`, `lookup --as-of D [--address ID]`, `changes`, `validate`, `export-web`, `all`.
- **LLM layer (`llm.py`):**
  - Backend `anthropic` (SDK, `ANTHROPIC_API_KEY`) or `claude_cli` (`claude -p --output-format json`, uses the Claude subscription). Pick via `NAV_LLM_BACKEND`.
  - Model from `NAV_MODEL`, default `claude-sonnet-5-5`.
  - Every response is cached at `cache/llm/<sha256(prompt_version|model|chunk)>.json` and **committed**, so `all` reruns offline and deterministically.
  - Prompts live in `prompts/` with a `PROMPT_VERSION`.
- **Audit log:** append-only `logs/audit.jsonl`. Log every LLM call (doc, chunk hash, model, prompt version, response hash, timestamp) and every run (corpus hashes, git sha, as_of).
- **Decision traces:** one file per address in `build/traces/`, listing the predicates evaluated and the facts used.

### 6.1 Internal rule record (superset of the schema)

Schema fields, plus:
- `source_doc_id`, `retrieved_at`.
- `doc_kind`: `statute | ordinance | regulation | bill | motion | ballot_measure | agency_guidance | news`.
- `enacted_date`, `effective_rule_text` (e.g. "first day of the twelfth month next following enactment").
- `quote_verified`, `quote_char_range`.
- `source_tier`: `official | code_publisher | secondary | link_only_research`; `corpus_text` (bool).
- `yields_to_local` (bool, from the text).
- `coverage_conditions = {"text": str, "predicates": [...]}`. The schema allows an object here.
- `test_rule_ids`.

**Predicate vocabulary.** The LLM fills only these; the engine evaluates them:

| Predicate | Meaning | Evaluation |
|---|---|---|
| `built_on_or_before {date, basis: certificate_of_occupancy\|year_built}` | Construction cutoff | year < cutoff year → true; year > cutoff year → false; same year with CO basis → **unknown**; missing year → unknown |
| `built_after {date, basis}` | Inverse cutoff | Same edge rule |
| `rolling_new_construction_exempt_years {n}` | e.g. AB 1482's 15 years | Cutoff = as_of − n years, then the edge rule |
| `min_units {n}` / `max_units {n}` | Unit thresholds | Exact units, else the `units_range` from facts; decided only if the whole range agrees |
| `owner_occupied_exempt_max_units {n}` | e.g. NJ ≤ 2 | Range min > n → exemption impossible (true); else unknown |
| `owner_type {text, max_units_if_small_landlord?}` | e.g. CA 1950.5(c)(5) | No owner data → unknown, unless units rule it out (> 4 units offered → exception impossible) |
| `special_status_exemptions [text]` | Affordable, subsidized, dorm, hotel, shared kitchen, ADU… | Assume not triggered and say so in the explanation, **unless** facts flag it (Boston `A/125`, `A/118`, NJ description containing `AFFORDABL`) → unknown |
| `tenant_level_conditions [text]` | Tenancy ≥ 12 months, service member… | Never blocks the address-level result; mention in the explanation |

### 6.2 Resolved address record

```json
{"address_id": "A0001", "postal_city": "Los Angeles", "state": "CA",
 "geocode": {"matched": true, "method": "census_oneline", "place_name": "Los Angeles city",
             "place_geoid": "0644000", "county": "Los Angeles County", "lat": 0.0, "lon": 0.0},
 "legal_city": "Los Angeles, CA", "stack": ["CA", "Los Angeles, CA"], "jurisdiction_confidence": "high",
 "facts": {"year_built": 1927, "units": 32, "units_range": [32, 32], "units_source": "column",
           "flags": []}}
```

---

## 7. Domain logic

### 7.1 Jurisdiction resolution (Module B)

- **Census Geocoder**, one-line geographies endpoint: `benchmark=Public_AR_Current`, `vintage=Current_Current`, `layers=all`. Read `Incorporated Places` (name + GEOID).
  - The batch endpoint returns tract/block, not place. Use the one-line call with 6–8 threads and cache to `cache/geocode/`, committed.
- **Retry** unmatched rows with the component endpoint (street/city/state/zip).
- **Still unmatched:**
  - City-only datasets (DataSF, Boston, Cambridge, NJ MOD-IV) → dataset city, confidence `high`.
  - County datasets (LA, SANDAG, Alameda) → postal city with confidence `low`; city-level rules become `unknown` with an explanation.
- **No incorporated place** → stack is `[STATE]` only. Explain: "unincorporated county; county rules are not in this corpus".
- Report every row where postal city ≠ legal city in `build/jurisdiction_report.md` (good demo material).

### 7.2 Status and dates — computed in code, never taken from the model

- `doc_kind = motion` (e.g. D039) → not a rule. Emit a no-rule finding instead.
- **Bills:**
  - Current 194th session and not enacted → `pending` (D045, D046/D047).
  - Earlier session ended → `failed` (D011, H.3744, 193rd, "accompanied a study order").
- Ballot question struck → `failed` (IP 25-21).
- **Effective dates:**
  - Explicit date → use it.
  - Relative rule + enactment date → resolve in code. Unit-test both of these:
    - FAIR §9 (D069): approved 2026-07-20, "first day of the twelfth month next following the date of enactment" → **2027-07-01**.
    - P.L.2025 c.405 §3 (D066): approved 2026-01-20, "first day of the fourth month next following the date of enactment" → **2026-05-01**.
  - No date → `null` plus a note.
- **Status at query date `d`:**
  - Enacted with `effective_date > d` → `not_yet_effective`.
  - Pending stays pending; failed stays failed.
  - Otherwise `in_force`.
- `rules.json` status is computed at 2026-10-01. Other dates go through the engine.

### 7.3 Result decision table, per (address, rule, as_of)

| Rule state | Coverage | Result |
|---|---|---|
| Rule jurisdiction not in address stack | — | omit |
| `failed` | — | omit (still listed in `rules.json` and test notes) |
| `pending` | geography matches | `pending` |
| Effective after `d` | geography matches | `not_yet_effective` |
| In force | true | `applies`, or `superseded` (§7.4) |
| In force | unknown | `unknown` |
| In force | false | omit |

### 7.4 Precedence and supersession, per state

**CA:**
- State law sets the floor.
- Civ §1947.12 (AB 1482) yields to stricter local rent control: where a local rent-control rule `applies` → `superseded`; where it is `unknown` → `unknown`; where it doesn't apply → evaluate AB 1482 normally.
- Civ §1946.2 yields to more protective local just-cause ordinances when its extracted text says so (`yields_to_local`).
- AB 325 coexists with local algorithmic bans: both `apply`.

**NJ:**
- No state rent control. City rent control: JC ch. 260 (D036), Hoboken and Newark (link-only).
- New-construction exemption, extracted from D067: "Under the Newly Constructed Multiple Dwellings Law (N.J.S.A. 2A:42-84.5), newly constructed multiple dwellings shall be exempt from any local rent control ordinances for a period of 30 years following completion of construction".
  - This is a rolling 30-year window from as_of: at 2026-10-01, built ≥ 1997 is eligible and 1996 is the edge year.
  - Eligible or missing year → city rent control `unknown`. The exemption hinges on an owner filing that isn't in the data; the organizers' own `lookups.json` template says exactly this.
  - Known year ≤ 1995 → `applies` to 5+ unit buildings. JC years are 1870–1930; Hoboken has 2000–2010.
  - The law's 1987 start date is not in the corpus. Don't use it.
- Statewide (all `apply` to 4C buildings): Anti-Eviction Act, deposit act, P.L.2025 c.405 fee cap, Fair Chance in Housing Act, LAD.

**MA:**
- **c.40P §4 bars local rent control.** It is an in-force state rule that `applies` to every MA address. Its key value is "no rent cap — local rent control prohibited". It is not a cap.
- No city rent caps. H.3744 is dead. IP 25-21 failed.
- S.2983 and H.5222 → `pending` for all MA addresses.

### 7.5 Conflict flags (→ `conflict_flag: true` + `conflict_note`; the README calls these a bonus)

- **FAIR Act vs JC/Hoboken bans:** §6(b), "A municipality shall be prohibited from enacting an ordinance that conflicts with this act". It bars *enacting*; it doesn't name or void the existing bans. Flag "possible conflict — human review" on JC and Hoboken addresses. **Never** mark the local bans `superseded`.
- **Berkeley ch. 13.63 effective date:** March 1, 2026 in the ordinance text vs January 2026 in a law-firm alert.
- **LA RSO new formula effective date:** 2026-02-02 (LAHD, D041/D042) vs 2026-01-24 (landlord association).
- **CA screening-fee cap:** no single official 2026 dollar figure. Output the formula from Civ §1950.6 and flag it.

### 7.6 Explanations (`explain.py`)

- Template-based, no LLM, written at a 6th–8th grade reading level. Built from the predicates that decided the result.
  - Example: "Applies: the LA Rent Stabilization Ordinance covers buildings first built on or before Oct 1, 1978 with 2+ units; this building was built in 1927 with 32 units."
  - For `unknown`, name the missing fact.
- Always end with: "As of 2026-10-01. Not legal advice."
- Spanish (stretch): translate the fixed templates once, review them, store them, and never generate free text.

### 7.7 No-rule findings (automatic)

For every in-scope jurisdiction × category with no in-force rule, emit `submission/no_rule_findings.json` (`jurisdiction, category, reason, docs_checked`).
- Examples: Boston/Cambridge rent caps (c.40P, H.3744 failed, IP 25-21 failed); LA algorithmic (only a 2024 motion).
- Show these in the UI. They prove the system doesn't invent rules.

### 7.8 Extraction details (Module A)

- **Chunk** by section markers (`§`, `Section`, `SEC.`, numbered headings). Max ~6k tokens per chunk. Prepend the document's definitions section to every chunk. Small docs go in as one chunk. D067 (161 KB) and D049 (56 KB) must be chunked.
- **Granularity:** one record per (jurisdiction, category, law), not per subsection. Fold exceptions into `exemptions`. Expect roughly **50–70 records**; 150+ means over-splitting, so merge. Dedupe key: `(jurisdiction, category, normalized citation)`. Prefer official > code_publisher > secondary sources.
- **Citation style:** `Cal. Civ. Code § 1947.12` · `Cal. Bus. & Prof. Code § 16729 (AB 325)` · `S.F. Admin. Code ch. 37` · `L.A. Mun. Code ch. XV (RSO)` · `Berkeley Mun. Code ch. 13.63` · `N.J.S.A. 46:8-21.2` · `P.L.2026, c.43` · `M.G.L. c. 186, § 15B` · `M.G.L. c. 40P, § 4` · `Mass. H.5222 (194th)`.
- **Quote normalization:** before matching, normalize both sides (NBSP→space, curly quotes→straight, en/em dashes→`-`, collapse whitespace).
  - Match against the raw file and store the char range.
  - On a miss, retry once with a "copy verbatim" prompt, then snap with `rapidfuzz` (partial ratio ≥ 95) to the real substring, else drop.
  - Quotes run 20–400 chars and support the requirement.
- **Recall checklist** (from the earlier brief's examples; for `validate.py` only, never a source of rules):
  - CA: Civ 1947.12, 1946.2, 1950.5, 1950.6; Gov 12955 SOI; AB 325.
  - CA cities: SF ch. 37 + §37.10C, LA RSO, San Diego §§98.1101–98.1104, Berkeley 13.63, Santa Ana NS-3090.
  - NJ: 2A:18-61.1, 46:8-21.2, P.L.2025 c.405, Fair Chance P.L.2021 c.110, P.L.2026 c.43, JC §218-12, Hoboken ch. 158 Art. II.
  - MA: c.40P, c.186 §15B, c.112 §87DDD½, S.2983, H.5222.

### 7.9 Link-only research lane

For T2 and the gaps in §4.1:
1. A human saves single pages by hand (browser → copy text) into `research/link_only/DNNN.txt` with the same header plus `NOTE: research copy — not supplied corpus`. Format is in `research/link_only/README.md`.
2. Run the same extractor on them. Set `source_tier = link_only_research`, `corpus_text = false`. Verify quotes against the saved copy.
3. Keep these records in `rules.json` (extraction credit, T2/T3), but label them in the UI and in notes.
4. Report the citation share with and without them.

Priority order: Hoboken ban + JC ban (T2/T3) → Hoboken/Newark rent control → IP 25-21 (T5 record) → SD §98.1103 (adoption evidence).

---

## 8. Traps checklist (test every one)

- [ ] Postal city ≠ legal city (Boston neighborhoods; "Los Angeles" mail in unincorporated county; San Ysidro ∈ San Diego).
- [ ] Year built ≠ certificate of occupancy: a row in the cutoff year → `unknown` (LA 1978 → A0107, A0432).
- [ ] AB 1482's 15-year window is computed from as_of. At 2026-10-01: built ≥ 2012 exempt, 2011 `unknown`, ≤ 2010 covered.
- [ ] Missing facts → `unknown`, never silent omission (SD/Berkeley year; Berkeley/Boston units from use codes).
- [ ] No owner data → owner-type tests `unknown`, unless unit counts rule them out (CA small-landlord deposit exception impossible above 4 units; NJ owner-occupied ≤ 2-unit exemptions impossible for class 4C).
- [ ] Not law:
  - D039 is a 2024 LA council motion → LA has **no** algorithmic ban.
  - D076 is April 2025 pre-adoption material. The San Diego ban was adopted ~June 2025 and is codified as SDMC §§98.1101–98.1104 (D074 URL) → in force; effective date not in the corpus → note it.
- [ ] D011 H.3744 (193rd) is dead → `failed`, never `pending`. D045/D046 (194th) → `pending`.
- [ ] SB 763 has no corpus text. Don't fabricate a record; AB 325 anchors T1.
- [ ] FAIR effective date is resolved in code = 2027-07-01; the local bans are flagged, not superseded.
- [ ] NJ city rent control vs the 30-year new-construction window (D067): an eligible or missing year → `unknown`, never omitted.
- [ ] MA: never report a rent cap. T5 affected set is empty.
- [ ] Santa Ana rules are extracted but never appear in lookups (no addresses).
- [ ] LA RSO: D042 shows 3% for 7/1/2025–6/30/2026. The 2026–27 percentage is not in the corpus → state the corpus figure with its period and add a note.
- [ ] Boston D010 Fair Chance policy only covers DND-funded/IDP units → `unknown` (special status).
- [ ] Never use numbers from `notes/research` (e.g. AB 1482 regional caps) in outputs: they aren't corpus.

**Expected behaviors (for tests only).** Derived from the brief, README and corpus; turn them into `tests/test_golden.py`.

- **SF, 20 units, built 1962** (brief example):
  - SF ch. 37 `applies`; Civ 1947.12 `superseded`.
  - Just cause §37.9 `applies`.
  - Civ 1950.5 `applies` (small-landlord exception impossible at 20 units).
  - Civ 1950.6 `applies`.
  - §37.10C and AB 325 both `apply`.
- **LA A0001** (1927, 32 units): RSO `applies`; AB 1482 `superseded`.
- **LA A0107** (1978): RSO `unknown`; AB 1482 `unknown`.
- **Every Berkeley row:** rent control `unknown` (no year); just cause `applies` (D009: covered whether built before or after 1980); ch. 13.63 `applies` + date-conflict flag.
- **Every San Diego row:** no local rent cap; AB 1482 `unknown`; SD algorithmic ban `applies`.
- **JC / Hoboken:** local ban `applies` + FAIR conflict flag; FAIR `not_yet_effective`.
  - JC rent control (ch. 260): `applies` for known years (1870–1930), `unknown` for missing years.
  - Hoboken rent control (if its page is saved): `unknown`.
- **Newark:** no local ban; FAIR `not_yet_effective`.
- **Every MA row:** c.40P `applies`; S.2983 + H.5222 `pending`; IP 25-21 and H.3744 absent from lookups.

---

## 9. Validation (we have no score.py — build our own)

`python -m navigator validate` writes `submission/validation_report.md` and `web/data/validation.json`. The tech video shows this report.

1. Every record in `rules.json` validates against the schema (`jsonschema`).
2. Quote verification: **100%** of corpus records match their text exactly; link-only records match their saved copy.
3. Citation share: % of `applies` answers backed by a corpus-verified quote. Report it with and without the link-only lane.
4. `lookups.json` has all 500 addresses; result counts by city × category.
5. T1–T5 assertions with the exact counts in §5.
6. Invariants:
   - City rules only inside their city.
   - Pending/failed never `applies`.
   - No MA rent cap.
   - Santa Ana never in lookups.
   - `superseded` only when a rule at another level applies.
   - No empty explanations.
7. Golden cases from §8, plus the recall checklist from §7.8 (found / missing).
8. Reproducibility: `python -m navigator all` with warm caches reproduces `submission/*.json` byte-for-byte.

---

## 10. Conventions

- **Environment:** Python 3.12 via `uv`. Dependencies: `anthropic`, `pydantic>=2`, `jsonschema`, `rapidfuzz`, `requests`, `python-dateutil`, `pyyaml`, `pytest`. Tests live in `tests/`; run `pytest -q` before each commit.
- **Web:** static site in `web/` (Vite + vanilla TS or React), no backend, no API keys in the browser. It reads `web/data/*.json` and deploys to Vercel.
- **Repo layout:**
  - `starter_pack/` and `notes/` are gitignored. The pack's data licensing is TBD, and judges have the pack.
  - `cache/` and `logs/` are committed.
  - Keep junk folders out of the repo: they skew GitHub's language stats.
- **Determinism:** sort everything (rules by jurisdiction → category → citation; addresses by ID). IDs are `r-0001`… assigned after the sort. Dates are ISO strings.
- **Workflow:** small commits with a clear message; run `validate` after every phase. No big refactors.
- **Scope:** if a task balloons beyond its time box in ROADMAP.md, stop and report rather than push on.
- **Docs:** `README.md` (public: what, how to run, architecture, outputs, limitations) and `submission/METHOD.md` (one page) are written in the docs phase.

## 11. Pointers

- `ROADMAP.md`: phases, time boxes, lanes, checkpoints, cut lines, kickoff prompts.
- `starter_pack/README.md`: official participant guide. `starter_pack/*.pdf`: v5 brief.
- `notes/brief_v5.txt`, `notes/organizer_clarifications.md`.
- `notes/research/ground_truth_brief.md`: law research matrix (leads only; v4-era parts stale).
- `notes/research/cella_case_report.md`: the MA ballot case behind T5.
- `research/link_only/`: our saved research copies (not corpus).

*Not legal advice. Nothing in this repo has been reviewed by counsel.*
