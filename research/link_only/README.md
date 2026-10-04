# Link-only research copies (NOT supplied corpus)

The organizers allow independently saved link-only texts for research, if their terms allow it.
These copies do **not** count toward the citation metric (organizer clarification, Oct 4).

How to save one: open the URL from `starter_pack/corpus/links_only.csv` in your browser, select all, copy,
and paste into `research/link_only/<doc_id>.txt`. One page at a time; no scripts against code publishers.

Every file starts with this header (then a blank line, then the page text):

```
SOURCE: <exact url you opened>
RETRIEVED: 2026-10-04 HH:MM UTC
NOTE: research copy — not supplied corpus; saved manually for research under organizer guidance
```

Priority: D032–D034 (Hoboken), D035 (Jersey City ban), then D070–D072 (Newark), D059 (WBUR, IP 25-21), D074 (San Diego §98.1103).
The pipeline extracts these with `source_tier = link_only_research` and `corpus_text = false`.

## Saved 2026-10-04 (09:12–09:15 UTC)

| File | What it holds | Exact page read |
|---|---|---|
| D032.txt | Hoboken § 155-2 (rent control coverage and exemptions, incl. the post-1987 new-construction exemption that requires a notice filing) | ecode360.com/15252460 |
| D033.txt | Hoboken § 155-4 opening paragraph + § 155-5 (cap: 5% or CPI, whichever is less) | ecode360.com/15252470 |
| D034.txt | Hoboken ch. 158: § 158-1 disclosures + Art. II § 158-2 algorithmic rent fixing ban (adopted 7-9-2025, Ord. B-781) | ecode360.com/46833413 |
| D035.txt | Jersey City Ord. 25-076 amending Code § 218-12 (algorithmic rent fixing), final passage Jul 16 2025, approved Jul 17 2025. Official city PDF used instead of the news article listed for D035. | cityofjerseycity.civicweb.net/document/433505/ |

Each body was checked against the live page text (whitespace-normalized SHA-256 match).

Loader rules: doc_id = file stem; jurisdictions from `starter_pack/corpus/links_only.csv`; **source_url and retrieved_at come from this file's SOURCE/RETRIEVED header, not from links_only.csv**; corpus_text = false; source_tier = link_only_research. The NOTE line is ordinary body text.
