# Reproducibility Package

Manuscript: **Identification Limits in Estimating the Effects of Algorithmic Surveillance on Digital Freedoms**

Package version 1.0.5 (2026-10-25), which produced the results reported in the manuscript. Archived at Zenodo: concept DOI (all versions, resolves to the latest) [10.5281/zenodo.23346779](https://doi.org/10.5281/zenodo.23346779); v1.0.4 [10.5281/zenodo.23630547](https://doi.org/10.5281/zenodo.23630547); v1.0.3 [10.5281/zenodo.23619079](https://doi.org/10.5281/zenodo.23619079); v1.0.2 [10.5281/zenodo.23539189](https://doi.org/10.5281/zenodo.23539189); v1.0.1 [10.5281/zenodo.23349640](https://doi.org/10.5281/zenodo.23349640); v1.0.0 [10.5281/zenodo.23346780](https://doi.org/10.5281/zenodo.23346780).

This repository contains everything needed to regenerate every table, figure and
number reported in the manuscript and its Supplementary Material, from the raw
source files: the treatment-dating rules, the master country table, the
estimation code, the cross-implementation checks, the country-level evidence
table, and the software environments.

## Two levels of verification

**Level 1: check the reported numbers (no external data needed, seconds).**

```bash
python -m pip install -r requirements.txt
python verify/verify_reported_results.py
```

This checks 48 values reported in the manuscript (sample sizes, cohorts, primary
estimates, overlap diagnostics, specification analysis, date shifts and
lag-informed dating, implementation comparison, operational-evidence coding) against the reference tables in
`results/`. Expected output: `All checks passed: True`.

**Level 2: regenerate everything from the raw data (about 10 minutes).**

1. Download the Digital Society Project v8 and V-Dem v16 files (licensed, not
   redistributed) and place them as described in `data_access/source_datasets.md`.
   The AIGS index and the Zotero export are included in `data/raw/`.
2. Run the pipeline and compare every regenerated table with the reference:

```bash
python scripts/run_all.py
python verify/verify_reported_results.py --results outputs/results --compare outputs/results
```

`scripts/00_verify_sources.py` (first step of `run_all.py`) stops the run if any
source file differs from the version used (SHA-256). Step 06b reproduces the
earlier software version (`differences` 0.1.2), which requires Python 3.8: set
the environment variable `PY38` to a Python 3.8 interpreter with
`requirements-py38.txt` installed. Without it, the reference cell tables of that
version are copied from `results/software/` and the run continues.

## Environments

| Environment | Python | Key packages | Used for |
|---|---|---|---|
| `requirements.txt` | 3.12.3 | differences 0.3.0, csdid 0.4.2, statsmodels 0.15.0, pandas 3.0.6 | all steps |
| `requirements-py38.txt` | 3.8.10 | differences 0.1.2, pandas 2.0.3 | step 06b only |

All resampling uses fixed seeds (20261011). Regenerated tables match the
reference tables to numerical precision (`verify/verify_reported_results.py --compare`).

## Pipeline (`scripts/`)

| Step | Script | Produces |
|---|---|---|
| 00 | `00_verify_sources.py` | SHA-256 check of the raw sources |
| 01 | `01_build_panel.py` | country-year panel (179 countries, 2000-2025); correction log of the two corrupted cells of the published index (`aigs_corrections_log.csv`) |
| 02 | `02_treatment_dating.py` | record-country attributions and the five dating rules |
| 03 | `03_master_table.py` | master country table (`tabla_maestra_v2.csv`), sample flow, rules by country, undated adopters |
| 04 | `04_primary_estimates.py` | primary estimates, full event studies, joint pre-trend tests, cohort-specific covariate windows, levels, restricted comparison |
| 05 | `05_specifications_dating.py` | 60-configuration specification analysis, date shifts of one to six years, technology-specific dating, decomposition of the earlier estimate |
| 06a-c | `06a_export_panels.py`, `06b_differences_012_py38.py`, `06c_compare_implementations.py` | cell-by-cell comparison of differences 0.1.2, differences 0.3.0, csdid 0.4.2 and a direct implementation; conditions under which doubly robust cells are missing |
| 07 | `07_overlap.py` | propensity scores, overlap and balance by cohort, support-restricted estimates |
| 08 | `08_inference_validity.py` | latent-to-ordinal scale, power and equivalence, estimator comparison, two-way fixed effects, validity checks |
| 09 | `09_evidence_table.py` | country-level evidence table (records that fix each date) |
| 10 | `10_operational_coding.py` | operational-status coding of the 102 dating records (protocol in the script header) |
| 11 | `11_operational_sensitivity.py` | estimates restricted to countries with operational evidence; deployment-year lags; lag-informed dating |
| 12 | `12_manuscript_numbers.py` | auxiliary numbers cited in the text |
| 13 | `13_figures.py` | Figures 1-7 (no value is written by hand) |

| 14 | `14_supplementary.py` | Supplementary Tables 1-9 (`Supplementary_Material.xlsx`) |
| 15 | `15_audit_manuscript_numbers.py` | consistency audit of the manuscript: every numerical table cell and 51 numerical statements of the text against the result tables (requires the manuscript `.tex`; not run by `run_all.py`) |
| 16 | `16_bootstrap_audit.py` | audit of the support-restricted bootstrap: fidelity of the published standard errors, their stability across random streams, and the cohort-stratified alternative (`results/bootstrap_auditoria.csv`) |
| 17 | `17_separation_diagnostic.py` | behaviour of an affected cohort under complete separation: logit convergence and warnings, fitted scores, normalised weights, Kish effective sample size, and a directly programmed group-time parameter (`results/diagnostico_separacion_2012.json`) |
| 18 | `18_margin_benchmarks.py` | the equivalence margins expressed against the between-country standard deviation and against the observed within-country annual changes (`results/referencia_margenes.csv`) |

Figure 1 is a schematic of the design: the script draws it from the sample-flow and specification-space counts, so every number in it is reproducible. The version printed in the manuscript, archived here as `figures/Fig1_manuscript.png`, is that schematic redrawn by the authors for legibility. It carries the same counts and adds a summary of the overlap result, so it is not pixel-identical to `figures/Fig1_design.png`; because it is drawn by hand rather than produced by the pipeline, its values are checked against the result files at each release. Figures 2 to 7 are the script output unchanged.

Code comments are in Spanish; table and figure labels are in English.

## Repository contents

- `data/raw/`: AIGS index (CC BY 4.0) and Zotero metadata export; placeholders for DSP and V-Dem.
- `data_access/`: sources, versions, checksums, licences and download instructions.
- `scripts/`: the complete pipeline; `common.py` holds the shared estimators and paths.
- `results/`: reference result tables (derived, non-raw); `results/software/` the implementation comparison.
- `figures/`: Figures 1-7 (PNG and PDF), plus `Fig1_manuscript.png`, the redrawn Figure 1 as published.
- `supplementary/`: Supplementary Material as submitted.
- `verify/`: verification script; `outputs/reproducibility_check_report.md` its last report.
- `checksums/manifest_sha256.csv`: SHA-256 of every file in the package.

## What is not included

The Digital Society Project and V-Dem files, and the analytical panel built from
them, are not redistributed; the pipeline rebuilds the panel from the files the
user downloads. The two corrupted cells of the published index file are
corrected in code (`01_build_panel.py`), and the original file is included unchanged.

## Licences

Code: MIT (`LICENSE`). Derived tables, figures and Supplementary Material: CC BY 4.0.
Third-party sources: see `LICENSE-DATA.md`.

The intermediate comparison panels (`results/software/panel_corregida.csv` and
`results/software/panel_enviada.csv`) are also excluded from the public archive;
step 06a regenerates them locally from the downloaded source data.

## Changelog

- **1.0.5** (2026-10-25): the complete pipeline was rerun from the raw sources in a clean environment built from `requirements.txt` (Python 3.12.3 with `differences` 0.3.0 and `csdid` 0.4.2, and a Python 3.8 interpreter with `differences` 0.1.2 for step 06b): nineteen steps, 32.6 minutes, no errors. The verification script passed all 54 manuscript-value checks and all 53 comparisons of regenerated tables against the archived reference, and 52 of the 53 result files were byte-reproducible. The exception is corrected here: `results/bootstrap_auditoria.csv` had retained the standard errors of the pooled bootstrap from before the v1.0.3 correction, so its `SE_publicado` column disagreed with `results/soporte_restringido.csv`; it is regenerated and the two now agree. All figures are regenerated under the declared environment, which the previously shipped ones were not. `scripts/18_margin_benchmarks.py` is restricted to the 158-country estimation sample: it had counted annual transitions over the 179-country integrated panel, reporting 3,920 where the estimation sample yields 3,476, a figure that exceeded the maximum possible for the sample described in the manuscript. The README script table is corrected (60 configurations instead of 75, Supplementary Tables 1-9 instead of 1-8, and steps 15 to 18, which were missing). No estimate, interval, test or conclusion changed.
- **1.0.4** (2026-10-24): corrects the copy of the manuscript design figure, `figures/Fig1_manuscript.png`, whose summary box still stated that standard errors within the supported region are 1.7-3.6 times larger; the cohort-stratified bootstrap introduced in 1.0.3 gives 1.4-2.7, which is what the manuscript reports. That figure is drawn by the authors rather than produced by the pipeline, so the value had not followed the recomputation. Updates the expected wordings in `scripts/15_audit_manuscript_numbers.py` so that the audit tracks the current manuscript text; run against the revised manuscript it reconciles all 460 numerical claims with the archived result files. That audit also located an error in the manuscript, which this version documents rather than changes: the last row of Table 7 carried the standard error of the pooled bootstrap, 0.236, where the stratified procedure gives 0.169, the value in `results/equivalencia_soporte_restringido.csv`. No data, code path or result changed; every result table is identical to v1.0.3.
- **1.0.3** (2026-10-23): second editorial assessment of the third review round. Corrected the bootstrap of the support-restricted subsample in `scripts/07_overlap.py`: resampling is now stratified by adoption cohort with 2,000 replications, instead of pooled resampling of the 34 treated countries with 499. The 2015 cohort retains a single treated country and was absent from 191 of the 499 pooled replications, so the aggregation ran over five cohorts instead of six and the estimand changed within the bootstrap; stratified resampling keeps all six cohorts present, and at most five of the 2,000 replications lose a cohort for want of comparison countries. The script now records requested, usable, incomplete and failed replications and the Monte Carlo error of each standard error. Consequences: equivalence within a quarter of an ordinal step holds for five of the eight outcomes instead of four, the ratio of restricted to full-sample standard errors becomes 1.44-2.67 (median 2.48) instead of 1.73-3.63 (median 2.44), four 95% intervals lie entirely within the band instead of three, and `results/equivalencia_soporte_restringido.csv`, Supplementary Table 9 and Figure 5 follow. Resampling within a cohort of one treated country generates no variation, so the uncertainty reported for that cohort comes from the comparison group alone; this is a property of the subsample and is stated in the manuscript. Added `scripts/16_bootstrap_audit.py`, which records the diagnosis that motivated the change (fidelity of the published standard errors, their stability across random streams, and the stratified alternative; `results/bootstrap_auditoria.csv`), and `scripts/17_separation_diagnostic.py`, which measures the behaviour of the 2012 cohort under complete separation, including a directly programmed group-time parameter (`results/diagnostico_separacion_2012.json`). Both are now steps of `run_all.py`. Added `scripts/18_margin_benchmarks.py`, which anchors the equivalence margins in the observed variation (`results/referencia_margenes.csv`): a quarter of an ordinal step is 0.20-0.27 of the between-country standard deviation of the indicator, and 88.7% to 94.5% of the within-country annual changes recorded over the estimation window are smaller than that margin. Corrected the internal title of Figure 5, which read "Precision depends on extrapolation beyond common support" and so asserted an attribution the comparison between the two samples cannot establish, since they differ in size, cohort composition, target population and standard-error method; it now reads "Equivalence to zero inside and outside the common-support region". Added two columns to Supplementary Table 3 recording the membership of the two subsets of 34 countries that the manuscript distinguishes, so that the reader can reproduce the overlap between them: Retained within the common support, a statistical criterion, and Documents an operating system, a documentary criterion applied per country (operational status Implemented or Retrospective). The two subsets share 15 members and 19 countries belong to each alone. The package now also ships the execution logs of the pipeline in `outputs/logs/`, so the reported software behaviour can be read without rerunning the analysis; these are the logs of the complete run from the raw sources carried out for this version on 2026-10-23. Each log is named after the analysis stage rather than the script file, a convention inherited from the earlier audit stages: `panel` is written by `01_build_panel.py`, `02_dating` by `02_treatment_dating.py`, `20a_maestra` by `03_master_table.py`, `20b_principal` by `04_primary_estimates.py`, `20c_especificaciones` by `05_specifications_dating.py`, `20d_software` by `06c_compare_implementations.py`, `20e_solapamiento` by `07_overlap.py`, `20f_inferencia` by `08_inference_validity.py`, `20g_evidencias` by `09_evidence_table.py`, `20n_operativa` by `11_operational_sensitivity.py` and `20i_cifras` by `12_manuscript_numbers.py`. Updated the reference values and added the bootstrap checks in `verify/verify_reported_results.py`.
- **1.0.2** (2026-10-21): second and third review rounds.
  *Second round.* Added the lag-informed dating analysis (deployment years stated in the sources; `results/desfase_informado.csv`) and extended the treatment-date shifts from one-three to one-six years (`results/desplazamiento_fechas.csv`), both reported in Supplementary Table 6; added the manuscript consistency audit (`scripts/15_audit_manuscript_numbers.py`) and seven verification checks.
  *Third round.* Corrected the specification space in `scripts/05_specifications_dating.py`: the levels/logarithms transformation affects only income and population, so it was duplicating the configurations of the covariate sets that contain neither. `results/multiverso_v2.csv` now holds 60 distinct configurations instead of 75, and Supplementary Table 5, Figure 1 and Figure 6 follow; the estimates themselves are unchanged, the 15 removed rows were exact duplicates. Added the equivalence tests for the support-restricted subsample in `scripts/08_inference_validity.py` (`results/equivalencia_soporte_restringido.csv`, Supplementary Table 9), reporting the estimate, bootstrap standard error, 90% and 95% intervals, outcome-specific margins and TOST p-values. Updated the reference values in `verify/verify_reported_results.py` and added four checks.
- **1.0.1** (2026-10-13): corrected the labels of three alternative dating rules in Supplementary Table 5 and in `scripts/14_supplementary.py`. The earliest-record, second-distinct-year and 25th-percentile rules use every dated record attributed to a country and do not require a surveillance tag; v1.0.0 described the 25th-percentile rule as based on qualifying records. No data, code path or result changed; all result tables are identical to v1.0.0.
- **1.0.0** (2026-10-13): first release.
