# -*- coding: utf-8 -*-
"""
Etapa 20f — Escala, potencia, estimadores, TWFE y comprobaciones de validez,
recalculados con la especificacion corregida.

Responde a:
  R1  derivacion explicita de la conversion de la escala latente a la
      ordinal (antes 1,229 fijado a mano, sin derivacion en el codigo).
  R1/R2  potencia, efecto minimo detectable y equivalencia por resultado,
      con el paso ordinal propio de cada indicador.
  Interno: la tabla TWFE de la version enviada comparaba con un «EE» que era
      la media de los EE por periodo; aqui con el EE del agregado.
  Fig. 3 / tabla de especificaciones: cohortes que sobreviven por estimador
      (regresion, doblemente robusto, IPW estandarizado) y covariables.
  Fig. 7: placebos de medicion (_sd, _nr), estratificacion por libertad de
      prensa previa, placebo regional; deteccion en el tratamiento (logit).
  Tabla 1: descriptivos de los resultados en la muestra de estimacion.

Uso:  python scripts/08_inference_validity.py
"""
import os, warnings
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from scipy import stats
import common as rc

L = rc.Log("20f_inferencia")
Z = stats.norm.ppf(0.975)
ZB = stats.norm.ppf(0.8)


def simple(d, var, covs=rc.COV5, est="reg"):
    cel, ev, (att, se), nviv, exc, _w = rc.paquete(d, var, covs=covs, est=est)
    return att, se, nviv, ev


def main():
    L("=== 20f — escala, potencia, estimadores, TWFE y validez ===")
    d = rc.cargar()
    res = pd.read_csv(os.path.join(rc.OUT, "resumen_escenarios.csv"))
    pr = res[res.escenario == "principal"].set_index("variable")

    # ------------------------------------------------ 1. escala
    L("")
    L("1. CONVERSIÓN LATENTE -> ORDINAL (muestra de estimación, 2000-2022)")
    L("   el DSP publica la estimación latente del modelo de medición y su")
    L("   versión ordinal (_ord, escala 0-4 del codebook). Paso = distancia media")
    L("   entre las medias latentes de categorías ordinales contiguas")
    esc = []
    for var, lab in rc.INDICADORES:
        o = d[var + "_ord"].round()
        g = d.groupby(o)[var].agg(["mean", "min", "max", "count"])
        paso = float((g["mean"].iloc[-1] - g["mean"].iloc[0]) / (len(g) - 1))
        umb = [(g["max"].iloc[k] + g["min"].iloc[k + 1]) / 2 for k in range(len(g) - 1)]
        ancho = float((umb[-1] - umb[0]) / (len(umb) - 1))
        pend = float(np.polyfit(d[var + "_ord"], d[var], 1)[0])
        sd_pais = float(d.groupby("country_text_id")[var].mean().std(ddof=1))
        solap = int(sum(g["max"].iloc[k] > g["min"].iloc[k + 1] for k in range(len(g) - 1)))
        esc.append(dict(variable=var, etiqueta=lab, paso_medias=paso, ancho_umbrales=ancho,
                        pendiente_ols=pend, sd_entre_paises=sd_pais,
                        categorias_solapadas=solap,
                        media=float(d[var].mean()), sd=float(d[var].std(ddof=1)),
                        **{"media_cat%d" % int(k): float(v) for k, v in g["mean"].items()}))
        L("  %-27s paso %.3f | ancho entre umbrales %.3f | pendiente %.3f | "
          "sd entre países %.3f | categorías solapadas %d"
          % (lab, paso, ancho, pend, sd_pais, solap))
    esc = pd.DataFrame(esc).set_index("variable")
    esc.to_csv(os.path.join(rc.OUT, "escala_latente_ordinal.csv"))

    # ------------------------------------------------ 2. potencia
    L("")
    L("2. POTENCIA Y EQUIVALENCIA (ATT agregado, EE analítico)")
    pot = []
    for var, lab in rc.INDICADORES:
        att, se = pr.loc[var, "ATT"], pr.loc[var, "SE"]
        paso = esc.loc[var, "paso_medias"]
        mde = (Z + ZB) * se
        f = dict(variable=var, etiqueta=lab, ATT=att, SE=se, IC_inf=att - Z * se,
                 IC_sup=att + Z * se, MDE_80=mde, paso=paso, MDE_pasos=mde / paso,
                 MDE_sd_paises=mde / esc.loc[var, "sd_entre_paises"])
        for nom, u in [("cuarto_paso", paso / 4), ("quinto_paso", paso / 5),
                       ("decima_sd", esc.loc[var, "sd_entre_paises"] / 10)]:
            p = max(1 - stats.norm.cdf((att + u) / se), stats.norm.cdf((att - u) / se))
            f["umbral_" + nom] = u; f["TOST_p_" + nom] = p
        pot.append(f)
        L("  %-27s ATT %+.3f [%+.3f, %+.3f] | MDE %.3f = %.2f pasos | TOST ±¼ paso p=%.3f"
          % (lab, att, att - Z * se, att + Z * se, mde, mde / paso, f["TOST_p_cuarto_paso"]))
    pot = pd.DataFrame(pot)
    pot.to_csv(os.path.join(rc.OUT, "potencia_equivalencia_v2.csv"), index=False)
    L("  MDE mediano %.3f = %.2f pasos ordinales"
      % (pot.MDE_80.median(), pot.MDE_pasos.median()))
    for nom in ["cuarto_paso", "quinto_paso", "decima_sd"]:
        L("  equivalentes a cero dentro de ±%s: %d de 8"
          % (nom.replace("_", " "), (pot["TOST_p_" + nom] < .05).sum()))

    # ------------------------------------------------ 3. estimadores
    L("")
    L("3. ESTIMADOR × COVARIABLES (filtrado): cohortes con celdas y estimación")
    grid = []
    for est in ["reg", "dr", "std_ipw"]:
        for cl, cv in [("sin covariables", []), ("dos covariables", rc.COV2),
                       ("cinco covariables", rc.COV5)]:
            if not cv and est != "reg":
                continue   # sin covariables los tres estimadores coinciden
            cel, ev, (att, se), nviv, exc, _w = rc.paquete(d, rc.PRINCIPAL, covs=cv, est=est)
            vivas = sorted(cel[cel.att.notna()].cohort.astype(int).unique())
            ntr = int(d[d.cohort.isin(vivas)].country_text_id.nunique())
            grid.append(dict(estimador=est, covariables=cl, cohortes_vivas=len(vivas),
                             cohortes=" ".join(map(str, vivas)), tratados_representados=ntr,
                             ATT=att, SE=se,
                             ATT_dinamico=float(ev[ev.rel >= 0].att.mean())))
            L("  %-8s %-17s cohortes %d (%s) | tratados representados %2d | ATT %+.3f (%.3f)"
              % (est, cl, len(vivas), ",".join(str(v)[2:] for v in vivas), ntr, att, se))
    pd.DataFrame(grid).to_csv(os.path.join(rc.OUT, "estimador_covariables.csv"), index=False)

    # ------------------------------------------------ 4. TWFE
    L("")
    L("4. TWFE ESTÁTICO frente a escalonado (mismo panel, 2000-2022)")
    tw = []
    dd = d.copy()
    dd["D"] = ((dd.cohort.notna()) & (dd.year >= dd.cohort)).astype(int)
    for var, lab in rc.INDICADORES:
        m = smf.ols("%s ~ D + C(country_text_id) + C(year)" % var, data=dd).fit(
            cov_type="cluster", cov_kwds={"groups": dd.country_text_id})
        b, s = m.params["D"], m.bse["D"]
        tw.append(dict(variable=var, etiqueta=lab, TWFE=b, TWFE_SE=s,
                       CS_simple=pr.loc[var, "ATT"], CS_simple_SE=pr.loc[var, "SE"],
                       CS_dinamico=pr.loc[var, "ATT_dinamico"],
                       CS_dinamico_SE=pr.loc[var, "SE_dinamico"],
                       ratio_EE_simple=pr.loc[var, "SE"] / s,
                       ratio_EE_dinamico=pr.loc[var, "SE_dinamico"] / s))
        L("  %-27s TWFE %+.3f (%.3f) | CS simple %+.3f (%.3f) ×%.1f | CS dinámico %+.3f (%.3f) ×%.1f"
          % (lab, b, s, tw[-1]["CS_simple"], tw[-1]["CS_simple_SE"], tw[-1]["ratio_EE_simple"],
             tw[-1]["CS_dinamico"], tw[-1]["CS_dinamico_SE"], tw[-1]["ratio_EE_dinamico"]))
    tw = pd.DataFrame(tw)
    tw.to_csv(os.path.join(rc.OUT, "twfe_vs_escalonado.csv"), index=False)
    L("  TWFE negativos %d/8, con IC que excluye cero %d/8"
      % ((tw.TWFE < 0).sum(), (abs(tw.TWFE / tw.TWFE_SE) > Z).sum()))
    L("  cociente de EE mediano: simple %.2f | dinámico %.2f (versión enviada: 4-6, con "
      "EE = media de EE)" % (tw.ratio_EE_simple.median(), tw.ratio_EE_dinamico.median()))

    # ------------------------------------------------ 5. validez
    L("")
    L("5. COMPROBACIONES DE VALIDEZ (filtrado, especificación principal)")
    val = []
    m = rc.maestra()
    p = rc.panel_bruto()
    Xp = rc.covariables(p, d.attrs["cov_fin"], vars_=rc.BASE_VARS + ["v2x_freexp_altinf"])
    pais = m[m.elegible].merge(Xp, left_on="country_text_id", right_index=True)
    pais = pais[pais.rol.isin(["tratado_datado", "control_limpio", "control_marcado"])]
    pais["tr"] = (pais.rol == "tratado_datado").astype(int)
    f0 = smf.logit("tr ~ x_v2x_freexp_altinf", data=pais).fit(disp=0)
    f1 = smf.logit("tr ~ x_v2x_freexp_altinf + " + " + ".join(rc.COV5), data=pais).fit(disp=0)
    for nom, f in [("logit prensa sin controles", f0), ("logit prensa con controles", f1)]:
        val.append(dict(contraste=nom, estimacion=f.params["x_v2x_freexp_altinf"],
                        SE=f.bse["x_v2x_freexp_altinf"], p=f.pvalues["x_v2x_freexp_altinf"]))
        L("  %-36s coef %+.3f (EE %.3f) p=%.3f" % (nom, val[-1]["estimacion"], val[-1]["SE"],
                                                   val[-1]["p"]))
    dpr = d.merge(Xp[["x_v2x_freexp_altinf"]], left_on="country_text_id", right_index=True)
    med = pais[pais.tr == 1].x_v2x_freexp_altinf.median()
    for nom, sel in [("prensa libre (> mediana de tratados)", dpr.x_v2x_freexp_altinf > med),
                     ("prensa restringida (<= mediana)", dpr.x_v2x_freexp_altinf <= med)]:
        sub = dpr[dpr.cohort.isna() | sel]
        att, se, nviv, _e = simple(sub, rc.PRINCIPAL)
        val.append(dict(contraste=nom, estimacion=att, SE=se,
                        p=2 * (1 - stats.norm.cdf(abs(att / se))),
                        n_tratados=sub[sub.cohort.notna()].country_text_id.nunique(),
                        cohortes=nviv))
        L("  %-36s ATT %+.3f (EE %.3f) p=%.3f | tratados %d, cohortes %d"
          % (nom, att, se, val[-1]["p"], val[-1]["n_tratados"], nviv))
    for suf, nom in [("", "resultado sustantivo"), ("_sd", "dispersión entre codificadores"),
                     ("_nr", "número de codificadores")]:
        att, se, nviv, _e = simple(d, rc.PRINCIPAL + suf)
        val.append(dict(contraste=nom, estimacion=att, SE=se,
                        p=2 * (1 - stats.norm.cdf(abs(att / se)))))
        L("  %-36s ATT %+.3f (EE %.3f) p=%.3f" % (nom, att, se, val[-1]["p"]))
    # placebo regional
    reg = pais.groupby("region").apply(lambda s: (s.aigs_adopter == 1).mean(),
                                       include_groups=False)
    alta = reg[reg >= reg.median()].index
    nt = d[d.cohort.isna()].copy()
    ids_alta = pais[(pais.tr == 0) & pais.region.isin(alta)].country_text_id
    g_med = float(d.loc[d.cohort.notna(), "cohort"].median())
    nt["cohort"] = np.where(nt.country_text_id.isin(ids_alta), g_med, np.nan)
    att, se, nviv, _e = simple(nt, rc.PRINCIPAL)
    val.append(dict(contraste="placebo regional (no tratados de regiones de alta adopción)",
                    estimacion=att, SE=se, p=2 * (1 - stats.norm.cdf(abs(att / se))),
                    n_tratados=int(nt.country_text_id[nt.cohort.notna()].nunique())))
    L("  %-36s ATT %+.3f (EE %.3f) p=%.3f | pseudo-tratados %d, cohorte %d"
      % ("placebo regional", att, se, val[-1]["p"], val[-1]["n_tratados"], g_med))
    pd.DataFrame(val).to_csv(os.path.join(rc.OUT, "validez_v2.csv"), index=False)

    # ------------------------------------------------ 7. equivalencia en la
    #    submuestra con soporte comun (respuesta al punto 1 del editor)
    L("")
    L("7. EQUIVALENCIA EN LA SUBMUESTRA CON SOPORTE COMUN")
    rest = pd.read_csv(os.path.join(rc.OUT, "soporte_restringido.csv"))
    marg = [("cuarto_paso", "umbral_cuarto_paso"),
            ("quinto_paso", "umbral_quinto_paso"),
            ("decima_sd", "umbral_decima_sd")]
    eq = rest.merge(pot[["variable", "paso"] + [c for _, c in marg] + ["SE"]],
                    on="variable", suffixes=("", "_completa"))
    for clave, col in marg:
        eq["TOSTp_" + clave] = 1.0 - stats.norm.cdf(
            (eq[col] - eq.ATT.abs()) / eq.SE)
        eq["equiv_" + clave] = eq["TOSTp_" + clave] < 0.05
    z90 = stats.norm.ppf(0.95)
    eq["IC90_inf"] = eq.ATT - z90 * eq.SE
    eq["IC90_sup"] = eq.ATT + z90 * eq.SE
    eq["IC95_dentro_cuarto"] = ((eq.IC_inf > -eq.umbral_cuarto_paso) &
                                (eq.IC_sup < eq.umbral_cuarto_paso))
    eq["ratio_EE"] = eq.SE / eq.SE_completa
    orden = ["variable", "etiqueta", "n_tratados", "n_cohortes", "ATT", "SE",
             "IC90_inf", "IC90_sup", "IC_inf", "IC_sup", "SE_completa",
             "ratio_EE", "paso"]
    for clave, col in marg:
        orden += [col, "TOSTp_" + clave, "equiv_" + clave]
    orden += ["IC95_dentro_cuarto"]
    eq = eq[[c for c in orden if c in eq.columns]]
    eq.to_csv(os.path.join(rc.OUT, "equivalencia_soporte_restringido.csv"),
              index=False)
    for clave, _ in marg:
        L("  equivalencia dentro de %-14s %d de 8"
          % (clave, int(eq["equiv_" + clave].sum())))
    L("  IC 95%% entero dentro de 1/4 de escalon: %d de 8"
      % int(eq.IC95_dentro_cuarto.sum()))
    L("  cociente EE restringida/completa: min %.2f max %.2f mediana %.2f"
      % (eq.ratio_EE.min(), eq.ratio_EE.max(), eq.ratio_EE.median()))

    # ------------------------------------------------ 6. descriptivos
    L("")
    L("6. DESCRIPTIVOS DE LOS RESULTADOS (muestra de estimación, 2000-2022)")
    for var, lab in rc.INDICADORES:
        L("  %-27s media %+.2f  dt %.2f" % (lab, esc.loc[var, "media"], esc.loc[var, "sd"]))
    L.cerrar()


if __name__ == "__main__":
    main()
