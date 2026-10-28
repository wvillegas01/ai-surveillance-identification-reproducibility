# -*- coding: utf-8 -*-
"""
Influencia de las replicas de composicion incompleta (observacion del editor,
28 de octubre de 2026).

El manuscrito acotaba la influencia de esas replicas por lo raras que son. El
editor objeta, con razon, que la influencia depende tambien de los valores que
producen, no solo de su frecuencia, y pide comparar los errores estandar y los
resultados de equivalencia con los que se obtienen usando SOLO las replicas que
conservan las seis cohortes.

Este script no decide cual es el procedimiento correcto: descartar replicas
sesgaria el bootstrap, porque la composicion incompleta no es independiente de
la muestra extraida. Lo que hace es medir si la diferencia importa.

Entrada : soporte_restringido_replicas.csv  (una fila por replica, con marca)
          soporte_restringido.csv           (ATT y EE publicados)
          escala_latente_ordinal.csv        (paso ordinal y DE entre paises)
Salida  : comparacion_replicas_completas.csv
"""
import os
import sys

import numpy as np
import pandas as pd
from scipy import stats

import common as rc


def tost(att, se, margen):
    """Dos pruebas unilaterales al 5%: p = max de las dos colas."""
    if not np.isfinite(se) or se <= 0:
        return float("nan")
    p1 = 1.0 - stats.norm.cdf((att + margen) / se)
    p2 = stats.norm.cdf((att - margen) / se)
    return float(max(p1, p2))


def main():
    rep = pd.read_csv(os.path.join(rc.OUT, "soporte_restringido_replicas.csv"))
    pub = pd.read_csv(os.path.join(rc.OUT, "soporte_restringido.csv")).set_index("variable")
    esc = pd.read_csv(os.path.join(rc.OUT, "escala_latente_ordinal.csv")).set_index("variable")

    filas = []
    for var, g in rep.groupby("variable"):
        att = float(pub.loc[var, "ATT"])
        paso = float(esc.loc[var, "paso_medias"])
        sd = float(esc.loc[var, "sd_entre_paises"])
        todas = g.valor.values.astype(float)
        comp = g.valor[g.composicion_completa].values.astype(float)
        se_t = float(np.std(todas, ddof=1))
        se_c = float(np.std(comp, ddof=1))
        f = dict(variable=var, etiqueta=esc.loc[var, "etiqueta"], ATT=att,
                 n_todas=len(todas), n_completas=len(comp),
                 n_incompletas=len(todas) - len(comp),
                 SE_todas=se_t, SE_solo_completas=se_c,
                 dif_SE=se_c - se_t, cociente_SE=se_c / se_t,
                 media_todas=float(todas.mean()),
                 media_incompletas=float(g.valor[~g.composicion_completa].mean())
                 if (~g.composicion_completa).any() else float("nan"))
        for clave, margen in (("cuarto_paso", paso / 4.0),
                              ("quinto_paso", paso / 5.0),
                              ("decima_sd", sd / 10.0)):
            pt, pc = tost(att, se_t, margen), tost(att, se_c, margen)
            f["margen_" + clave] = margen
            f["TOSTp_todas_" + clave] = pt
            f["TOSTp_completas_" + clave] = pc
            f["equiv_todas_" + clave] = bool(pt < 0.05)
            f["equiv_completas_" + clave] = bool(pc < 0.05)
        filas.append(f)

    d = pd.DataFrame(filas)
    salida = os.path.join(rc.OUT, "comparacion_replicas_completas.csv")
    d.to_csv(salida, index=False)

    print("replicas por indicador: %d, de las cuales completas %d a %d"
          % (d.n_todas.iloc[0], d.n_completas.min(), d.n_completas.max()))
    print("")
    print("%-27s %8s %8s %8s   %-18s %-18s"
          % ("indicador", "EE todas", "EE comp.", "cociente",
             "TOST 1/4 todas", "TOST 1/4 completas"))
    for _, r in d.iterrows():
        print("%-27s %8.4f %8.4f %8.3f   %8.4f %-9s %8.4f %s"
              % (r.etiqueta, r.SE_todas, r.SE_solo_completas, r.cociente_SE,
                 r.TOSTp_todas_cuarto_paso,
                 "si" if r.equiv_todas_cuarto_paso else "no",
                 r.TOSTp_completas_cuarto_paso,
                 "si" if r.equiv_completas_cuarto_paso else "no"))
    print("")
    for clave, et in (("cuarto_paso", "un cuarto de paso"),
                      ("quinto_paso", "un quinto de paso"),
                      ("decima_sd", "una decima de DE")):
        a = int(d["equiv_todas_" + clave].sum())
        b = int(d["equiv_completas_" + clave].sum())
        print("equivalencia a %-20s todas %d de 8 | solo completas %d de 8%s"
              % (et, a, b, "" if a == b else "   <- CAMBIA"))
    print("")
    print("cociente de EE: %.3f a %.3f | diferencia absoluta maxima %.4f"
          % (d.cociente_SE.min(), d.cociente_SE.max(), d.dif_SE.abs().max()))
    print("  -> comparacion_replicas_completas.csv")
    return 0


if __name__ == "__main__":
    sys.exit(main())
