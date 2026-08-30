# Gamification of history education: a systematic review — data, prompts and code

Supporting materials for the systematic review *Gamification of history education: a
systematic review* (Korniienko & Semerikov), submitted to *Social Sciences & Humanities
Open*. This repository is the openly released record referred to in the paper's Data
availability statement.

The review followed PRISMA 2020. It screened **4,011 records** from Scopus, Web of Science
and Dimensions and included **74 studies** published between **2004 and 2024**.

## What is here

| Path | Contents |
|---|---|
| `prompts/` | The three verbatim LLM prompts used in the workflow: eligibility screening (Claude 3.5 Sonnet), data extraction (GPT-4o), and risk-of-bias appraisal (GPT-4o). |
| `search/` | The database search strategies, as run, with the search date. |
| `data/extractions/` | One JSON record per screened study (`study_N.json`): bibliographic data, eligibility decision, study characteristics, per-RQ extractions, and risk-of-bias judgements with supporting quotations. |
| `data/aggregated/` | Cross-study tables derived from the extractions — characteristics, risk of bias, yearly and country distributions, eligibility summary, claims catalogue. |
| `data/extraction_schema.json` | The schema the extractions conform to. |
| `analysis/` | `gen_effect_size_table.py`, which recomputes every effect size from the statistics transcribed from the primary studies, and `effect_sizes.csv`, its output. |
| `scripts/` | Aggregation and table-generation utilities used to build the manuscript's appendix tables. |
| `included/` | PDFs of the included studies. |
| `prisma/` | PRISMA 2020 checklist and flow diagram. |
| `early_sheets/` | First-pass screening spreadsheets, retained for provenance. |

## Effect sizes

`analysis/gen_effect_size_table.py` is the authority for every effect size reported in the
paper. It takes no arguments:

```bash
python3 analysis/gen_effect_size_table.py
```

Points worth knowing before reusing the numbers:

- Effect sizes were **computed by the authors** from the statistics reported in each primary
  study. No language model produced them.
- Two families are kept strictly separate and never averaged: single-group pre–post
  standardized mean change (`d_z`), and controlled between-group contrasts. Mixing them is
  what makes the literature look more encouraging than it is.
- Hedges' *g* is used rather than Cohen's *d* because the samples are small (66.1% of the
  studies reporting a sample size had *n* < 50), where *d* is upward-biased.
- 95% confidence intervals are large-sample normal-theory intervals. Three qualifications are
  flagged per row in the output: an assumed equal split where a study reported only a total
  *N*; an approximation where the effect derives from a rank-based Wilcoxon statistic; and no
  interval at all where a study reported significance without the statistics needed to
  standardize an effect.
- Intervals express **sampling error only**. They do not express risk of bias, which is the
  dominant source of uncertainty here: 83.8% of the included studies are at high risk of bias.

## Human verification

The workflow was LLM-assisted, not automated. Models produced first-pass screening decisions
and structured extractions; every output was checked by a researcher against the source
article, eligibility decisions were checked by two researchers, and disagreements were
resolved by full-text adjudication. Decoding temperature and system prompts were not recorded
separately at the time, which limits exact computational reproducibility; the prompts, the
per-record outputs, and the analysis code are released here so that the procedure can be
audited and repeated.

## Citation

Korniienko, S. S., & Semerikov, S. O. Gamification of history education: a systematic review.
*Social Sciences & Humanities Open* (under review).
