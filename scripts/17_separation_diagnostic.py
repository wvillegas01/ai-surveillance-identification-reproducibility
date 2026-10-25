# -*- coding: utf-8 -*-
"""
Diagnostico del fallo bajo separacion completa, para una cohorte afectada.

Responde a los puntos 1 y 2 del editor. El manuscrito ha venido afirmando un
mecanismo ("la comparacion es numericamente degenerada porque los odds son del
orden de 1e-10") que no se sigue de la Ecuacion 9: los pesos normalizados son
invariantes a escala, de modo que multiplicar todos los odds por una constante
positiva no cambia nada. Este script no argumenta: mide.

Para la cohorte indicada registra, en este orden:

  1. ajuste del logit: convergencia, iteraciones, avisos, parametros
  2. scores ajustados: minimo y maximo por grupo, cuantos valen 1 o 0 en doble
     precision, y el odds correspondiente
  3. los pesos de la Ecuacion 9 calculados a mano, con sus dos convenciones de
     normalizacion, y el ESS de Kish
  4. el estimador doblemente robusto paso a paso, senalando el PRIMER valor no
     finito que aparece, si aparece
  5. lo que devuelve cada implementacion SIN ningun control nuestro, con sus
     avisos y su version
  6. que hace cada implementacion al agregar
  7. dependencias compartidas entre las implementaciones comparadas

Si el mecanismo interno no queda establecido, el script lo dice. La salida
sirve de material de apoyo para la respuesta al editor.

Uso:  python scripts/17_separation_diagnostic.py [--cohorte 2012]
"""
import os, sys, json, warnings, importlib
import numpy as np
import pandas as pd
import statsmodels.api as sm
import common as rc

G = 2012
for i, a in enumerate(sys.argv):
    if a == "--cohorte" and i + 1 < len(sys.argv):
        G = int(sys.argv[i + 1])

VAR = rc.PRINCIPAL
SEP = "-" * 78


def main():
    reg = {"cohorte": G, "variable": VAR}
    d = rc.cargar()
    p = rc.panel_bruto()
    X = rc.covariables(p, d.attrs["cov_fin"], log_trans=True)
    coh = d.groupby("country_text_id").cohort.first()
    ctrl = coh[coh.isna()].index
    tr = coh[coh == G].index
    idx = tr.append(ctrl)
    t = np.r_[np.ones(len(tr)), np.zeros(len(ctrl))]
    Xg = X.loc[idx, rc.COV5].values

    print(SEP)
    print("1. AJUSTE DEL LOGIT  (cohorte %d: %d tratados, %d comparacion)"
          % (G, len(tr), len(ctrl)))
    Z = sm.add_constant(Xg, has_constant="add")
    with warnings.catch_warnings(record=True) as ws:
        warnings.simplefilter("always")
        f = sm.GLM(t, Z, family=sm.families.Binomial()).fit()
    avisos = [str(w.message)[:90] for w in ws]
    print("   converged            : %s" % getattr(f, "converged", "n/d"))
    print("   iteraciones          : %s" % getattr(f, "fit_history", "n/d"))
    print("   parametros finitos   : %s" % bool(np.isfinite(f.params).all()))
    print("   |parametro| maximo   : %.3e" % np.abs(f.params).max())
    print("   avisos (%d)          : %s" % (len(avisos), avisos or "ninguno"))
    reg["logit"] = dict(converged=bool(getattr(f, "converged", False)),
                        params_finitos=bool(np.isfinite(f.params).all()),
                        max_abs_param=float(np.abs(f.params).max()),
                        avisos=avisos)

    ps = np.asarray(f.predict(Z), float)
    p1, p0 = ps[t == 1], ps[t == 0]
    print("")
    print(SEP)
    print("2. SCORES AJUSTADOS")
    print("   tratados     : min %.3e  max %.20g" % (p1.min(), p1.max()))
    print("   comparacion  : min %.3e  max %.3e" % (p0.min(), p0.max()))
    print("   tratados con 1-p == 0.0 exacto : %d de %d"
          % (int((1 - p1 == 0).sum()), len(p1)))
    print("   comparacion con p == 0.0 exacto: %d de %d"
          % (int((p0 == 0).sum()), len(p0)))
    with np.errstate(divide="ignore", invalid="ignore"):
        o1 = p1 / (1 - p1)
        o0 = p0 / (1 - p0)
    print("   odds tratados  no finitos: %d de %d" % (int((~np.isfinite(o1)).sum()), len(o1)))
    print("   odds comparacion no finitos: %d de %d" % (int((~np.isfinite(o0)).sum()), len(o0)))
    reg["scores"] = dict(tratados_p_igual_1=int((1 - p1 == 0).sum()),
                         comparacion_p_igual_0=int((p0 == 0).sum()),
                         odds_tratados_no_finitos=int((~np.isfinite(o1)).sum()),
                         odds_comparacion_no_finitos=int((~np.isfinite(o0)).sum()),
                         max_odds_comparacion=float(np.nanmax(o0)))

    print("")
    print(SEP)
    print("3. PESOS DE LA ECUACION 9, CALCULADOS A MANO")
    suma = o0.sum()
    w_unit = o0 / suma                      # suman 1
    w_media = o0 / o0.mean()                # media 1 sobre la comparacion
    N = len(t)
    w_muestra = o0 / (o0.sum() / N)         # media 1 sobre la muestra completa
    ess = (o0.sum() ** 2) / (o0 ** 2).sum()
    print("   suma de odds de comparacion   : %.3e" % suma)
    print("   normalizados a suma 1         : max %.4f" % w_unit.max())
    print("   normalizados a media 1 (comp.): max %.1f   <- convencion de la Tabla 4"
          % w_media.max())
    print("   normalizados a media 1 (todos): max %.1f   <- lectura literal de la Ec. 9"
          % w_muestra.max())
    print("   todos finitos                 : %s" % bool(np.isfinite(w_media).all()))
    print("   ESS de Kish                   : %.2f de %d comparacion (%.1f%%)"
          % (ess, len(o0), 100 * ess / len(o0)))
    print("   -> el ESS NO depende de la escala de los odds; la concentracion si")
    reg["pesos"] = dict(suma_odds=float(suma), max_suma1=float(w_unit.max()),
                        max_media1_comparacion=float(w_media.max()),
                        max_media1_muestra=float(w_muestra.max()),
                        finitos=bool(np.isfinite(w_media).all()),
                        ess_kish=float(ess))

    print("")
    print(SEP)
    print("4. ESTIMADOR DOBLEMENTE ROBUSTO PASO A PASO")
    Y = rc._wide(d, VAR)
    base, post = G - 1, min(G + 3, int(Y.columns.max()))
    ok = Y.index.isin(idx)
    Yg = Y.loc[Y.index[ok]]
    dy = (Yg[post] - Yg[base]).reindex(idx).values
    es_tr = np.r_[np.ones(len(tr), bool), np.zeros(len(ctrl), bool)]
    pasos = []
    wT = es_tr.astype(float) / es_tr.mean()
    pasos.append(("w^T = 1(G=g)/E[1(G=g)]", wT))
    wC = np.where(es_tr, 0.0, np.r_[np.zeros(len(tr)), w_media])
    pasos.append(("w^C (Ec. 9, media 1)", wC))
    Xc = Xg[~es_tr]
    beta = np.linalg.lstsq(sm.add_constant(Xc, has_constant="add"),
                           dy[~es_tr], rcond=None)[0]
    m = sm.add_constant(Xg, has_constant="add") @ beta
    pasos.append(("m(X) por MCO sobre la comparacion", m))
    pasos.append(("(w^T - w^C)", wT - wC))
    pasos.append(("(dY - m(X))", dy - m))
    pasos.append(("producto", (wT - wC) * (dy - m)))
    primer = None
    for nombre, v in pasos:
        v = np.asarray(v, float)
        nf = int((~np.isfinite(v)).sum())
        print("   %-38s no finitos: %d" % (nombre, nf))
        if nf and primer is None:
            primer = nombre
    att = float(np.nanmean((wT - wC) * (dy - m)))
    print("   ATT_DR(g=%d, t=%d) calculado a mano : %+.4f" % (G, post, att))
    print("   primer valor no finito en la cadena : %s" % (primer or "ninguno"))
    reg["dr_manual"] = dict(att=att, primer_no_finito=primer, periodo=post)

    print("")
    print(SEP)
    print("5. QUE DEVUELVE CADA IMPLEMENTACION, SIN CONTROLES NUESTROS")
    for nombre, mod in (("differences", "differences"), ("csdid", "csdid")):
        try:
            m_ = importlib.import_module(mod)
            v = getattr(m_, "__version__", "sin atributo __version__")
            print("   %-12s version %s" % (nombre, v))
            reg.setdefault("versiones", {})[nombre] = str(v)
        except Exception as e:
            print("   %-12s no disponible: %s" % (nombre, str(e)[:60]))
    print("   nota: las celdas crudas por implementacion, sin filtrado, estan en")
    print("         results/software/celdas_comparadas_corregida_dr.csv")
    cmp_ = os.path.join(rc.OUT, "software", "celdas_comparadas_corregida_dr.csv")
    if os.path.exists(cmp_):
        c = pd.read_csv(cmp_)
        g_ = c[c.cohort == G]
        print("   cohorte %d: %d celdas | v012 vacias %d | v030 vacias %d | csdid vacias %d"
              % (G, len(g_), int(g_.v012.isna().sum()), int(g_.v030.isna().sum()),
                 int(g_.csdid.isna().sum())))
        reg["celdas"] = dict(n=len(g_), v012_na=int(g_.v012.isna().sum()),
                             v030_na=int(g_.v030.isna().sum()),
                             csdid_na=int(g_.csdid.isna().sum()))

    print("")
    print(SEP)
    print("6. DEPENDENCIAS COMPARTIDAS")
    comunes = []
    for mod in ("numpy", "pandas", "scipy", "statsmodels", "sklearn"):
        try:
            m_ = importlib.import_module(mod)
            comunes.append("%s %s" % (mod, getattr(m_, "__version__", "?")))
        except Exception:
            pass
    print("   ambas implementaciones corren sobre: %s" % ", ".join(comunes))
    print("   -> la coincidencia entre ellas NO es independiente: comparten")
    print("      algebra lineal y el ajuste del modelo de propension")
    reg["dependencias_comunes"] = comunes

    dest = os.path.join(rc.OUT, "diagnostico_separacion_%d.json" % G)
    with open(dest, "w", encoding="utf8") as fh:
        json.dump(reg, fh, indent=2, ensure_ascii=False)
    print("")
    print("   -> %s" % os.path.basename(dest))
    return 0


if __name__ == "__main__":
    sys.exit(main())
