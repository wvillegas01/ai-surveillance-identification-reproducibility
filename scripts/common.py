# -*- coding: utf-8 -*-
"""
Modulo comun (corresponde a la etapa 20 del proyecto; rutas del paquete).

Corrige tres discrepancias entre codigo y manuscrito detectadas al preparar
la respuesta a los revisores:

  1. Regla de datacion principal. El manuscrito (Ec. 1) exige una etiqueta
     positiva de tecnologia de vigilancia; el codigo usaba `year_min`, que
     incluia registros smart city sin componente de vigilancia. Desde aqui la
     regla principal es `year_surv_pos`, tal como la describe la Ec. 1.
  2. Ventana de covariables. El codigo promediaba 2000-2015 para todos los
     paises, de modo que en las cohortes 2012-2015 entraban anos ya tratados.
     Ahora la ventana principal es comun y anterior a toda cohorte:
     2000 .. (primera cohorte - 1). Como sensibilidad, ventanas propias de
     cada cohorte (2000 .. g-1) con el estimador manual.
  3. PIB per capita y poblacion entran en logaritmos en la especificacion
     principal; en niveles como sensibilidad.

Entorno: Python 3.12, differences 0.3.0, csdid 0.4.2 (ver requirements.txt).
"""
import os, io, datetime, warnings
import numpy as np
import pandas as pd

# Rutas del paquete de reproducibilidad (relativas a la raiz del repositorio).
# OUTPUTS puede redirigirse con la variable de entorno REPRO_OUTPUTS.
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
RAW = os.environ.get("REPRO_RAW", os.path.join(ROOT, "data", "raw"))
AIGS_XLSX = os.path.join(RAW, "aigs", "AIGS_2022.xlsx")
DSP_CSV = os.path.join(RAW, "dsp", "DSP_CY_v8.csv")
VDEM_CSV = os.path.join(RAW, "vdem", "V-Dem-CY-Full+Others-v16.csv")
ZOTERO = os.path.join(RAW, "zotero", "zotero_items.csv")
OUTPUTS = os.environ.get("REPRO_OUTPUTS", os.path.join(ROOT, "outputs"))
PANEL = os.path.join(OUTPUTS, "panel", "panel_analitico.csv")
DATING = os.path.join(OUTPUTS, "dating")
OUT = os.path.join(OUTPUTS, "results")
REP = os.path.join(OUTPUTS, "reports")
FIGS = os.path.join(OUTPUTS, "figures")
LOGS = os.path.join(OUTPUTS, "logs")
SUPP = os.path.join(OUTPUTS, "supplementary")
CACHE = os.path.join(OUTPUTS, "source_cache")

PANEL_START = 2000
YEAR_MAIN = 2022            # cierre del inventario documental (max ano fechado)
REGLA_PRINCIPAL = "year_surv_pos"
REGLAS = ["year_surv_pos", "year_surv_neg", "year_min", "year_2nd", "year_p25"]

BASE_VARS = ["v2x_polyarchy", "v2x_rule", "v2stfisccap", "e_gdppc", "e_pop"]
DIAG_VARS = ["v2x_libdem", "v2svstterr", "v2x_freexp_altinf"]
LOG_VARS = ["e_gdppc", "e_pop"]
COV5 = ["x_v2x_polyarchy", "x_v2x_rule", "x_v2stfisccap", "x_e_gdppc", "x_e_pop"]
COV2 = ["x_v2x_polyarchy", "x_v2x_rule"]
COV_LABEL = {"x_v2x_polyarchy": "Electoral democracy (v2x_polyarchy)",
             "x_v2x_rule": "Rule of law (v2x_rule)",
             "x_v2stfisccap": "Fiscal capacity (v2stfisccap)",
             "x_e_gdppc": "GDP per capita (e_gdppc)",
             "x_e_pop": "Population (e_pop)"}

INDICADORES = [
    ("v2smgovfilprc", "Internet filtering"),
    ("v2smgovsmmon", "Social media surveillance"),
    ("v2smgovsmcenprc", "Social media censorship"),
    ("v2smgovshut", "Internet shutdowns"),
    ("v2smgovsm", "Social media shutdowns"),
    ("v2smarrest", "Arrests for online content"),
    ("v2smgovdom", "Government disinformation"),
    ("v2smpardom", "Party disinformation"),
]
PRINCIPAL = "v2smgovfilprc"
ETIQ = dict(INDICADORES)

TAGS_VIG = {"Safe City": "safe_city", "Facial Recognition": "facial",
            "ABC/Facial Recognition": "facial", "Smart Policing": "smart_policing",
            "smart policing": "smart_policing", "SM Monitoring": "sm_monitoring",
            "Video Analytics": "safe_city",
            "Intelligent Video Surveillance": "safe_city"}


class Log:
    def __init__(self, nombre):
        self.nombre, self.lines = nombre, []
        for d in (OUT, REP, FIGS, LOGS, DATING, os.path.dirname(PANEL), SUPP):
            os.makedirs(d, exist_ok=True)

    def __call__(self, m=""):
        line = "[%s] %s" % (datetime.datetime.now().strftime("%H:%M:%S"), m)
        print(line); self.lines.append(line)

    def cerrar(self):
        stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        with io.open(os.path.join(LOGS, "%s_%s.log" % (self.nombre, stamp)), "w",
                     encoding="utf-8") as fh:
            fh.write("\n".join(self.lines) + "\n")


# ---------------------------------------------------------------- datos
def panel_bruto():
    return pd.read_csv(PANEL)


def maestra():
    return pd.read_csv(os.path.join(OUT, "tabla_maestra_v2.csv"))


def covariables(p, fin, ini=PANEL_START, log_trans=True, vars_=None):
    """Medias por pais en [ini, fin]. Devuelve columnas x_<var>."""
    vars_ = vars_ or BASE_VARS
    s = p[(p.year >= ini) & (p.year <= fin)]
    c = s.groupby("country_text_id")[vars_].mean()
    if log_trans:
        for v in LOG_VARS:
            if v in c:
                c[v] = np.log(c[v])
    c.columns = ["x_" + v for v in c.columns]
    return c


def cargar(regla=REGLA_PRINCIPAL, hasta=YEAR_MAIN, excl_marcados=False,
           log_trans=True, desplazar=0, cov_fin=None, sin_paises=None):
    """Panel de estimacion. `desplazar`=k adelanta k anos la fecha de
    tratamiento (g-k). La ventana de covariables termina el ano anterior a la
    primera cohorte efectiva salvo que se indique `cov_fin`."""
    m = maestra()
    p = panel_bruto()
    tr = m[(m.elegible) & (m.aigs_adopter == 1) & m[regla].notna()]
    ct = m[(m.elegible) & (m.aigs_adopter == 0)]
    if excl_marcados:
        ct = ct[~ct.control_marcado]
    coh = pd.concat([tr[["country_text_id"]].assign(cohort=tr[regla] - desplazar),
                     ct[["country_text_id"]].assign(cohort=np.nan)])
    if sin_paises:
        coh = coh[~coh.country_text_id.isin(sin_paises)]
    g0 = int(coh.cohort.min())
    fin = cov_fin if cov_fin is not None else g0 - 1
    X = covariables(p, fin, log_trans=log_trans)
    d = p.merge(coh, on="country_text_id").merge(X, left_on="country_text_id",
                                                 right_index=True)
    d = d[(d.year >= PANEL_START) & (d.year <= hasta)].copy()
    d.attrs.update(dict(regla=regla, hasta=hasta, cov_fin=fin, desplazar=desplazar,
                        log_trans=log_trans, excl_marcados=excl_marcados))
    return d


# ------------------------------------------------- estimador del paquete
def _flat(df):
    df = df.copy()
    df.columns = ["_".join(map(str, c)).strip("_") if isinstance(c, tuple) else str(c)
                  for c in df.columns]
    return df.reset_index()


def paquete(d, var, covs=COV5, est="reg"):
    """differences 0.3.0. Devuelve (celdas, evento, simple, nviv, excepciones)."""
    from differences import ATTgt
    dd = d.set_index(["country_text_id", "year"]).sort_index()
    a = ATTgt(data=dd, cohort_column="cohort")
    f = var if not covs else "%s ~ %s" % (var, " + ".join(covs))
    with warnings.catch_warnings(record=True) as ws:
        warnings.simplefilter("always")
        a.fit(f, est_method=est, progress_bar=False)
    g = _flat(a.results())
    ac = [c for c in g.columns if c.endswith("ATT")][0]
    sc = [c for c in g.columns if "std_error" in c.lower()][0]
    cel = g[["cohort", "base_period", "time", ac, sc]].copy()
    cel.columns = ["cohort", "base", "time", "att", "se"]
    # El paquete captura la excepcion de cada celda (attgt_cal.py, bloque
    # `except Exception`) y la excluye de la tabla de resultados
    # (utility_ntl.py, `exclude_fields`). Solo es accesible en el estado
    # interno, de modo que se recupera de ahi.
    exc = []
    for s in a._result_dict:
        for el in a._result_dict[s]["ATTgt_ntl"]:
            if el.exception is not None:
                exc.append((int(el.cohort), int(el.time), type(el.exception).__name__,
                            str(el.exception)))
    nviv = cel[cel.att.notna()].cohort.nunique()
    ev = _flat(a.aggregate("event"))
    ac = [c for c in ev.columns if c.endswith("ATT")][0]
    sc = [c for c in ev.columns if "std_error" in c.lower()][0]
    rc = [c for c in ev.columns if "relative" in c.lower()][0]
    ev = ev[[rc, ac, sc]].copy(); ev.columns = ["rel", "att", "se"]
    s = _flat(a.aggregate("simple"))
    sa = [c for c in s.columns if c.endswith("ATT")][0]
    ss = [c for c in s.columns if "std_error" in c.lower()][0]
    simple = (float(s[sa].iloc[0]), float(s[ss].iloc[0]))
    return cel, ev, simple, nviv, exc, [str(w.message) for w in ws]


# ------------------------------------------------- estimador manual (OR)
def _wide(d, var):
    return d.pivot_table(index="country_text_id", columns="year", values=var)


def manual_or(d, var, covs=COV5, xcoh=None, unidades=None, pre=None):
    """ATT(g,t) por regresion de resultado (Sant'Anna-Zhao, panel), base
    'varying' como el paquete: t>=g -> base g-1 ; t<g -> base t-1. Grupo de
    comparacion: nunca tratados documentados.
    `xcoh`: dict g -> DataFrame de covariables propio de la cohorte (ventana
    2000..g-1). Si es None se usan las columnas `covs` de `d`.
    `unidades`: lista (con repeticion) de paises para el bootstrap."""
    if pre is None:
        pre = preparar(d, var, covs)
    Y, coh, Xc = pre
    if unidades is not None:
        idx = pd.Index(unidades)
        Y, coh, Xc = Y.loc[idx], coh.loc[idx], Xc.loc[idx]
    Yv = Y.values
    cols = {y: i for i, y in enumerate(Y.columns)}
    never = coh.isna().values
    filas = []
    for g in sorted(coh.dropna().unique()):
        g = int(g)
        tr = (coh.values == g)
        X = Xc.values if xcoh is None else xcoh[g].reindex(Y.index)[covs].values
        Xt = np.column_stack([np.ones(tr.sum()), X[tr]])
        Xn = np.column_stack([np.ones(never.sum()), X[never]])
        for t in Y.columns:
            t = int(t)
            b = g - 1 if t >= g else t - 1
            if b not in cols or t == b:
                continue
            dy = Yv[:, cols[t]] - Yv[:, cols[b]]
            ok_n = never & np.isfinite(dy)
            ok_t = tr & np.isfinite(dy)
            if ok_t.sum() == 0:
                continue
            beta = np.linalg.lstsq(np.column_stack([np.ones(ok_n.sum()), X[ok_n]]),
                                   dy[ok_n], rcond=None)[0]
            pred = np.column_stack([np.ones(ok_t.sum()), X[ok_t]]) @ beta
            filas.append((g, b, t, float(np.mean(dy[ok_t] - pred)), int(ok_t.sum())))
    return pd.DataFrame(filas, columns=["cohort", "base", "time", "att", "n_tr"])


def preparar(d, var, covs=COV5):
    return (_wide(d, var), d.groupby("country_text_id").cohort.first(),
            d.groupby("country_text_id")[covs].first())


def agregar_evento(cel):
    """Agregacion por tiempo relativo con pesos proporcionales al tamano de
    cohorte entre las celdas disponibles (Callaway-Sant'Anna)."""
    c = cel.dropna(subset=["att"]).copy()
    c["rel"] = c.time - c.cohort
    out = c.groupby("rel").apply(
        lambda s: pd.Series({"att": np.average(s.att, weights=s.n_tr),
                             "n_cohortes": len(s), "n_paises": int(s.n_tr.sum())}),
        include_groups=False)
    return out.reset_index()


def agregar_simple(cel):
    """Promedio de los ATT(g,t) posteriores ponderado por tamano de cohorte."""
    c = cel.dropna(subset=["att"])
    c = c[c.time >= c.cohort]
    return float(np.average(c.att, weights=c.n_tr))


def xcoh_dict(d, log_trans=True):
    """Covariables con ventana propia de cada cohorte: 2000..g-1, la misma
    ventana de calendario para tratados y comparacion."""
    p = panel_bruto()
    out = {}
    for g in sorted(d.cohort.dropna().unique()):
        out[int(g)] = covariables(p, int(g) - 1, log_trans=log_trans)
    return out


def bootstrap(d, var, covs=COV5, xcoh=None, B=499, seed=20261011, rel_max=None):
    """Bootstrap por conglomerados de pais del estimador manual: devuelve
    matriz de replicas por tiempo relativo y del agregado simple."""
    rng = np.random.default_rng(seed)
    pre = preparar(d, var, covs)
    coh = pre[1]
    tr_p = coh[coh.notna()].index.values
    ct_p = coh[coh.isna()].index.values
    evs, sims = [], []
    for _b in range(B):
        # remuestreo estratificado: tratados y comparacion por separado
        u = np.r_[rng.choice(tr_p, len(tr_p)), rng.choice(ct_p, len(ct_p))]
        try:
            cel = manual_or(d, var, covs, xcoh, unidades=u, pre=pre)
            ev = agregar_evento(cel).set_index("rel").att
            evs.append(ev); sims.append(agregar_simple(cel))
        except Exception:
            continue
    return pd.DataFrame(evs), np.array(sims)


def smd(x1, x0, w0=None):
    x1, x0 = np.asarray(x1, float), np.asarray(x0, float)
    m1, v1 = x1.mean(), x1.var(ddof=1)
    if w0 is None:
        m0, v0 = x0.mean(), x0.var(ddof=1)
    else:
        w = np.asarray(w0, float); w = w / w.sum()
        m0 = np.sum(w * x0); v0 = np.sum(w * (x0 - m0) ** 2) / (1 - np.sum(w ** 2))
    s = np.sqrt((v1 + x0.var(ddof=1)) / 2.0)   # denominador fijo, sin pesos
    return (m1 - m0) / s if s > 0 else np.nan
