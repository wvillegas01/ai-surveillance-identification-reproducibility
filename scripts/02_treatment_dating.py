# -*- coding: utf-8 -*-
"""
Paso 02 — Datacion del tratamiento desde la biblioteca Zotero del indice
(etapas 08 y 08c del proyecto).

1. Atribuye cada registro bibliografico a paises mediante sus etiquetas
   (las etiquetas "* Tech" indican el origen del PROVEEDOR y se excluyen).
2. Calcula las reglas de datacion: year_min, year_2nd, year_3rd, year_p25,
   year_median, year_focus.
3. Calcula las reglas corregidas por contenido: year_surv_neg (excluye los
   registros etiquetados "Smart City (non-surveillance)") y year_surv_pos
   (exige una etiqueta positiva de las cuatro tecnologias del indice; regla
   principal, Ec. 1 del manuscrito).

La variable es el "primer ano documentado", no el ano de adopcion.

Salidas (outputs/dating/): atribuciones_item_pais.csv,
  fechas_documentacion.csv, fechas_corregidas.csv

Uso:  python scripts/02_treatment_dating.py
"""
import os
import numpy as np
import pandas as pd
import common as rc

YEAR_FLOOR, YEAR_CEIL = 2005, 2025
ALIAS = {"United States": "United States of America", "UAE": "United Arab Emirates",
         "Turkey": "Türkiye", "Czech Republic": "Czechia", "Bosnia": "Bosnia and Herzegovina",
         "Burma": "Burma/Myanmar", "Myanmar": "Burma/Myanmar"}
NO_VIGILANCIA = "Smart City (non-surveillance)"
L = rc.Log("02_dating")


def main():
    L("=== Paso 02 — datación del tratamiento ===")
    panel = pd.read_csv(rc.PANEL)
    paises = set(panel.country_name.unique())
    adoptantes = set(panel.loc[panel.aigs_adopter == 1, "country_name"].unique())
    z = pd.read_csv(rc.ZOTERO)
    L("zotero: %d registros | panel: %d países, %d adoptantes"
      % (len(z), len(paises), len(adoptantes)))

    def resolver(tag):
        t = tag.strip()
        if not t or t.endswith(" Tech"):
            return None
        t = ALIAS.get(t, t)
        return t if t in paises else None

    filas = []
    for _i, r in z.iterrows():
        crudo = [x.strip() for x in str(r.tags or "").split("|") if x.strip()]
        cs = sorted(set(c for c in (resolver(t) for t in crudo) if c))
        if not cs:
            continue
        y = None if pd.isna(r.year) else int(r.year)
        if y is not None and not (YEAR_FLOOR <= y <= YEAR_CEIL):
            y = None
        for c in cs:
            filas.append([r.key, c, y, len(cs)])
    at = pd.DataFrame(filas, columns=["key", "country_name", "year", "n_paises_item"])
    at.to_csv(os.path.join(rc.DATING, "atribuciones_item_pais.csv"), index=False)
    L("atribuciones registro-país: %d" % len(at))

    res = []
    for c in sorted(paises):
        g = at[at.country_name == c]
        gd = g[g.year.notna()]
        ys = sorted(gd.year.astype(int).tolist())
        uy = sorted(set(ys))
        foco = sorted(gd.loc[gd.n_paises_item <= 3, "year"].astype(int).tolist())
        res.append([c, c in adoptantes, len(g), len(gd), len(uy),
                    uy[0] if len(uy) >= 1 else np.nan, uy[1] if len(uy) >= 2 else np.nan,
                    uy[2] if len(uy) >= 3 else np.nan,
                    int(np.percentile(ys, 25)) if ys else np.nan,
                    int(np.median(ys)) if ys else np.nan, foco[0] if foco else np.nan])
    f = pd.DataFrame(res, columns=["country_name", "aigs_adopter", "n_fuentes", "n_fechadas",
                                   "n_anios_distintos", "year_min", "year_2nd", "year_3rd",
                                   "year_p25", "year_median", "year_focus"])
    f.to_csv(os.path.join(rc.DATING, "fechas_documentacion.csv"), index=False)

    a2 = at.merge(z[["key", "tags"]], on="key", how="left")
    a2["tags"] = a2.tags.fillna("")
    a2["es_no_vigilancia"] = a2.tags.str.contains(NO_VIGILANCIA, regex=False)
    a2["es_vigilancia"] = a2.tags.apply(
        lambda s: any(t.strip() in rc.TAGS_VIG for t in s.split("|")))
    d = a2[a2.year.notna()]
    filas = []
    for c, g in d.groupby("country_name"):
        neg, pos = g[~g.es_no_vigilancia], g[g.es_vigilancia]
        filas.append([c, int(g.year.min()), int(neg.year.min()) if len(neg) else np.nan,
                      int(pos.year.min()) if len(pos) else np.nan, len(g), len(neg), len(pos),
                      bool(g.sort_values("year").iloc[0].es_no_vigilancia)])
    nueva = pd.DataFrame(filas, columns=["country_name", "year_min", "year_surv_neg",
                                         "year_surv_pos", "n_fechadas", "n_no_ns",
                                         "n_vigilancia", "min_era_no_vigilancia"])
    fc = f[["country_name", "aigs_adopter", "year_p25", "year_focus"]].merge(
        nueva, on="country_name", how="left")
    fc.to_csv(os.path.join(rc.DATING, "fechas_corregidas.csv"), index=False)
    ad = fc[fc.aigs_adopter]
    for col in ["year_min", "year_surv_neg", "year_surv_pos", "year_p25"]:
        L("  %-14s adoptantes datables: %d" % (col, ad[col].notna().sum()))
    L.cerrar()


if __name__ == "__main__":
    main()
