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
