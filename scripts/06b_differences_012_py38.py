# -*- coding: utf-8 -*-
"""
Etapa 20d (2/3) — Estimacion con differences 0.1.2 (la version usada en el
manuscrito enviado). Debe ejecutarse con Python 3.8, porque es la ultima
version instalable en ese interprete.

Exporta, para cada panel y estimador, la tabla completa de celdas ATT(g,t)
incluidas las vacias, la excepcion capturada internamente en cada celda (si
la hay), los avisos emitidos y el agregado por tiempo relativo.

Uso:  py -3.8 06b_differences_012_py38.py
"""
import os, sys, warnings, platform
import numpy as np
import pandas as pd
import differences
from differences import ATTgt

HERE = os.path.dirname(os.path.abspath(__file__))
SW = os.path.join(os.environ.get("REPRO_OUTPUTS", os.path.join(os.path.dirname(HERE), "outputs")),
                  "results", "software")
COV5 = ["x_v2x_polyarchy", "x_v2x_rule", "x_v2stfisccap", "x_e_gdppc", "x_e_pop"]
VAR = "v2smgovfilprc"


def flat(df):
    df = df.copy()
    df.columns = ["_".join(map(str, c)).strip("_") if isinstance(c, tuple) else str(c)
                  for c in df.columns]
    return df.reset_index()


def main():
    print("python", platform.python_version(), "| differences", differences.__version__
          if hasattr(differences, "__version__") else "0.1.2",
          "| pandas", pd.__version__, "| numpy", np.__version__)
    for panel in ["enviada", "corregida"]:
        d = pd.read_csv(os.path.join(SW, "panel_%s.csv" % panel))
        dd = d.set_index(["country_text_id", "year"]).sort_index()
        for est in ["reg", "dr"]:
            a = ATTgt(data=dd, cohort_name="cohort")
            with warnings.catch_warnings(record=True) as ws:
                warnings.simplefilter("always")
                a.fit(formula="%s ~ %s" % (VAR, " + ".join(COV5)), est_method=est,
                      progress_bar=False)
            r = flat(a.results())
            ac = [c for c in r.columns if c.endswith("ATT")][0]
            sc = [c for c in r.columns if "std_error" in c.lower()][0]
            cel = r[["cohort", "base_period", "time", ac, sc]].copy()
            cel.columns = ["cohort", "base", "time", "att", "se"]
            exc = {}
            for s in a._result_dict:
                for el in a._result_dict[s]["ATTgt_ntl"]:
                    if getattr(el, "exception", None) is not None:
                        exc[(int(el.cohort), int(el.time))] = "%s: %s" % (
                            type(el.exception).__name__, str(el.exception)[:120])
            cel["excepcion"] = [exc.get((int(c), int(t)), "") for c, t in
                                zip(cel.cohort, cel.time)]
            cel.to_csv(os.path.join(SW, "celdas_v012_%s_%s.csv" % (panel, est)), index=False)
            ev = flat(a.aggregate("event"))
            ac = [c for c in ev.columns if c.endswith("ATT")][0]
            sc = [c for c in ev.columns if "std_error" in c.lower()][0]
            rc_ = [c for c in ev.columns if "relative" in c.lower()][0]
            ev = ev[[rc_, ac, sc]]; ev.columns = ["rel", "att", "se"]
            ev.to_csv(os.path.join(SW, "evento_v012_%s_%s.csv" % (panel, est)), index=False)
            try:
                s_ = flat(a.aggregate("simple"))
                simple = float(s_[[c for c in s_.columns if c.endswith("ATT")][0]].iloc[0])
            except Exception as ex:
                simple = float("nan")
            post = ev[ev.rel >= 0]
            print("%-9s %-3s cohortes con celdas %s | vacías %d/%d | excepciones %d | "
                  "avisos %d | simple %+.4f | media de e>=0 %+.4f (EE medio %.4f)"
                  % (panel, est, sorted(cel[cel.att.notna()].cohort.astype(int).unique()),
                     int(cel.att.isna().sum()), len(cel), len(exc), len(ws), simple,
                     post.att.mean(), post.se.mean()))


if __name__ == "__main__":
    sys.exit(main())
