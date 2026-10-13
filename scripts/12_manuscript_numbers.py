# -*- coding: utf-8 -*-
"""
Etapa 20i — Cifras auxiliares para el manuscrito revisado.

Todas las cifras que el texto cita y que no estan ya en los CSV de 20a-20f:
  · balance agrupado tratados vs comparacion (ventana 2000-2011, log)
  · correlaciones entre los ocho indicadores y primer componente principal
  · concordancia entre reglas de datacion y artefacto de volumen documental
  · resumen de tendencias previas por resultado
  · cobertura posterior por horizonte
  · apendice: ATT por cohorte bajo cuatro estimadores y condiciones del logit

Salidas: cifras_manuscrito.csv (clave, valor), balance_agrupado.csv,
         apendice_cohortes.csv

Uso:  python scripts/12_manuscript_numbers.py
"""
import os
import numpy as np
import pandas as pd
from scipy import stats
import common as rc

L = rc.Log("20i_cifras")
C = {}


def main():
    L("=== 20i — cifras del manuscrito ===")
    d = rc.cargar()
    m = rc.maestra()
    p = rc.panel_bruto()

    # ---- balance agrupado
    X = rc.covariables(p, d.attrs["cov_fin"], log_trans=True,
                       vars_=rc.BASE_VARS + rc.DIAG_VARS)
    Xn = rc.covariables(p, d.attrs["cov_fin"], log_trans=False, vars_=["e_gdppc", "e_pop"])
    coh = d.groupby("country_text_id").cohort.first()
    tr, ct = coh[coh.notna()].index, coh[coh.isna()].index
    filas = []
    for c in X.columns:
        filas.append(dict(covariable=c.replace("x_", ""), tratados=X.loc[tr, c].mean(),
                          comparacion=X.loc[ct, c].mean(),
                          smd=rc.smd(X.loc[tr, c], X.loc[ct, c])))
    for c in Xn.columns:
        filas.append(dict(covariable=c.replace("x_", "") + "_niveles",
                          tratados=Xn.loc[tr, c].mean(), comparacion=Xn.loc[ct, c].mean(),
                          smd=rc.smd(Xn.loc[tr, c], Xn.loc[ct, c])))
    bal = pd.DataFrame(filas)
    bal.to_csv(os.path.join(rc.OUT, "balance_agrupado.csv"), index=False)
    L("BALANCE AGRUPADO (2000-%d)" % d.attrs["cov_fin"])
    for _i, r in bal.iterrows():
        L("  %-22s tratados %9.3f | comparación %9.3f | SMD %+.3f"
          % (r.covariable, r.tratados, r.comparacion, r.smd))
    b8 = bal[~bal.covariable.str.endswith("_niveles")]
    C["balance_n_sobre_025"] = int((b8.smd.abs() > .25).sum())
    C["balance_n_positivos"] = int((b8.smd > 0).sum())

    # ---- correlaciones entre indicadores
    Y = d[[v for v, _l in rc.INDICADORES]]
    R = Y.corr().values
    off = R[np.triu_indices(8, 1)]
    ev = np.linalg.eigvalsh(R)[::-1]
    C.update(corr_min=off.min(), corr_max=off.max(), corr_media=off.mean(),
             pc1_varianza=ev[0] / ev.sum())
    L("CORRELACIONES: %.2f a %.2f, media %.2f; PC1 %.0f%%"
      % (off.min(), off.max(), off.mean(), 100 * ev[0] / ev.sum()))

    # ---- datación
    ad = m[m.elegible & (m.aigs_adopter == 1)]
    a = ad.dropna(subset=["year_surv_pos", "year_p25"])
    C["dif_media_p25_principal"] = float((a.year_p25 - a.year_surv_pos).abs().mean())
    a2 = ad.dropna(subset=["year_surv_pos", "year_surv_neg"])
    C["rho_pos_neg"] = float(stats.spearmanr(a2.year_surv_pos, a2.year_surv_neg)[0])
    a3 = ad.dropna(subset=["year_surv_pos", "year_min"])
    dif = a3.year_surv_pos - a3.year_min
    C.update(n_fecha_distinta_min=int((dif != 0).sum()), dif_max_min=float(dif.max()),
             dif_media_min=float(dif[dif != 0].mean()))
    a4 = ad.dropna(subset=["year_surv_pos", "n_vigilancia"])
    C["rho_volumen_principal"] = float(stats.spearmanr(a4.year_surv_pos, a4.n_vigilancia)[0])
    C["p_volumen_principal"] = float(stats.spearmanr(a4.year_surv_pos, a4.n_vigilancia)[1])
    for r in rc.REGLAS:
        C["n_datables_" + r] = int(ad[r].notna().sum())
    L("DATACIÓN: |p25 - principal| medio %.2f años; rho(pos, neg) %.2f; fecha distinta de "
      "year_min en %d países (máx +%d, media +%.1f); rho(año, nº registros) %.2f (p=%.3f)"
      % (C["dif_media_p25_principal"], C["rho_pos_neg"], C["n_fecha_distinta_min"],
         C["dif_max_min"], C["dif_media_min"], C["rho_volumen_principal"],
         C["p_volumen_principal"]))

    # ---- tendencias previas y cobertura
    evs = pd.read_csv(os.path.join(rc.OUT, "event_study_todos.csv"))
    e = evs[(evs.escenario == "principal") & (evs.variable == rc.PRINCIPAL)]
    pre = e[e.rel < 0]
    C.update(pre_media=pre.att.mean(), pre_max_abs=pre.att.abs().max())
    allp = evs[(evs.escenario == "principal")]
    C["pre_sig_total"] = int(allp[allp.rel < 0].excluye_cero_puntual.sum())
    C["post_sig_total"] = int(allp[allp.rel >= 0].excluye_cero_puntual.sum())
    C["post_simult_total"] = int(allp[allp.rel >= 0].excluye_cero_simult.sum())
    C["pre_simult_total"] = int(allp[allp.rel < 0].excluye_cero_simult.sum())
    for h in (6, 8):
        C["paises_e%d" % h] = int(e.loc[e.rel == h, "n_paises"].iloc[0])
    L("PREVIOS (filtrado): media %+.3f, máx |%.3f|; en los 8 resultados: previos sig %d/144 "
      "(simult %d), posteriores sig %d/88 (simult %d); países en e=6: %d, e=8: %d"
      % (C["pre_media"], C["pre_max_abs"], C["pre_sig_total"], C["pre_simult_total"],
         C["post_sig_total"], C["post_simult_total"], C["paises_e6"], C["paises_e8"]))
    res = pd.read_csv(os.path.join(rc.OUT, "resumen_escenarios.csv"))
    pr = res[res.escenario == "principal"]
    C["wald_p_min"], C["wald_p_max"] = pr.wald_p.min(), pr.wald_p.max()
    C["p_min"], C["p_max"] = pr.p.min(), pr.p.max()

    # ---- apéndice: ATT por cohorte bajo cuatro estimadores
    L("APÉNDICE: ATT por cohorte (media de las celdas posteriores, t <= %d)" % rc.YEAR_MAIN)
    filas = []
    cond = pd.read_csv(os.path.join(rc.OUT, "software", "condiciones_dr_corregida.csv"))
    sp = pd.read_csv(os.path.join(rc.OUT, "soporte_por_especificacion.csv"))
    sp = sp[sp.especificacion == "logaritmos"].set_index("cohorte")
    cel = {}
    for est, covs in [("simple", []), ("reg", rc.COV5), ("std_ipw", rc.COV5), ("dr", rc.COV5)]:
        c_, _e, _s, _n, _x, _w = rc.paquete(d, rc.PRINCIPAL, covs=covs,
                                            est="reg" if est == "simple" else est)
        c_ = c_[c_.time >= c_.cohort]
        cel[est] = c_.groupby("cohort").att.apply(lambda s: s.mean() if s.notna().all() else np.nan)
    for _i, r in cond.iterrows():
        g = r.cohorte
        filas.append(dict(cohorte=g, n=r.n_tratados, simple=cel["simple"].get(g),
                          regresion=cel["reg"].get(g), ipw=cel["std_ipw"].get(g),
                          doble_robusto=cel["dr"].get(g), separacion=r.separacion,
                          tratados_ps_1=r.tratados_ps_igual_1,
                          fuera_soporte=r.tratados_sobre_max_comparacion,
                          ESS=sp.loc[g, "ESS"], peso_max=sp.loc[g, "peso_max"]))
        f = filas[-1]
        L("  %d n=%2d simple %+.3f | OR %+.3f | IPW %s | DR %s | sep %s | ps=1 %d | fuera %d"
          % (g, f["n"], f["simple"], f["regresion"],
             "%+.3f" % f["ipw"] if pd.notna(f["ipw"]) else "  —  ",
             "%+.3f" % f["doble_robusto"] if pd.notna(f["doble_robusto"]) else "  —  ",
             f["separacion"], f["tratados_ps_1"], f["fuera_soporte"]))
    pd.DataFrame(filas).to_csv(os.path.join(rc.OUT, "apendice_cohortes.csv"), index=False)
    pd.DataFrame(sorted(C.items()), columns=["clave", "valor"]).to_csv(
        os.path.join(rc.OUT, "cifras_manuscrito.csv"), index=False)
    L.cerrar()


if __name__ == "__main__":
    main()
