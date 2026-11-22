# Gamification of history education: a systematic review — data, prompts and code

Supporting materials for the systematic review *Gamification of history education: a
systematic review* (Korniienko & Semerikov), submitted to *Social Sciences & Humanities
Open*. This repository is the openly released record referred to in the paper's Data
availability statement.

The review followed PRISMA 2020. It identified **3,996 records** from Scopus (119), Web of Science (78)
and Dimensions (3,799) and included **74 reports of 73 studies** (one experiment is reported
twice) published between **2004 and 2024**.

## What is here

| Path | Contents |
|---|---|
| `prompts/` | The three verbatim LLM prompts used in the workflow: eligibility screening (Claude 3.5 Sonnet), data extraction (GPT-4o), and risk-of-bias appraisal (GPT-4o). |
| `search/` | The database search strategies, as run, with the search date. |
| `data/extractions/` | One JSON record per screened study (`study_N.json`): bibliographic data, eligibility decision, study characteristics, per-RQ extractions, and risk-of-bias judgements with supporting quotations. |
| `data/aggregated/` | Cross-study tables derived from the extractions — characteristics, risk of bias, yearly and country distributions, eligibility summary, claims catalogue. |
| `data/extraction_schema.json` | The schema the extractions conform to. |
| `analysis/` | The generators behind every quantitative table in the article: `gen_effect_size_table.py` (effect sizes, forest plot), `gen_rob.py` (risk-of-bias ratings), `gen_evidence_map.py` (design classification and evidence map), and `effect_sizes.csv`. Running them writes the LaTeX blocks to `tables/`, `figures/` and `numbers.tex` (not committed). Committed copies of the data outputs are in `analysis/`: `effect_sizes.csv`, `rob_rederived.csv`, `rob_report.md`, `design_family.csv`, `evidence_map.csv`. |
| `data/aggregated/provenance.csv` | Database from which each included report was retrieved (rebuilds the article's Table 2). |
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
- Paired rank statistics are put on the d_z metric of the paired *t* rows (d_z ≈ |Z|/√n), and
  flagged as approximate.
- 95% confidence intervals are large-sample normal-theory intervals. Three qualifications are
  flagged per row in the output: an assumed equal split where a study reported only a total
  *N*; an approximation where the effect derives from a rank-based Wilcoxon statistic; and no
  interval at all where a study reported significance without the statistics needed to
  standardize an effect.
- Intervals express **sampling error only**. They do not express risk of bias, which is the
  dominant source of uncertainty here: every included study is rated at high risk of bias.

## Risk of bias

`analysis/gen_rob.py` produces every risk-of-bias rating in the article mechanically from the
**verified** signalling-question answers in `data/extractions/study_N.json`, using the rule stated
in the article's Methods:

- **domain:** low if both answers are "yes", high if either is "no", unclear otherwise;
- **overall:** low only if all three domains are low.

Under that rule all 74 reports are rated high overall. 67 have at least one domain judged high,
and 7 are high only through unclear reporting (`analysis/rob_rederived.csv`, `analysis/rob_report.md`).
GPT-4o's original 2024 drafts are in `early_sheets/Strw103.xlsx` (sheet "Risk of bias"), aligned to
the studies by title. The script reports their agreement with the verified answers: 38–59% per
question, Cohen's kappa 0.01–0.35.

The holistic `risk_of_bias.overall` field in the study files ("High/Moderate/Unclear/Low"), and the
risk-of-bias and control-group counts in `data/aggregated/summary_stats.txt` and
`aggregate_stats_verified.json`, are **superseded**. They were used in earlier versions of the
article and do not follow the stated rule.

## Data passes

1. **2024.** Screening with Claude 3.5 Sonnet, checked by two researchers. Extraction and
   risk-of-bias drafts with GPT-4o, each verified by a researcher.
2. **February 2026.** Structured, schema-checked re-extraction of the verified data with Claude
   Opus 4.6 (Claude Code), every record checked by a researcher. This pass produced
   `data/extractions/`.
3. **Revision-time reliability check.** Gemini 3 Pro, GPT-4 and Grok 4.1 re-extracted all 80
   full texts; their outputs are in `early_sheets/AMX-13.xlsx`.

## Corrections made in the third revision

Every effect size was re-checked against its primary article; `analysis/gen_effect_size_table.py`
documents each change in its header. The main corrections:

- Paired Wilcoxon signed-rank statistics are converted as d_z ≈ |Z|/√n (studies 1, 39, 63).
- Study 66 measures engagement, not knowledge.
- Studies 71 and 24 are not estimable.
- Study 52 is the same experiment as 67.
- The forest-plot cap uses a single threshold.

Medians: pre–post 1.07 (n = 10); controlled 0.39 (n = 3).

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
