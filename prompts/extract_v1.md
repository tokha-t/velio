PROMPT_VERSION: extract-v1

You extract housing-law rules from one supplied document chunk. Return JSON only, matching this shape:
{"rules":[{"jurisdiction":"CA or City, ST","level":"state|city","category":"one category below","title":"...","requirement":"plain-language rule","citation":"canonical legal citation","quoted_span":"20-400 characters copied verbatim from SECTION TEXT","doc_kind":"one label below","enacted_date":"YYYY-MM-DD or null","effective_date_text":"exact relative/explicit wording or null","key_value":"... or null","exemptions":["..."],"yields_to_local":false,"coverage_conditions":{"text":"...","predicates":[{"type":"vocabulary item","parameters":{}}]},"confidence":0.0}],"no_rule_reason":null}

Categories: rent_increase_limits; just_cause_eviction; security_deposits; application_screening_fees; screening_restrictions; algorithmic_rent_setting.

Document-kind labels: statute; ordinance; regulation; bill; motion; ballot_measure; agency_guidance; news.

Predicate vocabulary only: built_on_or_before; built_after; rolling_new_construction_exempt_years; min_units; max_units; owner_occupied_exempt_max_units; owner_type; special_status_exemptions; tenant_level_conditions. Put predicate details in parameters (for example date, basis, n, text).

Extract only rules stated in this text. Do not use outside knowledge. A motion, news story, navigation page, or pre-adoption material is not enacted law; return no rules when it states no operative legal requirement. Granularity is one record per jurisdiction/category/law, folding exceptions into exemptions. The quote must support the requirement and be copied verbatim, never reconstructed. Use canonical citations such as Cal. Civ. Code § 1947.12, P.L.2026, c.43, or Mass. H.5222 (194th) when the text supports them. Do not decide current status.

DOCUMENT METADATA:
{metadata}

SECTION TEXT:
{chunk}
