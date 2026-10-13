# -*- coding: utf-8 -*-
"""
Etapa 20d (3/3) — Comparacion celda a celda entre implementaciones.

Implementaciones, con identicos datos (outputs/results/software/panel_*.csv),
identica base ('varying'), comparacion con nunca tratados y el mismo
modelo de covariables:
  A  differences 0.1.2   (version del manuscrito enviado; via 20d2, Py 3.8)
  B  differences 0.3.0   (version vigente)
  C  csdid 0.4.2         (port independiente del paquete `did` de R)
  D  estimador manual    (common.manual_or, solo regresion de resultado)

Para el estimador doblemente robusto se documenta ademas la condicion
exacta que vacia una celda: separacion perfecta en el logit de propension,
propension ajustada numericamente igual a 1 en algun tratado, y el cociente
0/0 resultante en los pesos de la comparacion (att_if.py, w_cont).

Responde a R1 y R2 (verificacion del comportamiento del software).

Uso:  python scripts/06c_compare_implementations.py      (Python 3.12)
"""
import os, warnings, platform, collections
import numpy as np
import pandas as pd
import statsmodels.api as sm
import differences, csdid
import common as rc

L = rc.Log("20d_software")
SW = os.path.join(rc.OUT, "software")
VAR = rc.PRINCIPAL


def v030(d, est):
    dd = d.copy()
    dd.attrs.clear()
    cel, ev, simple, nviv, exc, ws = rc.paquete(dd, VAR, est=est)
    cel["excepcion"] = ""
    return cel, ev, simple, len(ws)


def csd(d, est):
    from csdid.att_gt import ATTgt
    x = d.copy()
    x["g"] = x.cohort.fillna(0).astype(int)
    ids = {c: i + 1 for i, c in enumerate(sorted(x.country_text_id.unique()))}
    x["id"] = x.country_text_id.map(ids)
    with warnings.catch_warnings(record=True) as ws:
        warnings.simplefilter("always")
        m = ATTgt(yname=VAR, tname="year", idname="id", gname="g", data=x,
                  control_group=["nevertreated"], xformla="~ " + " + ".join(rc.COV5))
        m.fit(est_method=est, base_period="varying", bstrap=False)
    r = m.summ_attgt().results if hasattr(m.summ_attgt(), "results") else m.results
    r = pd.DataFrame({"cohort": m.results["group"], "time": m.results["year"],
                      "att": m.results["att"], "se": m.results["se"]})
    msgs = collections.Counter("%s: %s" % (w.category.__name__, str(w.message)[:90]) for w in ws)
    return r, msgs, m


def condiciones(d):
    """Por cohorte: separacion, tratados con propension = 1 y fuera de soporte."""
    X = d.groupby("country_text_id")[rc.COV5].first()
    coh = d.groupby("country_text_id").cohort.first()
    out = []
    for g in sorted(coh.dropna().unique()):
        s = coh[(coh == g) | coh.isna()]
        t = (s == g).astype(float).values
        Z = sm.add_constant(X.loc[s.index].values)
        with warnings.catch_warnings(record=True) as ws:
            warnings.simplefilter("always")
            ps = sm.GLM(t, Z, family=sm.families.Binomial()).fit().predict()
        sep = any("eparation" in str(w.message) for w in ws)
        ps = np.where(ps > 1 - 1e-16, 1, ps)          # mismo redondeo que el paquete
        p1, p0 = ps[t == 1], ps[t == 0]
        out.append(dict(cohorte=int(g), n_tratados=int(t.sum()), separacion=sep,
                        tratados_ps_igual_1=int((p1 >= 1).sum()),
                        tratados_sobre_max_comparacion=int((p1 > p0.max()).sum()),
                        ps_max_comparacion=float(p0.max())))
    return pd.DataFrame(out)


def main():
    L("=== 20d — comparación de implementaciones ===")
    L("Python %s | differences %s | csdid %s | pandas %s | numpy %s | statsmodels %s"
      % (platform.python_version(), differences.__version__, csdid.__version__
         if hasattr(csdid, "__version__") else "0.4.2", pd.__version__, np.__version__,
         sm.__version__ if hasattr(sm, "__version__") else ""))
    resumen = []
    for panel in ["enviada", "corregida"]:
        d = pd.read_csv(os.path.join(SW, "panel_%s.csv" % panel))
        L("")
        L("PANEL %s: %d países, %d tratados" % (panel, d.country_text_id.nunique(),
                                               d[d.cohort.notna()].country_text_id.nunique()))
        cond = condiciones(d)
        cond.to_csv(os.path.join(SW, "condiciones_dr_%s.csv" % panel), index=False)
        man = rc.manual_or(d, VAR)
        for est in ["reg", "dr"]:
            a = pd.read_csv(os.path.join(SW, "celdas_v012_%s_%s.csv" % (panel, est)))
            b, evb, sb, nwb = v030(d, est)
            c, msgs, _m = csd(d, est)
            k = ["cohort", "time"]
            t = (a[k + ["att"]].rename(columns={"att": "v012"})
                 .merge(b[k + ["att"]].rename(columns={"att": "v030"}), on=k, how="outer")
                 .merge(c[k + ["att"]].rename(columns={"att": "csdid"}), on=k, how="outer"))
            if est == "reg":
                t = t.merge(man[k + ["att"]].rename(columns={"att": "manual"}), on=k,
                            how="outer")
            t.to_csv(os.path.join(SW, "celdas_comparadas_%s_%s.csv" % (panel, est)),
                     index=False)
            L("  %s:" % est)
            for col in [c_ for c_ in ["v012", "v030", "csdid", "manual"] if c_ in t]:
                vac = t[t[col].isna()].cohort.astype(int).unique()
                L("    %-7s celdas %3d | vacías %3d | cohortes vacías %s"
                  % (col, t[col].notna().sum(), t[col].isna().sum(), list(vac)))
            for x_, y_ in [("v012", "v030"), ("v030", "csdid"), ("v030", "manual")]:
                if x_ in t and y_ in t:
                    both = t[[x_, y_]].dropna()
                    L("    |%s - %s| máx %.2e en %d celdas comunes"
                      % (x_, y_, (both[x_] - both[y_]).abs().max(), len(both)))
            if msgs:
                L("    avisos de csdid: %s" % "; ".join("%d× %s" % (v, k_)
                                                     for k_, v in msgs.most_common(4)))
            L("    avisos de differences 0.3.0: %d" % nwb)
            # ¿que hace cada implementacion al agregar con celdas vacias?
            import io, contextlib
            for na in (False, True):
                try:
                    with contextlib.redirect_stdout(io.StringIO()):
                        _m.aggte(typec="dynamic", na_rm=na, bstrap=False)
                    L("    csdid aggte(na_rm=%s): agrega, ATT medio %+.4f"
                      % (na, _m.atte["overall_att"]))
                except Exception as ex:
                    L("    csdid aggte(na_rm=%s): SE NIEGA -> %s" % (na, str(ex)[:90]))
            L("    differences 0.3.0 aggregate('event'): agrega sin aviso, ATT medio "
              "posterior %+.4f" % evb[evb.rel >= 0].att.mean())
            resumen.append(dict(panel=panel, estimador=est,
                                vacias_v012=int(t.v012.isna().sum()),
                                vacias_v030=int(t.v030.isna().sum()),
                                vacias_csdid=int(t.csdid.isna().sum()),
                                max_dif_v012_v030=float((t.v012 - t.v030).abs().max()),
                                max_dif_v030_csdid=float((t.v030 - t.csdid).abs().max())))
        L("  condiciones del logit de propensión por cohorte:")
        for _i, r in cond.iterrows():
            L("    %d n=%2d separación=%-5s ps=1 en %d tratados | sobre el máximo de la "
              "comparación %d" % (r.cohorte, r.n_tratados, r.separacion,
                                  r.tratados_ps_igual_1, r.tratados_sobre_max_comparacion))
    pd.DataFrame(resumen).to_csv(os.path.join(SW, "resumen_implementaciones.csv"),
                                 index=False)
    L.cerrar()


if __name__ == "__main__":
    main()
