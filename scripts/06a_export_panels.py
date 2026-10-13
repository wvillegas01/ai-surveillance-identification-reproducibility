# -*- coding: utf-8 -*-
"""
Etapa 20d (1/3) — Exporta los paneles de estimacion para la verificacion de
software, de modo que las tres implementaciones lean exactamente los mismos
datos.

  enviada    regla year_min, covariables 2000-2015 en niveles (la version
             enviada a la revista)
  corregida  regla de etiqueta positiva, covariables 2000-2011, logaritmos

Uso:  python scripts/06a_export_panels.py        (Python 3.12)
"""
import os
import common as rc

SW = os.path.join(rc.OUT, "software")


def main():
    os.makedirs(SW, exist_ok=True)
    for nombre, kw in [("enviada", dict(regla="year_min", cov_fin=2015, log_trans=False)),
                       ("corregida", dict())]:
        d = rc.cargar(**kw)
        cols = ["country_text_id", "year", "cohort", rc.PRINCIPAL] + rc.COV5
        d[cols].to_csv(os.path.join(SW, "panel_%s.csv" % nombre), index=False)
        print("panel_%s.csv: %d filas, %d países, %d tratados"
              % (nombre, len(d), d.country_text_id.nunique(),
                 d[d.cohort.notna()].country_text_id.nunique()))


if __name__ == "__main__":
    main()
