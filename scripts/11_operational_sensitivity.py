# -*- coding: utf-8 -*-
"""
Etapa 20n — Sensibilidad a la evidencia operativa (Revisor 2).

Restringe el grupo tratado a los paises cuyo registro datador documenta un
sistema en funcionamiento (Implemented o Retrospective en 20m) y compara con
la especificacion principal. Tambien resume el desfase entre el ano de
despliegue que declaran las fuentes y el primer ano documentado.

Segunda ronda (Revisor 1): sensibilidad informada por el desfase. Los paises
cuya fuente declara un despliegue anterior al primer ano documentado se redatan
con ese ano; los que quedarian antes de la primera cohorte no cumplen el periodo
previo minimo (2000-2011) y se excluyen. Variante: excluir todos los paises con
desfase.

Salidas: sensibilidad_operativa.csv, desfase_despliegue.csv, desfase_informado.csv
Uso:  python scripts/11_operational_sensitivity.py
"""
import os, re
import numpy as np
import pandas as pd
from scipy import stats
import common as rc

L = rc.Log("20n_operativa")


def main():
    L("=== 20n — sensibilidad a la evidencia operativa ===")
    p = pd.read_csv(os.path.join(rc.OUT, "estado_operativo_por_pais.csv"))
    oper = set(p[p.estado_operativo.isin(["Implemented", "Retrospective"])].country_text_id)
    d0 = rc.cargar()
    filas = []
    for nombre, d in [("Primary (81 treated)", d0),
                      ("Operational evidence only (%d treated)" % len(oper),
                       d0[d0.cohort.isna() | d0.country_text_id.isin(oper)])]:
        for var, lab in rc.INDICADORES:
            cel, ev, (att, se), nviv, exc, _w = rc.paquete(d, var)
            filas.append(dict(muestra=nombre, variable=var, etiqueta=lab, ATT=att, SE=se,
                              IC_inf=att - 1.96 * se, IC_sup=att + 1.96 * se,
                              p=2 * (1 - stats.norm.cdf(abs(att / se))), cohortes=nviv,
                              n_tratados=d[d.cohort.notna()].country_text_id.nunique()))
            L("  %-40s %-27s ATT %+.3f (EE %.3f) p=%.3f cohortes %d"
              % (nombre, lab, att, se, filas[-1]["p"], nviv))
    pd.DataFrame(filas).to_csv(os.path.join(rc.OUT, "sensibilidad_operativa.csv"), index=False)

    c = pd.read_csv(os.path.join(rc.OUT, "codificacion_estado_operativo.csv"))
    m = rc.maestra().set_index("country_text_id")[rc.REGLA_PRINCIPAL]
    c["anio_tratamiento"] = c.country_text_id.map(m)
    c["anio_fuente"] = c.anio_despliegue_segun_fuente.astype(str).str.extract(r"(\d{4})")[0].astype(float)
    c = c[c.estado_operativo.isin(["Implemented", "Retrospective"]) & c.anio_fuente.notna()]
    c = c[~c.anio_despliegue_segun_fuente.astype(str).str.contains("planned")]
    c["desfase"] = c.anio_fuente - c.anio_tratamiento
    g = c.groupby("country_name").desfase.min()
    L("")
    L("DESFASE (año de despliegue según la fuente - primer año documentado), %d países:" % len(g))
    L("  antes del año documentado: %d | mismo año: %d | después: %d"
      % ((g < 0).sum(), (g == 0).sum(), (g > 0).sum()))
    for k, v in g[g != 0].items():
        L("    %-14s %+d" % (k, v))
    c.to_csv(os.path.join(rc.OUT, "desfase_despliegue.csv"), index=False)

    # ---- sensibilidad informada por el desfase (Revisor 1, segunda ronda)
    lag = c.groupby("country_text_id").agg(nombre=("country_name", "first"),
                                            fuente=("anio_fuente", "min"),
                                            doc=("anio_tratamiento", "first"))
    lag = lag[lag.fuente < lag.doc]
    g0 = int(d0.cohort.min())
    redatar = {k: v for k, v in lag.fuente.items() if v >= g0}
    fuera = sorted(set(lag.index) - set(redatar))
    nom = lambda ks: ", ".join("%s %d" % (lag.nombre[k], lag.fuente[k]) for k in ks)
    esc = [("Lag-informed dates",
            "Re-dated to the deployment year stated in the source (%s); excluded because the "
            "stated year precedes the first cohort (%s)" % (nom(redatar), nom(fuera)),
            dict(fechas=redatar, sin_paises=fuera)),
           ("Lagged countries excluded",
            "All countries whose source states an earlier deployment excluded (%s)"
            % ", ".join(lag.nombre), dict(sin_paises=list(lag.index)))]
    L("")
    L("SENSIBILIDAD INFORMADA POR EL DESFASE")
    filas = []
    for nombre, detalle, kw in esc:
        d = rc.cargar(**kw)
        for var, lab in rc.INDICADORES:
            cel, ev, (att, se), nviv, exc, _w = rc.paquete(d, var)
            filas.append(dict(escenario=nombre, detalle=detalle, cov_fin=d.attrs["cov_fin"],
                              variable=var, etiqueta=lab, ATT=att, SE=se,
                              IC_inf=att - 1.96 * se, IC_sup=att + 1.96 * se,
                              p=2 * (1 - stats.norm.cdf(abs(att / se))), cohortes=nviv,
                              n_tratados=d[d.cohort.notna()].country_text_id.nunique()))
            L("  %-28s %-27s ATT %+.3f (EE %.3f) p=%.3f tratados %d"
              % (nombre, lab, att, se, filas[-1]["p"], filas[-1]["n_tratados"]))
    pd.DataFrame(filas).to_csv(os.path.join(rc.OUT, "desfase_informado.csv"), index=False)
    L.cerrar()


if __name__ == "__main__":
    main()
