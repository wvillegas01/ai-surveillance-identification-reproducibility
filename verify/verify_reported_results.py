# -*- coding: utf-8 -*-
"""
Verification of the numbers reported in the manuscript.

Level 1 (no raw data needed):
    python verify/verify_reported_results.py
  checks the values reported in the manuscript against the result tables in
  results/ (or in the folder given with --results).

Level 2 (after running scripts/run_all.py):
    python verify/verify_reported_results.py --results outputs/results --compare outputs/results
  additionally compares every regenerated table with the reference tables in
  results/, cell by cell (numeric tolerance 1e-8 relative, 1e-10 absolute).

Writes outputs/reproducibility_check_report.{md,json}.
"""
import os, sys, json, argparse
import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REF = os.path.join(ROOT, "results")


def checks(R):
    r = lambda f: pd.read_csv(os.path.join(R, f))
    c = []

    def add(desc, actual, expected, tol=0.0005):
        if isinstance(expected, (int, float)) and not isinstance(expected, bool):
            ok = abs(float(actual) - float(expected)) <= tol
        else:
            ok = actual == expected
        c.append(dict(check=desc, actual=actual if not isinstance(actual, float) else round(actual, 4),
                      expected=expected, passed=bool(ok)))

    m = r("tabla_maestra_v2.csv")
    add("Countries in the integrated panel", len(m), 179)
    add("Dated documented adopters (treated)", int((m.rol == "tratado_datado").sum()), 81)
    add("Undated documented adopters", int((m.rol == "tratado_sin_datar").sum()), 15)
    add("Comparison countries", int(m.rol.isin(["control_limpio", "control_marcado"]).sum()), 77)
    add("Comparison countries with surveillance-related records", int((m.rol == "control_marcado").sum()), 18)
    coh = m[m.rol == "tratado_datado"].year_surv_pos.astype(int).value_counts().sort_index().to_dict()
    add("Cohort sizes 2012-2019", coh, {2012: 5, 2013: 4, 2014: 8, 2015: 7, 2016: 18, 2017: 12, 2018: 15, 2019: 12})

    s = r("resumen_escenarios.csv"); p = s[s.escenario == "principal"].set_index("variable")
    add("Internet filtering, cohort-weighted ATT", p.loc["v2smgovfilprc", "ATT"], 0.012)
    add("Internet filtering, analytical SE", p.loc["v2smgovfilprc", "SE"], 0.065)
    add("Internet filtering, dynamic ATT", p.loc["v2smgovfilprc", "ATT_dinamico"], -0.001)
    add("Internet filtering, joint pre-trend Wald p", p.loc["v2smgovfilprc", "wald_p"], 0.51, 0.005)
    add("Outcomes with p < 0.05 (primary)", int((p.p < 0.05).sum()), 0)
    add("Smallest p-value across outcomes", p.p.min(), 0.165, 0.005)
    add("Arrests for online content, ATT", p.loc["v2smarrest", "ATT"], 0.099)
    add("Party disinformation, ATT", p.loc["v2smpardom", "ATT"], 0.105)
    add("Cohort-specific covariate window, filtering ATT",
        s[(s.escenario == "ventana de covariables por cohorte") & (s.variable == "v2smgovfilprc")].ATT.iloc[0], 0.010)
    add("Covariates in levels, filtering ATT",
        s[(s.escenario == "covariables en niveles") & (s.variable == "v2smgovfilprc")].ATT.iloc[0], -0.140)

    e = r("event_study_todos.csv"); e = e[e.escenario == "principal"]
    add("Pre-treatment pointwise intervals excluding zero (8 outcomes)", int(e[e.rel < 0].excluye_cero_puntual.sum()), 4)
    add("Post-treatment pointwise intervals excluding zero (8 outcomes)", int(e[e.rel >= 0].excluye_cero_puntual.sum()), 2)
    add("Simultaneous intervals excluding zero (8 outcomes)", int(e.excluye_cero_simult.sum()), 0)
    add("Event times estimated for filtering", int((e.variable == "v2smgovfilprc").sum()), 29)

    pe = r("potencia_equivalencia_v2.csv")
    add("Outcomes equivalent to zero within 1/4 ordinal step", int((pe.TOST_p_cuarto_paso < 0.05).sum()), 8)
    add("Median MDE in ordinal steps", pe.MDE_pasos.median(), 0.16, 0.01)

    sp = r("soporte_por_especificacion.csv"); lg = sp[sp.especificacion == "logaritmos"]
    add("Treated above the comparison maximum (log logit)", int(lg.sobre_max_comparacion.sum()), 47)
    add("Treated outside [0.1, 0.9] (log logit)", int(lg.fuera_crump_01_09.sum()), 33)
    add("Cohorts with complete separation", int(lg.separacion.sum()), 2)
    sr = r("soporte_restringido.csv")
    add("Treated retained within observed overlap", int(sr.n_tratados.iloc[0]), 34)

    g = r("estimador_covariables.csv").set_index(["estimador", "covariables"])
    add("Doubly robust, five covariates: cohorts with estimates", int(g.loc[("dr", "cinco covariables"), "cohortes_vivas"]), 6)
    add("Doubly robust, five covariates: ATT", g.loc[("dr", "cinco covariables"), "ATT"], -0.046)

    mv = r("multiverso_v2.csv").dropna(subset=["ATT"])
    add("Specification analysis: configurations", len(mv), 60)
    add("Specification analysis: negative estimates", int((mv.ATT < 0).sum()), 51)
    add("Specification analysis: median", mv.ATT.median(), -0.022)
    add("Specification analysis: intervals excluding zero", int(((mv.IC_inf > 0) | (mv.IC_sup < 0)).sum()), 0)

    eqr = r("equivalencia_soporte_restringido.csv")
    add("Support-restricted equivalence, quarter step", int(eqr.equiv_cuarto_paso.sum()), 5)
    add("Support-restricted equivalence, fifth step", int(eqr.equiv_quinto_paso.sum()), 3)
    add("Support-restricted equivalence, tenth SD", int(eqr.equiv_decima_sd.sum()), 0)
    add("Support-restricted SE ratio, median", eqr.ratio_EE.median(), 2.48, 0.005)

    sr = r("soporte_restringido.csv")
    add("Support-restricted bootstrap: usable replications", int(sr.replicas_usables.min()), 2000)
    add("Support-restricted bootstrap: replications losing a cohort", int(sr.replicas_incompletas.max() <= 5), 1)

    dc = r("descomposicion.csv")
    add("Earlier specification (cohort-weighted)", dc.ATT.iloc[0], -0.142)
    add("Earlier specification with logarithms", dc.ATT.iloc[2], -0.011)

    tw = r("twfe_vs_escalonado.csv").set_index("variable")
    add("TWFE filtering coefficient", tw.loc["v2smgovfilprc", "TWFE"], -0.092)
    add("TWFE negative coefficients", int((tw.TWFE < 0).sum()), 8)

    op = r("estado_operativo_por_pais.csv")
    add("Countries with operational evidence (implemented + retrospective)",
        int(op.estado_operativo.isin(["Implemented", "Retrospective"]).sum()), 34)
    so = r("sensibilidad_operativa.csv"); so = so[so.muestra.str.startswith("Operational")]
    add("Operational-evidence subset: filtering ATT", so[so.variable == "v2smgovfilprc"].ATT.iloc[0], -0.026)
    add("Operational-evidence subset: outcomes with p < 0.05", int((so.p < 0.05).sum()), 0)

    de = r("desplazamiento_fechas.csv")
    add("Treatment-date shifts estimated (years earlier)", sorted(int(k) for k in de.desplazamiento.unique() if k > 0),
        [1, 2, 3, 4, 5, 6])
    add("Date shifts of one to six years: outcomes with p < 0.05", int((de[de.desplazamiento > 0].p < 0.05).sum()), 0)
    di = r("desfase_informado.csv")
    li = di[di.escenario == "Lag-informed dates"]
    add("Lag-informed dates: treated countries", int(li.n_tratados.iloc[0]), 79)
    add("Lag-informed dates: filtering ATT", li[li.variable == "v2smgovfilprc"].ATT.iloc[0], 0.014)
    lx = di[di.escenario == "Lagged countries excluded"]
    add("Countries with stated earlier deployment excluded: treated countries", int(lx.n_tratados.iloc[0]), 75)
    add("Countries with stated earlier deployment excluded: filtering ATT", lx[lx.variable == "v2smgovfilprc"].ATT.iloc[0], 0.020)
    add("Lag-informed analyses: outcomes with p < 0.05", int((di.p < 0.05).sum()), 0)

    sw = r("software/resumen_implementaciones.csv")
    add("Max |differences 0.1.2 - 0.3.0| across cells", float(sw.max_dif_v012_v030.max()), 0.0, 1e-9)
    add("Max |differences 0.3.0 - csdid| across cells", float(sw.max_dif_v030_csdid.max()), 0.0, 1e-9)
    return c


def comparar(nuevo):
    filas = []
    for raiz, _d, fs in os.walk(REF):
        for f in fs:
            if not f.endswith(".csv"):
                continue
            rel = os.path.relpath(os.path.join(raiz, f), REF)
            pn = os.path.join(nuevo, rel)
            if not os.path.exists(pn):
                filas.append(dict(file=rel, passed=False, detail="missing in regenerated outputs")); continue
            a, b = pd.read_csv(os.path.join(REF, rel)), pd.read_csv(pn)
            if a.shape != b.shape or list(a.columns) != list(b.columns):
                filas.append(dict(file=rel, passed=False, detail="shape/columns differ %s vs %s" % (a.shape, b.shape))); continue
            ok, peor = True, 0.0
            for col in a.columns:
                x, y = a[col], b[col]
                if pd.api.types.is_numeric_dtype(x) and pd.api.types.is_numeric_dtype(y):
                    xv, yv = x.to_numpy(float), y.to_numpy(float)
                    same_nan = np.isnan(xv) == np.isnan(yv)
                    d = np.abs(np.nan_to_num(xv) - np.nan_to_num(yv))
                    lim = 1e-10 + 1e-8 * np.abs(np.nan_to_num(xv))
                    if not (same_nan.all() and (d <= lim).all()):
                        ok = False
                    peor = max(peor, float(d.max()) if len(d) else 0.0)
                elif not x.fillna("").astype(str).equals(y.fillna("").astype(str)):
                    ok = False
            filas.append(dict(file=rel, passed=ok, detail="max abs numeric difference %.2e" % peor))
    return filas


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", default=REF)
    ap.add_argument("--compare", default=None)
    a = ap.parse_args()
    c = checks(a.results)
    comp = comparar(a.compare) if a.compare else []
    ok = all(x["passed"] for x in c) and all(x["passed"] for x in comp)
    out = os.path.join(ROOT, "outputs"); os.makedirs(out, exist_ok=True)
    json.dump(dict(all_checks_passed=ok, results_folder=a.results, manuscript_checks=c,
                   regenerated_vs_reference=comp), open(os.path.join(out, "reproducibility_check_report.json"), "w"),
              indent=1, default=str)
    L = ["# Reproducibility Check Report", "", "All checks passed: `%s`" % ok, "",
         "Results folder checked: `%s`" % os.path.relpath(a.results, ROOT), "",
         "## Manuscript values (%d checks)" % len(c), ""]
    L += ["- `%s` %s: actual=%s expected=%s" % ("PASS" if x["passed"] else "FAIL", x["check"], x["actual"], x["expected"]) for x in c]
    if comp:
        L += ["", "## Regenerated tables vs reference (%d files)" % len(comp), ""]
        L += ["- `%s` %s: %s" % ("PASS" if x["passed"] else "FAIL", x["file"], x["detail"]) for x in comp]
    open(os.path.join(out, "reproducibility_check_report.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")
    print("\n".join(L[:3]))
    for x in c + comp:
        if not x["passed"]:
            print("FAIL", x)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
