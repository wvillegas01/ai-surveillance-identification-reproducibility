# -*- coding: utf-8 -*-
"""
Etapa 20c — Especificaciones, incertidumbre de datacion y tecnologia.

Responde a:
  R1  desplazar hacia atras la fecha de tratamiento 1, 2 y 3 anos (retraso
      documental), en los ocho resultados. Segunda ronda: se amplia a 4, 5 y 6
      anos; con 6 la ventana de covariables queda en 2000-2005, y desplazamientos
      mayores dejarian cohortes sin periodo previo dentro del panel.
  R1  el multiverso mezclaba el fin de panel 2025 con una principal que se
      justifica cortando en 2022. Se elimina el fin 2025: mas alla del cierre
      del inventario la condicion de comparacion no es verificable, y la misma
      logica debe regir la robustez.
  R1  heterogeneidad por version del tratamiento: estimacion por familia
      tecnologica con fechas propias de cada tecnologia.
  Interno: descomposicion del cambio entre la version enviada y la corregida
      (regla de datacion, ventana de covariables, transformacion).

Salidas: multiverso_v2.csv, desplazamiento_fechas.csv, descomposicion.csv,
         por_tecnologia.csv

Uso:  python scripts/05_specifications_dating.py
"""
import os, itertools
import numpy as np
import pandas as pd
from scipy import stats
import common as rc

L = rc.Log("20c_especificaciones")
Z = stats.norm.ppf(0.975)


def fila(d, var, covs=rc.COV5):
    cel, ev, (att, se), nviv, exc, _w = rc.paquete(d, var, covs=covs)
    return dict(ATT=att, SE=se, IC_inf=att - Z * se, IC_sup=att + Z * se,
                p=2 * (1 - stats.norm.cdf(abs(att / se))), cohortes_vivas=nviv,
                n_tratados=d[d.cohort.notna()].country_text_id.nunique(),
                n_comparacion=d[d.cohort.isna()].country_text_id.nunique())


def main():
    L("=== 20c — especificaciones, datación y tecnología ===")

    # ------------------------------------------------ 1. descomposición
    L("")
    L("1. DESCOMPOSICIÓN versión enviada -> versión corregida (filtrado)")
    pasos = [
        ("enviada: year_min, cov 2000-2015, niveles",
         dict(regla="year_min", cov_fin=2015, log_trans=False)),
        ("+ ventana 2000-2011", dict(regla="year_min", cov_fin=2011, log_trans=False)),
        ("+ logaritmos", dict(regla="year_min", cov_fin=2011, log_trans=True)),
        ("+ etiqueta positiva = corregida", dict(regla="year_surv_pos", cov_fin=2011,
                                                 log_trans=True)),
        ("solo etiqueta positiva (cov 2000-2015, niveles)",
         dict(regla="year_surv_pos", cov_fin=2015, log_trans=False)),
    ]
    dec = []
    for nombre, kw in pasos:
        r = fila(rc.cargar(**kw), rc.PRINCIPAL)
        dec.append(dict(paso=nombre, **r))
        L("  %-48s ATT %+.3f (EE %.3f)  tratados %d" % (nombre, r["ATT"], r["SE"],
                                                       r["n_tratados"]))
    pd.DataFrame(dec).to_csv(os.path.join(rc.OUT, "descomposicion.csv"), index=False)

    # ------------------------------------------------ 2. desplazamiento
    L("")
    L("2. DESPLAZAMIENTO DE LA FECHA (g-k), ocho resultados")
    L("   la ventana de covariables se adelanta con la primera cohorte (2000..g0-k-1)")
    des = []
    for k in [0, 1, 2, 3, 4, 5, 6]:
        d = rc.cargar(desplazar=k)
        for var, lab in rc.INDICADORES:
            r = fila(d, var)
            des.append(dict(desplazamiento=k, cov_fin=d.attrs["cov_fin"], variable=var,
                            etiqueta=lab, **r))
        sub = pd.DataFrame(des)
        sub = sub[sub.desplazamiento == k]
        L("  k=%d (cov 2000-%d): %s" % (k, d.attrs["cov_fin"], "  ".join(
            "%s %+.3f%s" % (lab.split()[0][:6], v, "*" if p < .05 else "")
            for lab, v, p in zip(sub.etiqueta, sub.ATT, sub.p))))
    pd.DataFrame(des).to_csv(os.path.join(rc.OUT, "desplazamiento_fechas.csv"), index=False)

    # ------------------------------------------------ 3. multiverso
    L("")
    L("3. MULTIVERSO (filtrado), fin de panel 2022 en todas las configuraciones")
    covs = [("sin covariables", []), ("dos covariables", rc.COV2),
            ("cinco covariables", rc.COV5)]
    trans = [("log", True), ("niveles", False)]
    muestras = [("completa", {}), ("sin marcados", dict(excl_marcados=True)),
                ("sin China", dict(sin_paises=["CHN"]))]
    mv = []
    # la transformación log/niveles solo afecta a renta y población: si el
    # conjunto de covariables no incluye ninguna de las dos, las dos variantes
    # son la misma configuración y solo se estima una
    afectadas = set("x_" + v for v in rc.LOG_VARS)
    for regla, (cl, cv), (tl, tv), (ml, mk) in itertools.product(rc.REGLAS, covs, trans,
                                                                 muestras):
        transforma = bool(set(cv) & afectadas)
        if tl == "niveles" and not transforma:
            continue
        try:
            r = fila(rc.cargar(regla=regla, log_trans=tv, **mk), rc.PRINCIPAL, covs=cv)
        except Exception as ex:
            r = dict(ATT=np.nan, error=type(ex).__name__)
        mv.append(dict(regla_datacion=regla, covariables=cl,
                       transformacion=tl if transforma else "-", muestra=ml, fin_panel=2022, **r))
    mv = pd.DataFrame(mv)
    mv.to_csv(os.path.join(rc.OUT, "multiverso_v2.csv"), index=False)
    ok = mv.dropna(subset=["ATT"])
    L("  configuraciones: %d (estimadas %d)" % (len(mv), len(ok)))
    L("  ATT: mín %+.3f | máx %+.3f | mediana %+.3f" % (ok.ATT.min(), ok.ATT.max(),
                                                      ok.ATT.median()))
    L("  negativas: %d de %d | IC excluye cero: %d | pierden cohortes: %d"
      % ((ok.ATT < 0).sum(), len(ok), ((ok.IC_inf > 0) | (ok.IC_sup < 0)).sum(),
         (ok.cohortes_vivas < ok.groupby("regla_datacion").cohortes_vivas.transform("max")).sum()))
    for r_, g in ok.groupby("regla_datacion"):
        L("    %-14s mediana %+.3f  rango [%+.3f, %+.3f]  negativas %d/%d"
          % (r_, g.ATT.median(), g.ATT.min(), g.ATT.max(), (g.ATT < 0).sum(), len(g)))
    for t_, g in ok.groupby("transformacion"):
        L("    transf. %-7s EE mediano %.3f" % (t_, g.SE.median()))

    # ------------------------------------------------ 4. por tecnología
    L("")
    L("4. POR FAMILIA TECNOLÓGICA (fecha = primer registro con etiqueta de esa familia)")
    L("   tratados: adoptantes con esa tecnología en el índice; comparación: nunca")
    L("   tratados documentados; se excluyen los demás adoptantes")
    at = pd.read_csv(os.path.join(rc.DATING, "atribuciones_item_pais.csv"))
    zot = pd.read_csv(rc.ZOTERO)
    at = at.merge(zot[["key", "tags"]], on="key", how="left").dropna(subset=["year"])
    at = at[at.year >= 2005]
    at["fam"] = at.tags.fillna("").apply(
        lambda s: sorted({rc.TAGS_VIG[t.strip()] for t in s.split("|")
                          if t.strip() in rc.TAGS_VIG}))
    at = at.explode("fam").dropna(subset=["fam"])
    fechas = at.groupby(["country_name", "fam"]).year.min().unstack()
    m = rc.maestra()
    col_aigs = dict(safe_city="tech_safecity", facial="tech_facial",
                    smart_policing="tech_smartpolicing", sm_monitoring="tech_socialmedia")
    tec = []
    base = rc.cargar()
    for fam, col in col_aigs.items():
        tr = m[m.elegible & (m.aigs_adopter == 1) & (m[col] == 1)].copy()
        tr["g"] = tr.country_name.map(fechas[fam]) if fam in fechas else np.nan
        tr = tr.dropna(subset=["g"])
        ids_tr = dict(zip(tr.country_text_id, tr.g))
        d = base[base.cohort.isna() | base.country_text_id.isin(ids_tr)].copy()
        d["cohort"] = d.country_text_id.map(ids_tr)
        # cohortes con un solo país no permiten estimar; se agrupan al año siguiente
        if d.cohort.notna().sum() == 0:
            continue
        g0 = int(d.cohort.min())
        X = rc.covariables(rc.panel_bruto(), g0 - 1)
        d = d.drop(columns=rc.COV5).merge(X, left_on="country_text_id", right_index=True)
        for var, lab in rc.INDICADORES:
            try:
                r = fila(d, var)
            except Exception as ex:
                r = dict(ATT=np.nan, error=type(ex).__name__)
            tec.append(dict(familia=fam, n_cohortes=d.cohort.nunique(), cov_fin=g0 - 1,
                            variable=var, etiqueta=lab, **r))
        sub = pd.DataFrame(tec)
        sub = sub[sub.familia == fam]
        L("  %-15s tratados %2d, cohortes %d, cov 2000-%d | filtrado %+.3f (EE %.3f) | "
          "vigilancia RRSS %+.3f (EE %.3f)"
          % (fam, len(ids_tr), d.cohort.nunique(), g0 - 1,
             sub[sub.variable == "v2smgovfilprc"].ATT.iloc[0],
             sub[sub.variable == "v2smgovfilprc"].SE.iloc[0],
             sub[sub.variable == "v2smgovsmmon"].ATT.iloc[0],
             sub[sub.variable == "v2smgovsmmon"].SE.iloc[0]))
    pd.DataFrame(tec).to_csv(os.path.join(rc.OUT, "por_tecnologia.csv"), index=False)
    L.cerrar()


if __name__ == "__main__":
    main()
