# Source datasets

`scripts/00_verify_sources.py` checks every file below against its SHA-256.
Place the downloaded files exactly at the paths shown (or set `REPRO_RAW` to a
folder with the same structure).

| Source | Version | File / path | SHA-256 | Licence | Included |
|---|---|---|---|---|---|
| AI & Big Data Global Surveillance Index (Feldstein) | Mendeley Data `gjhf5y4xjp`, v4 (2022 update) | `data/raw/aigs/AIGS_2022.xlsx` | `d36990124a364c49a3425a3aad8d93d667f3440286b0420d181f7d073600cdc2` | CC BY 4.0 | Yes |
| Bibliographic library of the index (Zotero group 2347403) | export of 2026-08-26 (1,320 items with metadata) | `data/raw/zotero/zotero_items.csv` | `b8960cef4653c24e545fcb5a2969bd5f650b661d0b91cd95da2b347e7ed187f8` | metadata export | Yes |
| Digital Society Project, country-year | v8 | `data/raw/dsp/DSP_CY_v8.csv` | `a931f3566a9433481fee131908f17c1789587a377a868950546227b78960afe8` | provider terms | No: https://digitalsocietyproject.org/data/ |
| V-Dem Country-Year Full+Others | v16 (March 2026) | `data/raw/vdem/V-Dem-CY-Full+Others-v16.csv` | `d65f32bacb7b358c58ca9c908424444170058fc283acb625f3a6bce74faa1994` | provider terms | No: https://v-dem.net/data/the-v-dem-dataset/ |

Notes
- Zotero library URL: https://www.zotero.org/groups/2347403/global_ai_surveillance. The
  library may have changed since the export; the analysis uses the export above.
- Only these variables are used: DSP `v2smgovsmmon`, `v2smgovfilprc`, `v2smgovdom`,
  `v2smpardom`, `v2smgovshut`, `v2smgovsm`, `v2smgovsmcenprc`, `v2smarrest` (latent
  score and the `_ord`, `_codelow`, `_codehigh`, `_sd`, `_nr` variants); V-Dem
  `v2x_polyarchy`, `v2x_libdem`, `v2x_regime`, `v2x_civlib`, `v2x_rule`, `v2svstterr`,
  `v2stfisccap`, `v2x_freexp_altinf`, `v2mecenefm`, `v2xme_altinf`, `e_gdppc`, `e_pop`,
  `e_regionpol_6C`.
