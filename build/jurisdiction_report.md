# Jurisdiction resolution report

As of 2026-10-01. Not legal advice.

## Summary

- Address rows: **500**
- Census address matches: **485 / 500 (97.0%)**
- Place match or confident dataset fallback: **499 / 500 (99.8%)**
- Postal city differs from legal city: **38**
- No incorporated place (state-only stack): **0**
- Low-confidence dataset fallback: **1**
- Methods: `census_oneline` 485, `dataset_fallback` 15

## Postal city differs from legal city

| Address ID | Street | Postal city | Legal city | Method | Confidence |
|---|---|---|---|---|---|
| A0036 | 33 WARD ST | South Boston | Boston, MA | census_oneline | high |
| A0048 | 1619 COMMONWEALTH AV | Brighton | Boston, MA | census_oneline | high |
| A0052 | 88 Gardner ST | Allston | Boston, MA | census_oneline | high |
| A0054 | 13 Shetland ST | Roxbury | Boston, MA | census_oneline | high |
| A0065 | 63 Bailey ST | Dorchester | Boston, MA | census_oneline | high |
| A0083 | 38 KENILWORTH ST | Roxbury | Boston, MA | census_oneline | high |
| A0093 | 90 BICKFORD ST | Jamaica Plain | Boston, MA | census_oneline | high |
| A0098 | WILLOWWOOD ST | Dorchester | Boston, MA | dataset_fallback | high |
| A0118 | 18-34 KINGBIRD RD | Dorchester | Boston, MA | census_oneline | high |
| A0123 | 123 Condor ST | East Boston | Boston, MA | census_oneline | high |
| A0128 | Harvard ST | Dorchester | Boston, MA | dataset_fallback | high |
| A0134 | 101 Norfolk ST | Dorchester | Boston, MA | census_oneline | high |
| A0143 | 75 ELM HILL AV | Dorchester | Boston, MA | census_oneline | high |
| A0144 | 112-114 Amory ST | Roxbury | Boston, MA | census_oneline | high |
| A0149 | 25 Everett ST | East Boston | Boston, MA | census_oneline | high |
| A0155 | 473 Harvard ST | Dorchester | Boston, MA | census_oneline | high |
| A0169 | 115 KILSYTH RD | Brighton | Boston, MA | census_oneline | high |
| A0195 | 1850-1848 COMMONWEALTH AV | Brighton | Boston, MA | census_oneline | high |
| A0198 | 194 Havre ST | East Boston | Boston, MA | census_oneline | high |
| A0203 | 2986-2930 Washington ST | Roxbury | Boston, MA | census_oneline | high |
| A0217 | 170-172 Maverick ST | East Boston | Boston, MA | census_oneline | high |
| A0220 | 21-23 Faulkner ST | Dorchester | Boston, MA | census_oneline | high |
| A0242 | 85-87 SIERRA RD | Hyde Park | Boston, MA | census_oneline | high |
| A0245 | 30 WEST HOWELL ST M-D | Dorchester | Boston, MA | census_oneline | high |
| A0258 | 471 COLUMBIA RD | Dorchester | Boston, MA | census_oneline | high |
| A0295 | Harvard ST LOT 2A-13 | Dorchester | Boston, MA | dataset_fallback | high |
| A0310 | 53-55 Ashford ST | Allston | Boston, MA | census_oneline | high |
| A0312 | 25 ORLANDO ST | Mattapan | Boston, MA | census_oneline | high |
| A0322 | 227 CYPRESS DR | San Ysidro | San Diego, CA | census_oneline | high |
| A0332 | 26 SONOMA ST | Dorchester | Boston, MA | census_oneline | high |
| A0354 | 73 LUBEC ST | East Boston | Boston, MA | census_oneline | high |
| A0356 | 16 Brainerd RD | Allston | Boston, MA | census_oneline | high |
| A0366 | 230 Everett ST | East Boston | Boston, MA | census_oneline | high |
| A0376 | ST JAMES ST | Roxbury | Boston, MA | dataset_fallback | high |
| A0380 | GREENVILLE ST | Roxbury | Boston, MA | dataset_fallback | high |
| A0423 | 10 CAMELOT CT | Brighton | Boston, MA | census_oneline | high |
| A0463 | 4 BEECHWOOD ST | Dorchester | Boston, MA | census_oneline | high |
| A0464 | 2-98 DABNEY ST | Roxbury | Boston, MA | census_oneline | high |

## Unincorporated / state-only rows

| Address ID | Street | Postal city | County | Method |
|---|---|---|---|---|
| — | — | — | — | — |

## Low-confidence rows

| Address ID | Street | Postal city | County | Method |
|---|---|---|---|---|
| A0346 | AUBURN DR | San Diego | — | dataset_fallback |
