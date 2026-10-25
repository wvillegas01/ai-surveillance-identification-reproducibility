# -*- coding: utf-8 -*-
"""
Etapa 20p — Auditoria de coherencia de cifras (Revisor 1, segunda ronda).

Coteja cada tabla numerica del manuscrito, celda a celda, con el archivo de
resultados que la genera, y cada cifra citada en el texto con la celda
concreta de la que procede (lista AFIRMACIONES). Una busqueda global de cada
cifra en todas las salidas no sirve: con mas de 200.000 valores, una cifra
aleatoria de tres decimales "aparece" casi siempre.

No forma parte de run_all.py porque necesita el manuscrito (.tex), que no se
distribuye en este paquete.

Salida: outputs/reports/auditoria_cifras.csv (una fila por cifra cotejada)
Uso:  python scripts/15_audit_manuscript_numbers.py ruta/al/manuscrito.tex
      (tras run_all.py; sale con codigo 1 si algo no cuadra)
"""
import os, re, sys
import numpy as np
import pandas as pd
import common as rc

TEX = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REPRO_TEX")
NUM = re.compile(r"(?<![\w.{])[-+]?\d+(?:\.\d+)?")
O = lambda f: pd.read_csv(os.path.join(rc.OUT, f))
VARS = [v for v, _l in rc.INDICADORES]
R = []


def filas_tabla(s, etiqueta):
    i = s.index(r"\label{%s}" % etiqueta)
    a, b = s.rindex(r"\begin{table", 0, i), s.index(r"\end{table", i)
    t = s[s.index(r"\begin{tabular", a):b]
    out = []
    for f in t.split(r"\\"):
        f = re.sub(r"\\(hline|toprule|midrule|bottomrule)\b", " ", f).strip()
        if "&" in f:
            celdas = [c.strip() for c in f.split("&")]
            if re.search(r"textbf|boldsymbol|begin\{tabular", celdas[0]):
                continue                                         # cabecera
            out.append((celdas[0], [m.group() for c in celdas[1:] for m in NUM.finditer(c)]))
    return out


def comparar(donde, rotulo, texto, esperado):
    """texto: lista de cifras tal como aparecen; esperado: lista de valores."""
    if len(texto) != len(esperado):
        R.append(dict(lugar=donde, fila=rotulo, cifra=" ".join(texto), esperado=str(esperado),
                      ok=False, nota="numero de cifras distinto"))
        return
    for t, e in zip(texto, esperado):
        dec = len(t.split(".")[1]) if "." in t else 0
        ok = e is not None and abs(abs(float(t)) - abs(round(float(e), dec))) < 1e-9 \
            and (float(t) == 0 or e == 0 or np.sign(float(t)) == np.sign(e) or round(e, dec) == 0
                 or not t[0] in "+-")
        R.append(dict(lugar=donde, fila=rotulo, cifra=t, esperado=e, ok=bool(ok), nota=""))


def tablas(s):
    esc = O("escala_latente_ordinal.csv").set_index("variable")
    for (rot, nums), v in zip(filas_tabla(s, "tab:dependent_variables"),
                              ["v2smgovsmmon", "v2smgovfilprc", "v2smgovsmcenprc", "v2smgovshut",
                               "v2smgovsm", "v2smarrest", "v2smgovdom", "v2smpardom"]):
        x = esc.loc[v]
        comparar("Table 1", rot, nums, [x.media, x.sd, x.paso_medias])

    fl = O("flujo_muestral_v2.csv").set_index("paso").n_paises
    esperado = [None, fl[1], fl[2], fl[1] - fl[2], fl[3], fl[4], fl[5] - 0, fl[8], fl[7], fl[11],
                fl[6], fl[8]]
    t2 = filas_tabla(s, "tab:sample_flow")
    plano = [n for _r, ns in t2 for n in ns if not re.fullmatch(r"20\d\d|12|2000|2025|4,636|636|4", n)]
    nums2 = {r: ns for r, ns in t2}
    comparar("Table 2", "panel", [nums2[k][0] for k in nums2 if k.startswith("Integrated")], [fl[1]])
    comparar("Table 2", "short history", [x for x in nums2[[k for k in nums2 if "fewer than" in k][0]]
                                          if x.startswith("-")], [-fl[2]])
    comparar("Table 2", "eligible", nums2["Eligible sample"], [fl[1] - fl[2]])
    comparar("Table 2", "covariates", nums2[[k for k in nums2 if "incomplete" in k][0]], [-fl[3]])
    comparar("Table 2", "main sample", nums2["Main analytical sample"], [fl[4], fl[5], fl[8]])
    comparar("Table 2", "undated", nums2[[k for k in nums2 if "without a datable" in k][0]][:1], [-fl[7]])
    comparar("Table 2", "estimation", nums2["Effective estimation sample"], [fl[11], fl[6], fl[8]])

    bal = O("balance_agrupado.csv").set_index("covariable")
    for (rot, nums), c in zip(filas_tabla(s, "tab:pretreatment_balance"),
                              ["e_pop", "e_gdppc", "v2stfisccap", "v2svstterr", "v2libdem",
                               "v2polyarchy", "v2rule", "v2freexp_altinf"]):
        comparar("Table 3", rot, nums, list(bal.loc[c, ["tratados", "comparacion", "smd"]]))

    sp = O("soporte_por_especificacion.csv")
    sp = sp[sp.especificacion == "logaritmos"].set_index("cohorte")
    ap = O("apendice_cohortes.csv").set_index("cohorte")
    t4 = filas_tabla(s, "tab:overlap_diagnostics")
    for rot, nums in t4:
        if rot.startswith("Total"):
            comparar("Table 4", rot, nums, [sp.n_tratados.sum(), sp.sobre_max_comparacion.sum(),
                                            sp.fuera_crump_01_09.sum(), sp.separacion.sum(), 8])
            continue
        g = int(rot); x = sp.loc[g]
        comparar("Table 4", rot, nums, [x.n_tratados, x.sobre_max_comparacion,
                                            x.fuera_crump_01_09, x.peso_max, x.ESS, x.ESS_pct])
        comparar("Table 4", rot + " (appendix)", [nums[3], nums[4]], [ap.loc[g].peso_max, ap.loc[g].ESS])

    ec = O("estimador_covariables.csv").set_index(["estimador", "covariables"])
    claves = [("reg", "sin covariables"), ("reg", "dos covariables"), ("dr", "dos covariables"),
              ("std_ipw", "dos covariables"), ("reg", "cinco covariables"),
              ("dr", "cinco covariables"), ("std_ipw", "cinco covariables")]
    for (rot, nums), k in zip(filas_tabla(s, "tab:estimator_dependence"), claves):
        x = ec.loc[k]
        comparar("Table 5", rot, nums, [x.cohortes_vivas, 8, x.tratados_representados, x.ATT, x.SE])

    pe = O("potencia_equivalencia_v2.csv").set_index("variable")
    re_ = O("resumen_escenarios.csv")
    pr = re_[re_.escenario == "principal"].set_index("variable")
    for (rot, nums), v in zip(filas_tabla(s, "tab:outcome_estimates"), VARS):
        x, y = pe.loc[v], pr.loc[v]
        tost = x.TOST_p_cuarto_paso
        nums = [n for n in nums if n != "0.001"]   # "<0.001" se coteja aparte
        esperado = [x.ATT, x.IC_inf, x.IC_sup, y.ATT_dinamico, y.SE_dinamico, x.MDE_pasos]
        if len(nums) == 7:
            esperado.append(tost)
        else:                                   # "<0.001"
            R.append(dict(lugar="Table 6", fila=rot, cifra="<0.001", esperado=tost,
                          ok=bool(tost < 0.001), nota=""))
        comparar("Table 6", rot, nums, esperado)

    def rango(df, filtro):
        g = df[filtro]
        f = g[g.variable == rc.PRINCIPAL].iloc[0]
        return [f.ATT, f.SE, g.ATT.min(), g.ATT.max(),
                int(((g.IC_inf > 0) | (g.IC_sup < 0)).sum())]
    de = O("desplazamiento_fechas.csv"); di = O("desfase_informado.csv")
    so = O("sensibilidad_operativa.csv"); sr = O("soporte_restringido.csv")
    t7 = {"Primary": rango(re_, re_.escenario == "principal"),
          "Covariates in cohort-specific windows": rango(re_, re_.escenario == "ventana de covariables por cohorte"),
          "Comparison countries with records excluded": rango(re_, re_.escenario == "sin controles marcados"),
          "Income and population in levels": rango(re_, re_.escenario == "covariables en niveles"),
          "Treated with operational evidence only": rango(so, so.muestra.str.startswith("Operational")),
          "Within observed overlap": rango(sr, sr.variable.notna()),
          "Lag-informed dates": rango(di, di.escenario == "Lag-informed dates"),
          "Countries with stated earlier deployment excluded": rango(di, di.escenario == "Lagged countries excluded")}
    for k, n in zip(["one", "two", "three", "four", "five", "six"], range(1, 7)):
        t7["Treatment dates shifted %s year" % k] = rango(de, de.desplazamiento == n)
    for rot, nums in filas_tabla(s, "tab:sensitivity"):
        k = [k for k in t7 if rot.startswith(k)]
        par = re.findall(r"\((\d+)(?: treated)?\)", rot)
        if par:
            n_esp = {"Lag-informed dates": di[di.escenario == "Lag-informed dates"].n_tratados.iloc[0],
                     "Countries with stated earlier deployment excluded": di[di.escenario == "Lagged countries excluded"].n_tratados.iloc[0],
                     "Treated with operational evidence only": so[so.muestra.str.startswith("Operational")].n_tratados.iloc[0],
                     "Within observed overlap": sr.n_tratados.iloc[0]}[k[0]]
            comparar("Table 7", rot + " [n]", par, [n_esp])
        comparar("Table 7", rot, nums, t7[k[0]])

    tw = O("twfe_vs_escalonado.csv").set_index("variable")
    for (rot, nums), v in zip(filas_tabla(s, "tab:twfe_comparison"), VARS):
        x = tw.loc[v]
        comparar("Table 8", rot, nums, [x.TWFE, x.TWFE_SE, x.CS_simple, x.CS_simple_SE,
                                        x.CS_dinamico, x.CS_dinamico_SE, x.ratio_EE_simple,
                                        x.ratio_EE_dinamico])

    for rot, nums in filas_tabla(s, "tab:manual_reimplementation"):
        x = ap.loc[int(rot)]
        esp = [x.n, x.simple, x.regresion] + ([] if pd.isna(x.ipw) else [x.ipw, x.doble_robusto]) \
            + [x.tratados_ps_1, x.fuera_soporte]
        comparar("Table A2", rot, nums, esp)


def texto(s):
    """Cifras del texto corrido: cada afirmacion se reconstruye a partir de los
    resultados y debe aparecer literalmente en el manuscrito."""
    s = re.sub(r"\s+", " ", s)
    f3 = lambda x: "%+.3f" % x
    cm = O("cifras_manuscrito.csv").set_index("clave").valor
    fl = O("flujo_muestral_v2.csv").set_index("paso").n_paises
    re_ = O("resumen_escenarios.csv"); pr = re_[re_.escenario == "principal"].set_index("variable")
    fil = pr.loc[rc.PRINCIPAL]
    b = O("balance_por_cohorte.csv"); b = b[b.en_el_modelo]
    ab = lambda c, col: b[b.covariable == c][col].abs().mean()
    sp = O("soporte_por_especificacion.csv").groupby("especificacion")[
        ["sobre_max_comparacion", "fuera_crump_01_09"]].sum()
    ess = O("soporte_por_especificacion.csv").query("especificacion == 'logaritmos'").ESS
    mv = O("multiverso_v2.csv").dropna(subset=["ATT"])
    mvp = mv[mv.regla_datacion == rc.REGLA_PRINCIPAL]
    dc = O("descomposicion.csv").ATT.values
    tec = O("por_tecnologia.csv").query("variable == @rc.PRINCIPAL").set_index("familia")
    va = O("validez_v2.csv").set_index("contraste")
    sr = O("soporte_restringido.csv").set_index("variable")
    ratio = sr.SE / pr.SE_bootstrap
    ratio_an = sr.SE / pr.SE
    pe = O("potencia_equivalencia_v2.csv")
    de = O("desplazamiento_fechas.csv").query("variable == @rc.PRINCIPAL").set_index("desplazamiento").ATT
    di = O("desfase_informado.csv").query("variable == @rc.PRINCIPAL").set_index("escenario").ATT
    win = re_[re_.escenario == "ventana de covariables por cohorte"].set_index("variable").ATT
    ev = O("estado_operativo_por_pais.csv").estado_operativo.value_counts()
    cod = O("codificacion_estado_operativo.csv").base_codificacion.value_counts()
    lag = O("desfase_despliegue.csv").groupby("country_text_id").desfase.min()
    ap = O("apendice_cohortes.csv").set_index("cohorte")
    rg = lambda g: ap.loc[g, ["simple", "regresion", "ipw", "doble_robusto"]]
    esc = O("escala_latente_ordinal.csv")[["ancho_umbrales", "pendiente_ols"]]
    sd = O("sin_datar_descriptivo.csv").set_index("variable")
    afirm = [
        ("[0.1,0.9]; 47 sobre el maximo", "%d of the 81 treated countries have propensity scores above"
         % sp.loc["logaritmos"].sobre_max_comparacion),
        ("Crump", "; %d fall outside the interval" % sp.loc["logaritmos"].fuera_crump_01_09),
        ("niveles y cuadraticos", "With covariates in levels, %d treated countries lie above the comparison maximum and %d outside"
         % tuple(sp.loc["niveles"]) + r" \([0.1,0.9]\); with logarithms and quadratic terms, %d and %d"
         % tuple(sp.loc["log + cuadraticos"])),
        ("ESS mediano", r"median of the reported Kish effective sample sizes is \(%.1f\)" % ess.median()),
        ("balance medio", r"decreases from \(%.3f\) before weighting to \(%.3f\) afterward"
         % (b.smd_antes.abs().mean(), b.smd_despues.abs().mean())),
        ("balance umbral", "Before weighting, %d of the %d combinations exceed" % ((b.smd_antes.abs() > .25).sum(), len(b))
         + r" the \(0.25\) threshold; after weighting, %d combinations" % (b.smd_despues.abs() > .25).sum()),
        ("balance fiscal/PIB", r"fiscal capacity decreases from \(%.3f\) to \(%.3f\), and that for GDP per capita from \(%.3f\) to \(%.3f\)"
         % (ab("v2stfisccap", "smd_antes"), ab("v2stfisccap", "smd_despues"), ab("e_gdppc", "smd_antes"), ab("e_gdppc", "smd_despues"))),
        ("balance poblacion", r"decreasing only from \(%.3f\) to \(%.3f\)" % (ab("e_pop", "smd_antes"), ab("e_pop", "smd_despues"))),
        ("correlaciones", r"range from \(%.2f\) to \(%.2f\), with a mean of \(%.2f\)" % (cm.corr_min, cm.corr_max, cm.corr_media)
         + r", and the first principal component explains \(%d\%%\)" % round(100 * cm.pc1_varianza)),
        ("volumen documental", r"correlates with the documented year at \(%.2f\)" % cm.rho_volumen_principal),
        ("rho reglas", r"Spearman rank correlation of \(%.2f\)" % cm.rho_pos_neg),
        ("p25", "by an average of %.1f years" % cm.dif_media_p25_principal),
        ("fecha distinta", "assigns a different year to %d of the dated countries" % cm.n_fecha_distinta_min),
        ("reglas alternativas", "(%d datable countries)" % cm.n_datables_year_surv_neg),
        ("reglas alternativas 2", "the earliest record of any kind (%d)" % cm.n_datables_year_min),
        ("escala", r"yield values between \(%.2f\) and \(%.2f\)" % (esc.min().min(), esc.max().max())),
        ("sin fecha", "which occurs for %d of the %d documented adopters" % (fl[7], fl[5])),
        ("muestra", "The effective estimation sample comprises %d countries and %s country--year observations"
         % (fl[11], "{:,}".format(len(rc.cargar())))),
        ("panel", "contains %s observations for %d countries" % ("{:,}".format(len(rc.panel_bruto())), fl[1])),
        ("sin fecha tecnologias", "(mean %.1f against %.1f)" % (sd.loc["aigs_dose"].media_sin_datar, sd.loc["aigs_dose"].media_datados)),
        ("sin fecha facial", r"(%d\%% against %d\%%)" % (round(100 * sd.loc["tech_facial"].media_sin_datar), round(100 * sd.loc["tech_facial"].media_datados))),
        ("evidencias", "%d could be read in full and %d through the abstract stored in the library; %d were not accessible"
         % (cod["Full text"], cod["Zotero abstract"], cod["Source not accessible"])),
        ("estado operativo", "operating system for %d countries (%d implemented and %d retrospective), a contract or purchase for %d, an approved project for %d, and an announcement or negotiation for %d; for %d countries"
         % (ev.Implemented + ev.Retrospective, ev.Implemented, ev.Retrospective, ev.Contract, ev.Project, ev.Announcement, ev["Not established"])),
        ("desfase", "Among the %d countries whose sources state a deployment year, %d deployed in the documented year and %d deployed earlier"
         % (len(lag), (lag == 0).sum(), (lag < 0).sum())),
        ("horizontes", "Seventeen treated countries contribute observations eight years" if cm.paises_e8 == 17 else "#"),
        ("horizontes 2", "whereas %d contribute observations six years" % cm.paises_e6),
        ("cohorte 2018", r"yield \(%s\), \(%s\), \(%s\), and \(%s\), respectively, a range of \(%.2f\); for the 2019 cohort the range is \(%.2f\)"
         % tuple([f3(v) for v in rg(2018)] + [rg(2018).max() - rg(2018).min(), rg(2019).max() - rg(2019).min()])),
        ("previas", r"with a mean of \(%s\) and a maximum absolute value of \(%.3f\)" % (f3(cm.pre_media), cm.pre_max_abs)),
        ("Wald", r"\(p\)-values between \(%.3f\) and \(%.2f\); for internet filtering \(p=%.2f\)" % (cm.wald_p_min, cm.wald_p_max, fil.wald_p)),
        ("previas sig", "%d of the 144 pre-treatment pointwise intervals exclude zero" % cm.pre_sig_total),
        ("posteriores sig", "%d of the 88 post-treatment pointwise intervals exclude zero" % cm.post_sig_total),
        ("MDE", r"is \(%.2f\) latent units, equivalent to \(%.2f\) steps" % (pe.MDE_80.median(), pe.MDE_pasos.median())),
        ("bootstrap", r"bootstrap standard error for internet filtering is \(%.3f\), compared with an analytical standard error of \(%.3f\)"
         % (fil.SE_bootstrap, fil.SE)),
        ("bootstrap rango", r"bootstrap standard errors are %d--%d\%% larger" % (round(100 * ((pr.SE_bootstrap / pr.SE).min() - 1)), round(100 * ((pr.SE_bootstrap / pr.SE).max() - 1)))),
        ("p sin ajustar", r"range from \(%.2f\) to \(%.2f\)" % (cm.p_min, cm.p_max)),
        # el manuscrito declara los dos denominadores: el EE analitico de la
        # muestra completa y su EE bootstrap, que es la comparacion homogenea
        ("soporte EE", "The restricted standard errors are %.1f to %.1f times larger (median %.1f) "
         "than the analytical standard errors of the full sample, and %.1f to %.1f times larger "
         "(median %.1f) than its bootstrap standard errors"
         % (ratio_an.min(), ratio_an.max(), ratio_an.median(),
            ratio.min(), ratio.max(), ratio.median())),
        ("soporte rango", r"between \(%s\) and \(%s\) latent units" % (f3(sr.ATT.min()), f3(sr.ATT.max()))
         + r", with bootstrap standard errors"),
        ("soporte EE rango", r"between \(%.2f\) and \(%.2f\), obtained by resampling"
         % (sr.SE.min(), sr.SE.max())),
        ("multiverso", r"Most point estimates are negative, %d of the %d, but they are concentrated near zero: the median is \(%s\), the range extends from \(%s\) to \(%s\)"
         % ((mv.ATT < 0).sum(), len(mv), f3(mv.ATT.median()), f3(mv.ATT.min()), f3(mv.ATT.max()))),
        ("multiverso regla", r"the estimates range from \(%s\) to \(%s\)" % (f3(mvp.ATT.min()), f3(mvp.ATT.max()))),
        ("descomposicion", r"which yields \(%s\) under the same aggregation" % f3(dc[0])),
        ("descomposicion 2", r"leaves the estimate unchanged (\(%s\)), entering income and population in logarithms moves it to \(%s\), and adopting the positive-tag dating rule moves it to \(%s\)"
         % (f3(dc[1]), f3(dc[2]), f3(dc[3]))),
        ("desplazamientos", r"changes the filtering estimate by at most \(%.3f\)" % (np.ceil(1000 * (de.loc[1:3] - de.loc[0]).abs().max()) / 1000)),
        ("desplazamientos 4-6", r"with filtering estimates between \(%s\) and \(%s\)" % (f3(de.loc[4:6].min()), f3(de.loc[4:6].max()))),
        ("desfase informado", r"it gives a filtering estimate of \(%s\), and excluding all six countries gives \(%s\)"
         % (f3(di["Lag-informed dates"]), f3(di["Lagged countries excluded"]))),
        ("ventana por cohorte", r"reproduce the primary estimates to within \(%.3f\)" % (np.ceil(1000 * (win - pr.ATT).abs().max()) / 1000)),
        ("tecnologias", r"\(%s\) for safe-city platforms (%d dated countries), \(%s\) for facial recognition (%d), \(%s\) for smart policing (%d), and \(%s\) for social media monitoring (%d)"
         % (f3(tec.loc["safe_city"].ATT), tec.loc["safe_city"].n_tratados, f3(tec.loc["facial"].ATT), tec.loc["facial"].n_tratados,
            f3(tec.loc["smart_policing"].ATT), tec.loc["smart_policing"].n_tratados, f3(tec.loc["sm_monitoring"].ATT), tec.loc["sm_monitoring"].n_tratados)),
        ("prensa", r"\(%s\) among the %d documented adopters with more restricted pre-treatment press freedom and \(%s\) among the %d"
         % (f3(va.loc["prensa restringida (<= mediana)"].estimacion), va.loc["prensa restringida (<= mediana)"].n_tratados,
            f3(va.loc["prensa libre (> mediana de tratados)"].estimacion), va.loc["prensa libre (> mediana de tratados)"].n_tratados)),
        ("codificadores", r"estimate of \(%s\) with a standard error of \(%.3f\)" % (f3(va.loc["dispersión entre codificadores"].estimacion), va.loc["dispersión entre codificadores"].SE)),
        ("n codificadores", r"estimate of \(%s\) with a standard error of \(%.3f\)" % (f3(va.loc["número de codificadores"].estimacion), va.loc["número de codificadores"].SE)),
        ("placebo", r"to the %d comparison countries in regions with high documented adoption produces an estimate of \(%s\) with a standard error of \(%.3f\)"
         % (va.iloc[-1].n_tratados, f3(va.iloc[-1].estimacion), va.iloc[-1].SE)),
    ]
    for nombre, frase in afirm:
        R.append(dict(lugar="Text", fila=nombre, cifra=frase[:120], esperado="literal en el manuscrito",
                      ok=frase in s, nota=""))


def main():
    if not TEX:
        sys.exit("usage: python scripts/15_audit_manuscript_numbers.py path/to/manuscript.tex")
    s = open(TEX, encoding="utf-8").read()
    tablas(s)
    texto(s)
    d = pd.DataFrame(R)
    os.makedirs(rc.REP, exist_ok=True)
    d.to_csv(os.path.join(rc.REP, "auditoria_cifras.csv"), index=False, encoding="utf-8-sig")
    print("cifras cotejadas: %d | coinciden: %d | no coinciden: %d"
          % (len(d), d.ok.sum(), (~d.ok).sum()))
    print(d.groupby("lugar").ok.agg(["size", "sum"]).to_string())
    for _i, r in d[~d.ok].iterrows():
        print("  NO CUADRA %-9s %-45s texto %-10s esperado %s %s"
              % (r.lugar, r.fila[:45], r.cifra, r.esperado, r.nota))
    sys.exit(int((~d.ok).any()))


if __name__ == "__main__":
    main()
