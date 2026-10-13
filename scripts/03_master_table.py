# -*- coding: utf-8 -*-
"""
Etapa 20a — Tabla maestra v2 (regla de etiqueta positiva) y flujo muestral.

Responde a:
  R2  ¿por que la regla «estricta» pasa de 88 a 82 paises? -> la regla
      principal pasa a ser la de la Ec. 1 (etiqueta positiva); se documenta
      que ocurre con cada pais en cada regla.
  R1  descripcion de los adoptantes sin fecha y efecto de excluirlos sobre la
      composicion del grupo tratado.
  R1/R2  ventana temporal de las covariables por cohorte.

Salidas en outputs/results/:
  tabla_maestra_v2.csv, flujo_muestral_v2.csv, reglas_por_pais.csv,
  sin_datar_descriptivo.csv, ventanas_covariables.csv

Uso:  python scripts/03_master_table.py
"""
import os, collections
import numpy as np
import pandas as pd
import common as rc

L = rc.Log("20a_maestra")


def main():
    L("=== 20a — tabla maestra v2 ===")
    p = rc.panel_bruto()
    f8 = pd.read_csv(os.path.join(rc.DATING, "fechas_documentacion.csv"))
    fc = pd.read_csv(os.path.join(rc.DATING, "fechas_corregidas.csv"))
    at = pd.read_csv(os.path.join(rc.DATING, "atribuciones_item_pais.csv"))
    zot = pd.read_csv(rc.ZOTERO)

    base = (p.groupby(["country_text_id", "country_name"])
            .agg(n_pre_years=("n_pre_years", "first"),
                 sample_main=("sample_main", "first"),
                 aigs_adopter=("aigs_adopter", "first"),
                 aigs_dose=("aigs_dose", "first"),
                 tech_safecity=("tech_safecity", "first"),
                 tech_facial=("tech_facial", "first"),
                 tech_smartpolicing=("tech_smartpolicing", "first"),
                 tech_socialmedia=("tech_socialmedia", "first"),
                 vendor_china=("vendor_china", "first"),
                 vendor_us=("vendor_us", "first"),
                 region=("e_regionpol_6C", "first"))
            .reset_index())
    base = base.merge(fc[["country_name", "year_min", "year_surv_neg", "year_surv_pos",
                          "year_p25", "n_fechadas", "n_vigilancia"]],
                      on="country_name", how="left")
    base = base.merge(f8[["country_name", "year_2nd"]], on="country_name", how="left")

    # evidencia documental de vigilancia entre los no adoptantes
    at = at.merge(zot[["key", "tags"]], on="key", how="left")
    at["tags"] = at.tags.fillna("")
    at["vig"] = at.tags.apply(lambda s: any(t.strip() in rc.TAGS_VIG for t in s.split("|")))
    ev = (at[at.vig & at.year.notna()].groupby("country_name")
          .agg(n_fuentes_vig=("key", "size"), primer_anio_vig=("year", "min")).reset_index())
    base = base.merge(ev, on="country_name", how="left")
    base["n_fuentes_vig"] = base.n_fuentes_vig.fillna(0).astype(int)
    base["control_marcado"] = (base.aigs_adopter == 0) & (base.n_fuentes_vig > 0)

    # covariables completas en la ventana mas temprana usada (2000..2008, que
    # cubre el desplazamiento de tres anos) y en la principal
    X = rc.covariables(p, 2008)
    base["cov_completas"] = base.country_text_id.map(X.notna().all(axis=1)).fillna(False)
    base["elegible"] = (base.sample_main == 1) & base.cov_completas

    def rol(r):
        if r.sample_main == 0:
            return "excluido_historial_corto"
        if not r.cov_completas:
            return "excluido_sin_covariables"
        if r.aigs_adopter == 1:
            return "tratado_datado" if pd.notna(r[rc.REGLA_PRINCIPAL]) else "tratado_sin_datar"
        return "control_marcado" if r.control_marcado else "control_limpio"

    base["rol"] = base.apply(rol, axis=1)
    base = base.sort_values(["rol", "country_name"])
    base.to_csv(os.path.join(rc.OUT, "tabla_maestra_v2.csv"), index=False)
    L("  -> tabla_maestra_v2.csv (%d países)" % len(base))

    # ---------------------------------------------------------- flujo
    fl = []

    def paso(desc, n, det=""):
        fl.append([len(fl) + 1, desc, n, det]); L("  %-58s %4d  %s" % (desc, n, det))

    L("")
    L("FLUJO MUESTRAL (regla principal: %s, panel 2000-%d)" % (rc.REGLA_PRINCIPAL,
                                                              rc.YEAR_MAIN))
    paso("Países en el panel integrado DSP x V-Dem x AIGS", len(base))
    paso("Excluidos por historial corto (<12 años previos)",
         int((base.rol == "excluido_historial_corto").sum()),
         ", ".join(base.loc[base.rol == "excluido_historial_corto", "country_name"]))
    paso("Excluidos por covariables incompletas",
         int((base.rol == "excluido_sin_covariables").sum()),
         ", ".join(base.loc[base.rol == "excluido_sin_covariables", "country_name"]))
    el = base[base.elegible]
    paso("Muestra elegible", len(el))
    paso("  adoptantes documentados (AIGS)", int((el.aigs_adopter == 1).sum()))
    paso("    con fecha (etiqueta positiva)", int((el.rol == "tratado_datado").sum()))
    paso("    sin fecha", int((el.rol == "tratado_sin_datar").sum()),
         ", ".join(el.loc[el.rol == "tratado_sin_datar", "country_name"]))
    paso("  sin capacidad documentada", int((el.aigs_adopter == 0).sum()))
    paso("    con fuentes de vigilancia fechadas (marcados)",
         int((el.rol == "control_marcado").sum()))
    paso("    sin fuentes (limpios)", int((el.rol == "control_limpio").sum()))
    paso("Muestra de estimación principal",
         int(el.rol.isin(["tratado_datado", "control_marcado", "control_limpio"]).sum()))
    pd.DataFrame(fl, columns=["paso", "descripcion", "n_paises", "detalle"]).to_csv(
        os.path.join(rc.OUT, "flujo_muestral_v2.csv"), index=False)

    tr = el[el.rol == "tratado_datado"]
    coh = collections.Counter(tr[rc.REGLA_PRINCIPAL].astype(int))
    L("")
    L("COHORTES: %s  (suma %d)" % (dict(sorted(coh.items())), sum(coh.values())))

    # ---------------------------------------------------------- reglas por país
    ad = el[el.aigs_adopter == 1].copy()
    L("")
    L("PAÍSES DATABLES POR REGLA (adoptantes elegibles = %d)" % len(ad))
    for r in rc.REGLAS:
        L("  %-14s %3d" % (r, ad[r].notna().sum()))
    perd = ad[ad.year_min.notna() & ad.year_surv_pos.isna()]
    L("  datables con year_min pero sin etiqueta positiva: %d -> %s"
      % (len(perd), ", ".join(perd.country_name)))
    L("    (sus únicos registros fechados no llevan etiqueta de ninguna de las")
    L("     cuatro tecnologías del índice: smart city sin vigilancia u otras)")
    cambia = ad.dropna(subset=["year_min", "year_surv_pos"])
    cambia = cambia[cambia.year_min != cambia.year_surv_pos]
    L("  con fecha distinta entre year_min y la regla principal: %d (media %+.2f años)"
      % (len(cambia), (cambia.year_surv_pos - cambia.year_min).mean()))
    ad[["country_text_id", "country_name"] + rc.REGLAS + ["n_fechadas", "n_vigilancia"]
       ].to_csv(os.path.join(rc.OUT, "reglas_por_pais.csv"), index=False)

    # ---------------------------------------------------------- sin datar
    L("")
    L("ADOPTANTES SIN FECHA frente a datados (medias 2000-2011)")
    Xr = rc.covariables(p, 2011, log_trans=True,
                        vars_=rc.BASE_VARS + rc.DIAG_VARS)
    ad = ad.merge(Xr, left_on="country_text_id", right_index=True)
    ad["datado"] = ad.rol == "tratado_datado"
    cols = ["x_" + v for v in rc.BASE_VARS + rc.DIAG_VARS] + \
           ["aigs_dose", "vendor_china", "vendor_us", "tech_safecity", "tech_facial",
            "tech_smartpolicing", "tech_socialmedia", "n_fechadas"]
    filas = []
    for c in cols:
        a, b = ad.loc[ad.datado, c].astype(float), ad.loc[~ad.datado, c].astype(float)
        s = rc.smd(b, a)
        filas.append([c, round(a.mean(), 3), round(b.mean(), 3), round(s, 3)])
        L("  %-24s datados %8.3f | sin datar %8.3f | SMD %+.2f" % (c, a.mean(), b.mean(), s))
    # composición del grupo tratado con y sin los no datados
    todos = ad
    filas.append(["n", int(ad.datado.sum()), int((~ad.datado).sum()), np.nan])
    pd.DataFrame(filas, columns=["variable", "media_datados", "media_sin_datar",
                                 "smd_sin_datar_vs_datados"]).to_csv(
        os.path.join(rc.OUT, "sin_datar_descriptivo.csv"), index=False)
    L("  cambio en la media del grupo tratado al excluir a los sin datar:")
    for c in ["x_v2x_polyarchy", "x_v2stfisccap", "x_e_gdppc", "x_e_pop"]:
        L("    %-20s todos %.3f -> datados %.3f" % (c, todos[c].mean(),
                                                    ad.loc[ad.datado, c].mean()))
    ad[~ad.datado][["country_name", "region", "aigs_dose", "vendor_china", "vendor_us",
                    "n_fechadas", "year_min"]].to_csv(
        os.path.join(rc.OUT, "sin_datar_lista.csv"), index=False)

    # ---------------------------------------------------------- ventanas
    L("")
    L("VENTANAS DE COVARIABLES")
    g0 = int(min(coh))
    vent = []
    for g in sorted(coh):
        vent.append([g, coh[g], "2000-%d" % (g0 - 1), "2000-%d" % (g0 - 1),
                     "2000-%d" % (g - 1), "2000-%d" % (g - 1)])
    pd.DataFrame(vent, columns=["cohorte", "n_tratados", "principal_tratados",
                                "principal_comparacion", "sensibilidad_tratados",
                                "sensibilidad_comparacion"]).to_csv(
        os.path.join(rc.OUT, "ventanas_covariables.csv"), index=False)
    L("  principal: ventana común 2000-%d para todos los países y cohortes" % (g0 - 1))
    L("  (anterior a la primera cohorte: ningún año tratado entra en el ajuste)")
    L("  sensibilidad: 2000..g-1 para la cohorte g, igual en tratados y comparación")
    L("  ventana antigua (errónea): 2000-2015 para todos -> años tratados en las")
    L("  cohortes %s" % [g for g in sorted(coh) if g <= 2015])
    L.cerrar()


if __name__ == "__main__":
    main()
