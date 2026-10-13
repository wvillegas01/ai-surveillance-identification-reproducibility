# Reproducibility Package

Manuscript: **Identification Limits in Estimating the Effects of Algorithmic Surveillance on Digital Freedoms**

Package version 1.0.0 (2026-10-13). Archived release: [10.5281/zenodo.23346780](https://doi.org/10.5281/zenodo.23346780).

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

This checks 41 values reported in the manuscript (sample sizes, cohorts, primary
estimates, overlap diagnostics, specification analysis, implementation
comparison, operational-evidence coding) against the reference tables in
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
| 05 | `05_specifications_dating.py` | 75-configuration specification analysis, date shifts, technology-specific dating, decomposition of the earlier estimate |
| 06a-c | `06a_export_panels.py`, `06b_differences_012_py38.py`, `06c_compare_implementations.py` | cell-by-cell comparison of differences 0.1.2, differences 0.3.0, csdid 0.4.2 and a direct implementation; conditions under which doubly robust cells are missing |
| 07 | `07_overlap.py` | propensity scores, overlap and balance by cohort, support-restricted estimates |
| 08 | `08_inference_validity.py` | latent-to-ordinal scale, power and equivalence, estimator comparison, two-way fixed effects, validity checks |
| 09 | `09_evidence_table.py` | country-level evidence table (records that fix each date) |
| 10 | `10_operational_coding.py` | operational-status coding of the 102 dating records (protocol in the script header) |
| 11 | `11_operational_sensitivity.py` | estimates restricted to countries with operational evidence; deployment-year lags |
| 12 | `12_manuscript_numbers.py` | auxiliary numbers cited in the text |
| 13 | `13_figures.py` | Figures 1-7 (no value is written by hand) |
| 14 | `14_supplementary.py` | Supplementary Tables 1-8 (`Supplementary_Material.xlsx`) |

Code comments are in Spanish; table and figure labels are in English.

## Repository contents

- `data/raw/`: AIGS index (CC BY 4.0) and Zotero metadata export; placeholders for DSP and V-Dem.
- `data_access/`: sources, versions, checksums, licences and download instructions.
- `scripts/`: the complete pipeline; `common.py` holds the shared estimators and paths.
- `results/`: reference result tables (derived, non-raw); `results/software/` the implementation comparison.
- `figures/`: Figures 1-7 (PNG and PDF).
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
