# -*- coding: utf-8 -*-
"""
Etapa 20e — Solapamiento: distribuciones, especificaciones y estimacion
restringida al soporte comun.

Responde a:
  R2  la propension de un tratado por encima del maximo de la comparacion es
      un diagnostico de muestra finita, no prueba de violacion estructural de
      positividad -> se reportan las distribuciones completas, varios criterios
      de soporte y varias especificaciones del logit (niveles, logaritmos,
      logaritmos con terminos cuadraticos).
  R1/R2  analisis restringido a la region de solapamiento observado, con su
      poblacion objetivo explicitamente distinta.
  R1  balance por cohorte antes y despues de ponderar (suplemento).

Salidas: propension_por_pais.csv, soporte_por_especificacion.csv,
         balance_por_cohorte.csv, soporte_restringido.csv

Uso:  python scripts/07_overlap.py
"""
import os, warnings
import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy import stats
import common as rc

L = rc.Log("20e_solapamiento")
B = 2000   # el remuestreo estratificado tiene colas: 499 dejaba
           # un error Monte Carlo de hasta 3x entre semillas


def logit_ps(t, X):
    Z = sm.add_constant(X, has_constant="add")
    with warnings.catch_warnings(record=True) as ws:
        warnings.simplefilter("always")
        f = sm.GLM(t, Z, family=sm.families.Binomial()).fit()
    sep = any("eparation" in str(w.message) for w in ws)
    return f.predict(Z), sep


def disenos(d):
    """Matrices de covariables para cada especificacion del logit."""
    p = rc.panel_bruto()
    fin = d.attrs["cov_fin"]
    Xl = rc.covariables(p, fin, log_trans=True)
    Xn = rc.covariables(p, fin, log_trans=False)
    Xq = Xl.copy()
    for v in ["x_e_gdppc", "x_e_pop"]:
        Xq[v + "_2"] = Xq[v] ** 2
    return {"niveles": Xn, "logaritmos": Xl, "log + cuadraticos": Xq}


def main():
    L("=== 20e — solapamiento ===")
    d = rc.cargar()
    coh = d.groupby("country_text_id").cohort.first()
    nombres = d.groupby("country_text_id").country_name.first()
    ctrl = coh[coh.isna()].index
    esp = disenos(d)

    # ------------------------------------------------ 1. especificaciones
    filas, ps_rows = [], []
    for nom, X in esp.items():
        for g in sorted(coh.dropna().unique()):
            tr = coh[coh == g].index
            idx = tr.append(ctrl)
            t = np.r_[np.ones(len(tr)), np.zeros(len(ctrl))]
            ps, sep = logit_ps(t, X.loc[idx].values)
            p1, p0 = ps[t == 1], ps[t == 0]
            w = p0 / np.clip(1 - p0, 1e-12, None); w = w / w.mean()
            ess = w.sum() ** 2 / (w ** 2).sum()
            filas.append(dict(
                especificacion=nom, cohorte=int(g), n_tratados=len(tr), n_comparacion=len(ctrl),
                separacion=sep,
                sobre_max_comparacion=int((p1 > p0.max()).sum()),
                fuera_crump_01_09=int(((p1 < .1) | (p1 > .9)).sum()),
                ps_tratados_mediana=float(np.median(p1)),
                ps_comparacion_p95=float(np.percentile(p0, 95)),
                peso_max=float(w.max()), ESS=float(ess), ESS_pct=float(100 * ess / len(ctrl))))
            for u, v, tt in zip(idx, ps, t):
                ps_rows.append(dict(especificacion=nom, cohorte=int(g), country_text_id=u,
                                    country_name=nombres[u], tratado=int(tt), ps=float(v)))
    sp = pd.DataFrame(filas)
    sp.to_csv(os.path.join(rc.OUT, "soporte_por_especificacion.csv"), index=False)
    pd.DataFrame(ps_rows).to_csv(os.path.join(rc.OUT, "propension_por_pais.csv"), index=False)
    L("")
    L("1. SOPORTE POR ESPECIFICACIÓN DEL LOGIT (81 tratados, 8 cohortes)")
    for nom, g in sp.groupby("especificacion", sort=False):
        L("  %-18s separación %d/8 | tratados sobre el máx. de la comparación %2d/81 | "
          "fuera de [0,1;0,9] %2d/81 | peso máx %.1f | ESS mediano %.1f (%.0f%%)"
          % (nom, g.separacion.sum(), g.sobre_max_comparacion.sum(),
             g.fuera_crump_01_09.sum(), g.peso_max.max(), g.ESS.median(), g.ESS_pct.median()))
    L("  por cohorte (logaritmos):")
    for _i, r in sp[sp.especificacion == "logaritmos"].iterrows():
        L("    %d n=%2d sobre máx %2d | fuera [0,1;0,9] %2d | peso máx %6.1f | ESS %5.1f | sep %s"
          % (r.cohorte, r.n_tratados, r.sobre_max_comparacion, r.fuera_crump_01_09,
             r.peso_max, r.ESS, r.separacion))

    # ------------------------------------------------ 2. balance por cohorte
    L("")
    L("2. BALANCE POR COHORTE antes y después de ponderar (logaritmos)")
    X = esp["logaritmos"]
    X5 = X.join(rc.covariables(rc.panel_bruto(), d.attrs["cov_fin"],
                               vars_=rc.DIAG_VARS))
    bal = []
    for g in sorted(coh.dropna().unique()):
        tr = coh[coh == g].index
        idx = tr.append(ctrl)
        t = np.r_[np.ones(len(tr)), np.zeros(len(ctrl))]
        ps, _s = logit_ps(t, X.loc[idx].values)
        p0 = ps[t == 0]
        w = p0 / np.clip(1 - p0, 1e-12, None)
        for c in X5.columns:
            b0 = rc.smd(X5.loc[tr, c], X5.loc[ctrl, c])
            b1 = rc.smd(X5.loc[tr, c], X5.loc[ctrl, c], w0=w)
            bal.append(dict(cohorte=int(g), covariable=c.replace("x_", ""),
                            en_el_modelo=c in rc.COV5, smd_antes=b0, smd_despues=b1))
    bal = pd.DataFrame(bal)
    bal.to_csv(os.path.join(rc.OUT, "balance_por_cohorte.csv"), index=False)
    m = bal[bal.en_el_modelo]
    L("  covariables del modelo: |SMD| medio %.3f -> %.3f | >0,25: %d -> %d de %d"
      % (m.smd_antes.abs().mean(), m.smd_despues.abs().mean(),
         (m.smd_antes.abs() > .25).sum(), (m.smd_despues.abs() > .25).sum(), len(m)))
    n = bal[~bal.en_el_modelo]
    L("  diagnósticas externas: |SMD| medio %.3f -> %.3f | >0,25: %d -> %d de %d"
      % (n.smd_antes.abs().mean(), n.smd_despues.abs().mean(),
         (n.smd_antes.abs() > .25).sum(), (n.smd_despues.abs() > .25).sum(), len(n)))
    for c, g in bal.groupby("covariable", sort=False):
        L("    %-20s antes %+.3f -> después %+.3f (media entre cohortes)"
          % (c, g.smd_antes.mean(), g.smd_despues.mean()))

    # ------------------------------------------------ 3. restringido al soporte
    L("")
    L("3. ESTIMACIÓN RESTRINGIDA AL SOPORTE COMÚN OBSERVADO (logaritmos)")
    L("   por cohorte: tratados con ps <= máx. de la comparación y comparación con")
    L("   ps >= mín. de los tratados; cambia la población objetivo")
    keep_tr, keep_ct = {}, {}
    for g in sorted(coh.dropna().unique()):
        tr = coh[coh == g].index
        idx = tr.append(ctrl)
        t = np.r_[np.ones(len(tr)), np.zeros(len(ctrl))]
        ps, _s = logit_ps(t, X.loc[idx].values)
        p1, p0 = ps[t == 1], ps[t == 0]
        keep_tr[int(g)] = list(tr[p1 <= p0.max()])
        keep_ct[int(g)] = list(ctrl[p0 >= p1.min()])
    retenidos = sorted(sum(keep_tr.values(), []))
    L("  tratados retenidos: %d de 81 en %d cohortes" %
      (len(retenidos), sum(1 for v in keep_tr.values() if v)))
    rest = []
    for g in sorted(keep_tr):
        L("    %d: %d de %d tratados | comparación %d de %d | %s"
          % (g, len(keep_tr[g]), int((coh == g).sum()), len(keep_ct[g]), len(ctrl),
             ", ".join(nombres[keep_tr[g]]) if keep_tr[g] else "—"))
    # perfil de los retenidos frente a todos los tratados
    Xd = X5.loc[coh.dropna().index]
    L("  perfil (medias 2000-%d): todos los tratados vs retenidos" % d.attrs["cov_fin"])
    for c in X5.columns:
        L("    %-20s %8.3f vs %8.3f" % (c.replace("x_", ""), Xd[c].mean(),
                                         X5.loc[retenidos, c].mean() if retenidos else np.nan))

    def estimar_rest(dd, var, unidades=None):
        Y = rc._wide(dd, var)
        if unidades is not None:
            Y = Y.loc[pd.Index(unidades)]
        cols = {y: i for i, y in enumerate(Y.columns)}
        filas_ = []
        for g in sorted(keep_tr):
            sel_t = Y.index.isin(keep_tr[g]); sel_c = Y.index.isin(keep_ct[g])
            if sel_t.sum() == 0 or sel_c.sum() < 7:
                continue
            Xt = X.reindex(Y.index[sel_t])[rc.COV5].values
            Xc = X.reindex(Y.index[sel_c])[rc.COV5].values
            for t in Y.columns:
                b = g - 1 if t >= g else t - 1
                if b not in cols:
                    continue
                dy = Y.values[:, cols[t]] - Y.values[:, cols[b]]
                beta = np.linalg.lstsq(np.column_stack([np.ones(sel_c.sum()), Xc]),
                                       dy[sel_c], rcond=None)[0]
                pred = np.column_stack([np.ones(sel_t.sum()), Xt]) @ beta
                filas_.append((g, b, t, float(np.mean(dy[sel_t] - pred)), int(sel_t.sum())))
        return pd.DataFrame(filas_, columns=["cohort", "base", "time", "att", "n_tr"])

    # Remuestreo ESTRATIFICADO por cohorte. El conjunto perdia la cohorte de
    # 2015, que retiene un solo pais tratado, en cerca del 38% de las replicas,
    # y la agregacion corria entonces sobre cinco cohortes: el estimando
    # cambiaba dentro del propio bootstrap. Estratificando, los tratados de las
    # seis cohortes se extraen en todas las replicas, pero una replica puede
    # extraer pocos comparadores en una cohorte y dejarla sin estimar: esas se
    # conservan, se agregan sobre las cohortes que quedan y se marcan, para que
    # el script 19 pueda comparar ambos conjuntos. Dentro de una cohorte de un
    # solo pais el remuestreo no genera variacion, lo que es una propiedad de
    # la submuestra y se declara en el manuscrito.
    rng = np.random.default_rng(20261011)
    estratos = [np.array(v) for v in keep_tr.values() if v]
    ct_p = np.array(sorted(set(sum(keep_ct.values(), []))))
    n_coh = sum(1 for v in keep_tr.values() if v)
    replicas = []
    L("  remuestreo estratificado por cohorte: %s tratados por estrato"
      % ", ".join(str(len(e)) for e in estratos))
    for var, lab in rc.INDICADORES:
        cel = estimar_rest(d, var)
        if cel.empty:
            continue
        att = rc.agregar_simple(cel)
        sims, incompletas, fallos = [], 0, 0
        completa = []
        for _b in range(B):
            u = np.r_[np.concatenate([rng.choice(e, len(e)) for e in estratos]),
                      rng.choice(ct_p, len(ct_p))]
            try:
                c2 = estimar_rest(d, var, u)
                entera = c2.cohort.nunique() == n_coh
                if not entera:
                    incompletas += 1
                completa.append(entera)
                sims.append(rc.agregar_simple(c2))
            except Exception:
                fallos += 1
        se = float(np.std(sims, ddof=1))
        # el editor pregunta si las replicas de composicion incompleta mueven
        # el resultado: se guarda tambien el EE de las que conservan las seis
        sc = [v for v, e in zip(sims, completa) if e]
        se_completas = float(np.std(sc, ddof=1)) if len(sc) > 2 else float("nan")
        replicas.extend(dict(variable=var, replica=k, valor=float(v),
                             composicion_completa=bool(e))
                        for k, (v, e) in enumerate(zip(sims, completa)))
        rest.append(dict(variable=var, etiqueta=lab, n_tratados=len(retenidos),
                         n_cohortes=cel.cohort.nunique(), ATT=att, SE=se,
                         IC_inf=att - 1.96 * se, IC_sup=att + 1.96 * se,
                         p=2 * (1 - stats.norm.cdf(abs(att / se))),
                         replicas_solicitadas=B, replicas_usables=len(sims),
                         replicas_incompletas=incompletas, replicas_fallidas=fallos,
                         SE_solo_completas=se_completas, n_completas=len(sc),
                         error_montecarlo=se / np.sqrt(2 * (len(sims) - 1))))
        L("  %-27s ATT %+.3f (EE boot %.3f) p=%.3f | %d cohortes | %d/%d "
          "replicas usables, %d incompletas"
          % (lab, att, se, rest[-1]["p"], cel.cohort.nunique(),
             len(sims), B, incompletas))
    pd.DataFrame(rest).to_csv(os.path.join(rc.OUT, "soporte_restringido.csv"), index=False)
    pd.DataFrame(replicas).to_csv(
        os.path.join(rc.OUT, "soporte_restringido_replicas.csv"), index=False)
    pd.DataFrame([dict(cohorte=g, tratados_retenidos="|".join(keep_tr[g]),
                       n_comparacion=len(keep_ct[g])) for g in keep_tr]).to_csv(
        os.path.join(rc.OUT, "soporte_restringido_composicion.csv"), index=False)
    L.cerrar()


if __name__ == "__main__":
    main()
