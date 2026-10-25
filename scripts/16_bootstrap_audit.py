# -*- coding: utf-8 -*-
"""
Auditoria del bootstrap de la submuestra con soporte comun (punto 4 del editor).

Este script registra el diagnostico que motivo la correccion aplicada en
v1.0.3. Hasta v1.0.2, 07_overlap.py remuestreaba los 34 tratados en conjunto.
La cohorte de 2015 conserva un solo pais tras la restriccion, de modo que
desaparecia de una parte apreciable de las replicas y la agregacion corria
sobre cinco cohortes en lugar de seis: el estimando cambiaba dentro del
bootstrap. 07_overlap.py estratifica ahora por cohorte, que es la alternativa
que mide el apartado C.

Este script mide tres cosas y no modifica nada:

  A. fidelidad: reproduce los EE publicados usando un unico flujo aleatorio
     compartido entre indicadores, como hace 07_overlap.py
  B. estabilidad: repite el procedimiento anterior con varias semillas, para ver
     cuanto depende el EE del flujo concreto
  C. alternativa: remuestreo estratificado por cohorte, que conserva el
     estimando, con el recuento de replicas utilizables

Uso:  python scripts/16_bootstrap_audit.py [--replicas 499] [--semillas 4]
"""
import os, sys, warnings
import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy import stats
import common as rc

warnings.filterwarnings("ignore")
B, NSEM = 499, 4
for i, a in enumerate(sys.argv):
    if a == "--replicas" and i + 1 < len(sys.argv):
        B = int(sys.argv[i + 1])
    if a == "--semillas" and i + 1 < len(sys.argv):
        NSEM = int(sys.argv[i + 1])
SEMILLAS = [20261011 + 7919 * k for k in range(NSEM)]


def logit_ps(t, X):
    Z = sm.add_constant(X, has_constant="add")
    with warnings.catch_warnings(record=True):
        warnings.simplefilter("always")
        f = sm.GLM(t, Z, family=sm.families.Binomial()).fit()
    return f.predict(Z)


def main():
    d = rc.cargar()
    X = rc.covariables(rc.panel_bruto(), d.attrs["cov_fin"], log_trans=True)
    coh = d.groupby("country_text_id").cohort.first()
    ctrl = coh[coh.isna()].index
    keep_tr, keep_ct = {}, {}
    for g in sorted(coh.dropna().unique()):
        tr = coh[coh == g].index
        idx = tr.append(ctrl)
        t = np.r_[np.ones(len(tr)), np.zeros(len(ctrl))]
        ps = logit_ps(t, X.loc[idx].values)
        p1, p0 = ps[t == 1], ps[t == 0]
        keep_tr[int(g)] = list(tr[p1 <= p0.max()])
        keep_ct[int(g)] = list(ctrl[p0 >= p1.min()])
    ret = sorted(sum(keep_tr.values(), []))

    def est(dd, var, u=None):
        Y = rc._wide(dd, var)
        if u is not None:
            Y = Y.loc[pd.Index(u)]
        cols = {y: i for i, y in enumerate(Y.columns)}
        filas, vivas = [], []
        for g in sorted(keep_tr):
            st = Y.index.isin(keep_tr[g]); sc = Y.index.isin(keep_ct[g])
            if st.sum() == 0 or sc.sum() < 7:
                continue
            vivas.append(g)
            Xt = X.reindex(Y.index[st])[rc.COV5].values
            Xc = X.reindex(Y.index[sc])[rc.COV5].values
            for tt in Y.columns:
                b = g - 1 if tt >= g else tt - 1
                if b not in cols:
                    continue
                dy = Y.values[:, cols[tt]] - Y.values[:, cols[b]]
                be = np.linalg.lstsq(np.column_stack([np.ones(sc.sum()), Xc]),
                                     dy[sc], rcond=None)[0]
                pr = np.column_stack([np.ones(st.sum()), Xt]) @ be
                filas.append((g, b, tt, float(np.mean(dy[st] - pr)),
                              int(st.sum())))
        return pd.DataFrame(filas, columns=["cohort", "base", "time", "att",
                                            "n_tr"]), vivas

    tr_p = np.array(ret)
    ct_p = np.array(sorted(set(sum(keep_ct.values(), []))))
    pub = pd.read_csv(os.path.join(rc.OUT, "soporte_restringido.csv")
                      ).set_index("variable")

    print("COMPOSICION RETENIDA")
    n = len(ret)
    for g in sorted(keep_tr):
        k = len(keep_tr[g])
        if k:
            print("  %d: %2d tratados | ausente en %.0f%% de las replicas conjuntas"
                  % (g, k, 100 * (1 - k / n) ** n))

    def corrida(modo, semilla):
        """Un flujo aleatorio compartido por los ocho indicadores, como en 07."""
        rng = np.random.default_rng(semilla)
        out = {}
        for var, _lab in rc.INDICADORES:
            sims, perdidas, fallos = [], 0, 0
            for _ in range(B):
                if modo == "conjunto":
                    u = np.r_[rng.choice(tr_p, len(tr_p)),
                              rng.choice(ct_p, len(ct_p))]
                else:
                    partes = [rng.choice(np.array(v), len(v))
                              for v in keep_tr.values() if v]
                    u = np.r_[np.concatenate(partes), rng.choice(ct_p, len(ct_p))]
                try:
                    c2, vivas = est(d, var, u)
                    sims.append(rc.agregar_simple(c2))
                    if len(vivas) < sum(1 for v in keep_tr.values() if v):
                        perdidas += 1
                except Exception:
                    fallos += 1
            out[var] = dict(se=float(np.std(sims, ddof=1)), usables=len(sims),
                            fallos=fallos, perdidas=perdidas)
        return out

    print("")
    print("A. FIDELIDAD  (modo vigente, semilla original, flujo compartido)")
    base = corrida("conjunto", SEMILLAS[0])
    for var, lab in rc.INDICADORES:
        print("  %-27s %.4f vs %.4f publicado  %s"
              % (lab, base[var]["se"], pub.loc[var, "SE"],
                 "OK" if abs(base[var]["se"] - pub.loc[var, "SE"]) < 1e-3
                 else "NO COINCIDE"))

    print("")
    print("B. ESTABILIDAD DEL PROCEDIMIENTO VIGENTE ENTRE SEMILLAS")
    conj = {s: (base if s == SEMILLAS[0] else corrida("conjunto", s))
            for s in SEMILLAS}
    for var, lab in rc.INDICADORES:
        v = [conj[s][var]["se"] for s in SEMILLAS]
        print("  %-27s EE: %s | razon max/min %.1f"
              % (lab, " ".join("%.3f" % x for x in v), max(v) / min(v)))

    print("")
    print("C. REMUESTREO ESTRATIFICADO POR COHORTE")
    estr = {s: corrida("estratificado", s) for s in SEMILLAS}
    for var, lab in rc.INDICADORES:
        v = [estr[s][var]["se"] for s in SEMILLAS]
        print("  %-27s EE: %s | razon max/min %.1f"
              % (lab, " ".join("%.3f" % x for x in v), max(v) / min(v)))

    filas = []
    for var, lab in rc.INDICADORES:
        cel, _ = est(d, var)
        filas.append(dict(
            variable=var, etiqueta=lab, ATT=rc.agregar_simple(cel),
            SE_publicado=float(pub.loc[var, "SE"]),
            SE_conjunto_media=float(np.mean([conj[s][var]["se"] for s in SEMILLAS])),
            SE_conjunto_min=float(min(conj[s][var]["se"] for s in SEMILLAS)),
            SE_conjunto_max=float(max(conj[s][var]["se"] for s in SEMILLAS)),
            SE_estratificado_media=float(np.mean([estr[s][var]["se"] for s in SEMILLAS])),
            SE_estratificado_min=float(min(estr[s][var]["se"] for s in SEMILLAS)),
            SE_estratificado_max=float(max(estr[s][var]["se"] for s in SEMILLAS)),
            replicas=B,
            perdidas_conjunto=int(np.mean([conj[s][var]["perdidas"] for s in SEMILLAS])),
            perdidas_estratificado=int(np.mean([estr[s][var]["perdidas"] for s in SEMILLAS])),
            usables_conjunto=int(np.mean([conj[s][var]["usables"] for s in SEMILLAS])),
            usables_estratificado=int(np.mean([estr[s][var]["usables"] for s in SEMILLAS]))))
    f = pd.DataFrame(filas)
    f.to_csv(os.path.join(rc.OUT, "bootstrap_auditoria.csv"), index=False)

    pot = pd.read_csv(os.path.join(rc.OUT, "potencia_equivalencia_v2.csv"))
    m = f.merge(pot[["variable", "umbral_cuarto_paso", "umbral_quinto_paso"]],
                on="variable")
    print("")
    print("D. EQUIVALENCIA (TOST al 5%) SEGUN EL ESQUEMA")
    for col, nom in (("umbral_cuarto_paso", "1/4 de escalon"),
                     ("umbral_quinto_paso", "1/5 de escalon")):
        for se, et in (("SE_publicado", "publicado"),
                       ("SE_conjunto_media", "conjunto, media de semillas"),
                       ("SE_estratificado_media", "estratificado")):
            pv = 1 - stats.norm.cdf((m[col] - m.ATT.abs()) / m[se])
            print("  %-16s %-28s %d de 8" % (nom, et, int((pv < 0.05).sum())))
    print("")
    print("  replicas perdidas por cohorte ausente: conjunto %d de %d, "
          "estratificado %d de %d"
          % (f.perdidas_conjunto.mean(), B, f.perdidas_estratificado.mean(), B))
    print("  -> bootstrap_auditoria.csv")
    return 0


if __name__ == "__main__":
    sys.exit(main())
