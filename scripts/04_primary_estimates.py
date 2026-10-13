# -*- coding: utf-8 -*-
"""
Etapa 20b — Estimacion principal recalculada y sus sensibilidades directas.

Especificacion principal (corregida):
  · tratamiento: primer ano documentado con etiqueta positiva (Ec. 1)
  · covariables: medias 2000-2011 (anteriores a toda cohorte), PIB y
    poblacion en logaritmos
  · estimador: regresion de resultado de Callaway-Sant'Anna, base 'varying',
    comparacion = nunca tratados documentados, panel 2000-2022
  · implementacion: differences 0.3.0, verificada celda a celda con un
    estimador programado a mano (common.manual_or)

Responde a:
  R2  Figura 4: tabla completa del estudio de eventos (todas las e), con EE,
      IC puntuales y simultaneos (Bonferroni) y numero de cohortes y paises
      que contribuyen a cada e.
  R2  contraste conjunto de tendencias previas (el `wald_pre_test` de
      differences 0.3.0 falla; se calcula con la covarianza bootstrap).
  R1  comparacion restringida (sin controles con evidencia documental) para
      los ocho resultados, no solo el principal.
  R1/R2  covariables con ventana propia de cada cohorte (2000..g-1, misma
      ventana de calendario para tratados y comparacion).
  R2  sensibilidad a la transformacion de PIB y poblacion (niveles).

Uso:  python scripts/04_primary_estimates.py
"""
import os
import numpy as np
import pandas as pd
from scipy import stats
import common as rc

L = rc.Log("20b_principal")
B = 499
Z95 = stats.norm.ppf(0.975)


def bandas(ev):
    pre, post = ev.rel < 0, ev.rel >= 0
    zpre = stats.norm.ppf(1 - 0.05 / (2 * pre.sum()))
    zpost = stats.norm.ppf(1 - 0.05 / (2 * post.sum()))
    ev["z_simult"] = np.where(pre, zpre, zpost)
    ev["lo"], ev["hi"] = ev.att - Z95 * ev.se, ev.att + Z95 * ev.se
    ev["lo_sim"] = ev.att - ev.z_simult * ev.se
    ev["hi_sim"] = ev.att + ev.z_simult * ev.se
    ev["excluye_cero_puntual"] = (ev.lo > 0) | (ev.hi < 0)
    ev["excluye_cero_simult"] = (ev.lo_sim > 0) | (ev.hi_sim < 0)
    return ev


def wald_previas(reps, ev):
    """Contraste conjunto H0: todos los coeficientes previos = 0, con la
    covarianza bootstrap de los coeficientes previos."""
    pre = [r for r in ev.rel if r < 0 and r in reps.columns]
    R = reps[pre].dropna()
    V = np.cov(R.values, rowvar=False)
    b = ev.set_index("rel").loc[pre, "att"].values
    W = float(b @ np.linalg.pinv(V) @ b)
    return W, len(pre), float(1 - stats.chi2.cdf(W, len(pre))), len(R)


def una(d, var, etiqueta_esc, xcoh=None, log_paquete=True):
    """Estima un resultado. Con xcoh se usa solo el estimador manual."""
    man = rc.manual_or(d, var, xcoh=xcoh)
    cob = rc.agregar_evento(man)[["rel", "n_cohortes", "n_paises"]]
    reps, sims = rc.bootstrap(d, var, xcoh=xcoh, B=B)
    if xcoh is None:
        cel, ev, simple, nviv, exc, ws = rc.paquete(d, var)
        dif = float(cel.merge(man, on=["cohort", "time"]).eval("att_x-att_y").abs().max())
    else:
        ev = rc.agregar_evento(man)[["rel", "att"]]
        ev["se"] = ev.rel.map(reps.std(ddof=1))
        simple = (rc.agregar_simple(man), float(np.std(sims, ddof=1)))
        nviv, exc, dif = man.cohort.nunique(), [], np.nan
    ev = bandas(ev.merge(cob, on="rel"))
    ev["se_bootstrap"] = ev.rel.map(reps.std(ddof=1))
    W, k, pW, nr = wald_previas(reps, ev)
    att, se = simple
    se_b = float(np.std(sims, ddof=1))
    # ATT global "dinamico" de did/csdid: media de los efectos por tiempo
    # relativo e>=0. Es la cifra que daba la version enviada (-0,171), pero
    # con EE = media de los EE; aqui con EE bootstrap correcto.
    post_cols = [c for c in reps.columns if c >= 0]
    dyn = float(ev[ev.rel >= 0].att.mean())
    se_dyn = float(reps[post_cols].mean(axis=1).std(ddof=1))
    fila = dict(escenario=etiqueta_esc, variable=var, etiqueta=rc.ETIQ[var],
                n_paises=d.country_text_id.nunique(),
                n_tratados=d[d.cohort.notna()].country_text_id.nunique(),
                cohortes_vivas=nviv, ATT=att, SE=se, SE_bootstrap=se_b,
                IC_inf=att - Z95 * se, IC_sup=att + Z95 * se,
                p=2 * (1 - stats.norm.cdf(abs(att / se))),
                ATT_dinamico=dyn, SE_dinamico=se_dyn,
                pre_n=int((ev.rel < 0).sum()), pre_sig_puntual=int(ev[ev.rel < 0].excluye_cero_puntual.sum()),
                pre_sig_simult=int(ev[ev.rel < 0].excluye_cero_simult.sum()),
                post_n=int((ev.rel >= 0).sum()), post_sig_puntual=int(ev[ev.rel >= 0].excluye_cero_puntual.sum()),
                post_sig_simult=int(ev[ev.rel >= 0].excluye_cero_simult.sum()),
                wald_previas=W, wald_gl=k, wald_p=pW, reps_validas=nr,
                excepciones_paquete=len(exc), dif_max_paquete_manual=dif)
    return fila, ev


def main():
    L("=== 20b — estimación principal recalculada ===")
    esc = [
        ("principal", dict(), False),
        ("sin controles marcados", dict(excl_marcados=True), False),
        ("covariables en niveles", dict(log_trans=False), False),
        ("ventana de covariables por cohorte", dict(), True),
    ]
    resumen, eventos = [], []
    for nombre, kw, por_cohorte in esc:
        d = rc.cargar(**kw)
        L("")
        L("ESCENARIO: %s | %d países (%d tratados) | covariables %s"
          % (nombre, d.country_text_id.nunique(),
             d[d.cohort.notna()].country_text_id.nunique(),
             "2000..g-1 por cohorte" if por_cohorte else "2000-%d" % d.attrs["cov_fin"]))
        xcoh = rc.xcoh_dict(d, log_trans=kw.get("log_trans", True)) if por_cohorte else None
        for var, lab in rc.INDICADORES:
            f, ev = una(d, var, nombre, xcoh)
            resumen.append(f)
            ev.insert(0, "escenario", nombre); ev.insert(1, "variable", var)
            eventos.append(ev)
            L("  %-27s ATT %+.3f (EE %.3f; boot %.3f) p=%.3f | dinámico %+.3f (%.3f) | "
              "previos sig %d/%d (simult %d) Wald p=%.3f | post sig %d/%d | cohortes %d"
              % (lab, f["ATT"], f["SE"], f["SE_bootstrap"], f["p"], f["ATT_dinamico"],
                 f["SE_dinamico"], f["pre_sig_puntual"],
                 f["pre_n"], f["pre_sig_simult"], f["wald_p"], f["post_sig_puntual"],
                 f["post_n"], f["cohortes_vivas"]))
    res = pd.DataFrame(resumen)
    evs = pd.concat(eventos, ignore_index=True)
    res.to_csv(os.path.join(rc.OUT, "resumen_escenarios.csv"), index=False)
    evs.to_csv(os.path.join(rc.OUT, "event_study_todos.csv"), index=False)

    # tabla limpia del estudio de eventos principal (material suplementario)
    p = evs[(evs.escenario == "principal") & (evs.variable == rc.PRINCIPAL)]
    p.to_csv(os.path.join(rc.OUT, "event_study_principal_filtrado.csv"), index=False)
    L("")
    L("ESTUDIO DE EVENTOS PRINCIPAL (filtrado): e = %d..%d (%d previos, %d posteriores)"
      % (p.rel.min(), p.rel.max(), (p.rel < 0).sum(), (p.rel >= 0).sum()))
    for _i, r in p.iterrows():
        L("  e=%+3d  ATT %+.3f  EE %.3f  IC [%+.3f, %+.3f]  simult [%+.3f, %+.3f]  "
          "cohortes %d  países %d %s"
          % (r.rel, r.att, r.se, r.lo, r.hi, r.lo_sim, r.hi_sim, r.n_cohortes, r.n_paises,
             "*" if r.excluye_cero_puntual else ""))
    pr = res[res.escenario == "principal"]
    L("")
    L("VERIFICACIÓN: diferencia máxima paquete vs manual en las celdas: %.2e"
      % pr.dif_max_paquete_manual.max())
    L("CORRECCIÓN MÚLTIPLE (ocho resultados, escenario principal)")
    pv = pr.p.values
    o = np.argsort(pv); m = len(pv)
    bh = np.empty(m); bh[o] = np.minimum.accumulate((pv[o] * m / np.arange(1, m + 1))[::-1])[::-1]
    for (_i, r), b in zip(pr.iterrows(), np.minimum(bh, 1)):
        L("  %-27s p=%.3f  Bonferroni=%.3f  BH=%.3f" % (r.etiqueta, r.p, min(1, r.p * m), b))
    L.cerrar()


if __name__ == "__main__":
    main()
