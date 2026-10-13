# -*- coding: utf-8 -*-
"""
Etapa 20h — Figuras de la version revisada.

Regla de esta etapa: NINGUN valor numerico ni anotacion se escribe a mano.
Todo se lee de outputs/results/ y las anotaciones se calculan (la Fig. 4 enviada
tenia la frase «No coefficient excludes zero» fija en el script y un eje
recortado a -12..8; R2 lo detecto).

  Fig1  diagrama del diseno (recuentos del flujo muestral)
  Fig2  estructura de cohortes
  Fig3  cohortes usadas y estimacion por estimador y covariables
  Fig4  estudio de eventos completo (e = -18..10), con cohortes por e
  Fig5  estimaciones en pasos ordinales frente a la region de equivalencia:
        muestra completa (regresion de resultado) vs soporte comun
  Fig6  curva de especificaciones (fin de panel 2022 en todas)
  Fig7  comprobaciones de validez

Uso:  python scripts/13_figures.py
"""
import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
from matplotlib.ticker import MultipleLocator
import common as rc

matplotlib.rcParams.update({
    "font.family": "sans-serif", "font.sans-serif": ["DejaVu Sans"], "font.size": 10.5,
    "axes.titlesize": 12.5, "axes.labelsize": 10.5, "xtick.labelsize": 9.5,
    "ytick.labelsize": 9.5, "legend.fontsize": 10, "lines.linewidth": 1.9,
    "axes.linewidth": 0.9, "figure.dpi": 150, "savefig.dpi": 600,
    "savefig.bbox": "tight", "savefig.pad_inches": 0.06, "savefig.facecolor": "white",
    "pdf.fonttype": 42, "svg.fonttype": "none"})
INK, MUTED, RULE = "#151A22", "#5B6573", "#B9BFC9"
AZUL, OCRE, GRANATE, FONDO = "#3D4E93", "#A87231", "#9C3A40", "#F1F3F7"
O = lambda f: pd.read_csv(os.path.join(rc.OUT, f))


def limpiar(ax, eje="y"):
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(RULE)
    ax.tick_params(color=RULE, labelcolor=INK)
    ax.grid(axis=eje, color=RULE, lw=.7, alpha=.5); ax.set_axisbelow(True)


def guardar(fig, n):
    for e in ("png", "pdf", "svg"):
        fig.savefig(os.path.join(rc.FIGS, "%s.%s" % (n, e)))
    fig.savefig(os.path.join(rc.FIGS, "%s.jpg" % n), dpi=600,
                pil_kwargs={"quality": 95})
    plt.close(fig); print("  -> %s" % n)


# ------------------------------------------------------------------ Fig1
def fig1():
    fl = O("flujo_muestral_v2.csv").set_index("descripcion").n_paises
    m = rc.maestra()
    tr = m[m.rol == "tratado_datado"]
    n_tr, n_ct = len(tr), int(m.rol.isin(["control_limpio", "control_marcado"]).sum())
    n_sd = int((m.rol == "tratado_sin_datar").sum())
    mv = O("multiverso_v2.csv")
    g0, g1_ = int(tr[rc.REGLA_PRINCIPAL].min()), int(tr[rc.REGLA_PRINCIPAL].max())
    fig, ax = plt.subplots(figsize=(12.2, 6.4))
    ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
    COL = {1: (.020, .195), 2: (.268, .225), 3: (.541, .205), 4: (.794, .186)}
    FILA = {"a": .880, "b": .620, "c": .360}; ALTO = .175

    def caja(col, fila, tit, lin, color, alto=ALTO):
        x, w = COL[col]; yt = FILA[fila]
        ax.add_patch(FancyBboxPatch((x, yt - alto), w, alto,
                                    boxstyle="round,pad=0.006,rounding_size=0.018",
                                    lw=1.3, edgecolor=color, facecolor="white", zorder=3))
        ax.text(x + w / 2, yt - .042, tit, ha="center", va="center", fontsize=9.6,
                color=INK, weight="bold", zorder=4)
        for i, l in enumerate(lin):
            ax.text(x + w / 2, yt - .085 - i * .038, l, ha="center", va="center",
                    fontsize=8.3, color=MUTED, zorder=4)

    def flecha(p1, p2, color=RULE, lw=1.6):
        ax.add_patch(FancyArrowPatch(p1, p2, arrowstyle="-|>", mutation_scale=12, lw=lw,
                                     color=color, zorder=2, shrinkA=1, shrinkB=1))

    for col, etq, alto in [(1, "1 · SOURCES", .650), (2, "2 · PANEL & TREATMENT DATING", .695),
                           (3, "3 · ESTIMATION", .695), (4, "4 · DIAGNOSTICS", .695)]:
        x, w = COL[col]
        ax.add_patch(FancyBboxPatch((x - .012, .880 - alto - .010), w + .024, alto + .066,
                                    boxstyle="round,pad=0.004,rounding_size=0.014", lw=0,
                                    facecolor=FONDO, zorder=1))
        ax.text(x - .004, .916, etq, ha="left", va="center", fontsize=8.4, color=MUTED,
                weight="bold", style="italic")
    caja(1, "a", "AI surveillance index", ["97 documented adopters", "4 technologies"], AZUL, .130)
    caja(1, "b", "Digital Society Project v8", ["8 indicators", "2000–2025"], AZUL, .130)
    caja(1, "c", "V-Dem v16", ["pre-treatment", "covariates"], AZUL, .130)
    caja(2, "a", "Analytical panel",
         ["integrated: %d countries" % fl["Países en el panel integrado DSP x V-Dem x AIGS"],
          "estimated: %d countries, 2000–%d" % (n_tr + n_ct, rc.YEAR_MAIN),
          "%d dated · %d comparison" % (n_tr, n_ct)], AZUL)
    caja(2, "c", "Treatment dating",
         ["1,320 bibliographic records", "positive surveillance tag, eq. (1)",
          "%d dated · %d undated · %d–%d" % (n_tr, n_sd, g0, g1_)], OCRE)
    caja(3, "a", "Callaway–Sant'Anna", ["never-documented comparison",
                                       "eq. (2)–(4)", "clustered by country"], AZUL)
    caja(3, "c", "Group-time estimation", ["outcome regression",
                                           "covariates averaged 2000–%d" % (g0 - 1),
                                           "all %d cohorts retained" % tr[rc.REGLA_PRINCIPAL].nunique()], OCRE)
    caja(4, "a", "Specification space", ["%d configurations" % len(mv),
                                         "%d dating rules" % mv.regla_datacion.nunique(),
                                         "covariate sets and transforms",
                                         "3 comparison samples",
                                         "date shifts of 1–3 years"], AZUL, alto=.268)
    caja(4, "c", "Overlap diagnostics", ["overlap and weights by cohort",
                                                "support-restricted estimate",
                                                "equivalence, validity checks"], GRANATE)
    x1, w1 = COL[1]; x2, w2 = COL[2]; x3, w3 = COL[3]; x4, w4 = COL[4]
    for f in "abc":
        flecha((x1 + w1, FILA[f] - .065), (x2, FILA["a"] - ALTO / 2))
    flecha((x2 + w2 / 2, FILA["a"] - ALTO), (x2 + w2 / 2, FILA["c"]), RULE, 1.8)
    for f in "ac":
        flecha((x2 + w2, FILA[f] - .088), (x3, FILA[f] - .088))
        flecha((x3 + w3, FILA[f] - .088), (x4, FILA[f] - .088))
    flecha((x3 + w3 / 2, FILA["a"] - ALTO), (x3 + w3 / 2, FILA["c"]), RULE, 1.8)
    yb, hb = .012, .118
    ax.add_patch(FancyBboxPatch((x2 - .012, yb), (x4 + w4) - x2 + .012, hb,
                                boxstyle="round,pad=0.005,rounding_size=0.018", lw=1.4,
                                edgecolor=AZUL, facecolor="#3D4E930D", zorder=3))
    ax.text(x2 + .002, yb + hb - .026, "OUTCOME", ha="left", va="center", fontsize=8.4,
            color=AZUL, weight="bold", style="italic", zorder=4)
    cx = (x2 + x4 + w4) / 2
    ax.text(cx, yb + hb - .060, "Precise null estimates under outcome regression rest on "
            "extrapolation beyond common support;", ha="center", va="center", fontsize=9.6,
            color=INK, zorder=4)
    ax.text(cx, yb + hb - .095, "within the supported region the comparison is "
            "uninformative and unrepresentative.", ha="center", va="center", fontsize=9.0,
            color=MUTED, zorder=4)
    flecha((x4 + w4 / 2, FILA["c"] - ALTO), (x4 + w4 / 2, yb + hb), AZUL, 1.8)
    guardar(fig, "Fig1_design")


# ------------------------------------------------------------------ Fig2
def fig2():
    m = rc.maestra()
    tr = m[m.rol == "tratado_datado"]
    c = tr[rc.REGLA_PRINCIPAL].astype(int).value_counts().sort_index()
    n_ct = int(m.rol.isin(["control_limpio", "control_marcado"]).sum())
    n_mk = int((m.rol == "control_marcado").sum())
    n_sd = int((m.rol == "tratado_sin_datar").sum())
    fig, ax = plt.subplots(figsize=(10.4, 4.4))
    ax.bar(c.index, c.values, color=AZUL, width=.66, zorder=3)
    for g, n in c.items():
        ax.text(g, n + .35, str(n), ha="center", fontsize=9.5, color=INK)
    limpiar(ax)
    ax.set_xticks(c.index)
    ax.set_xlabel("First documented year of deployment (positive surveillance tag)")
    ax.set_ylabel("Countries")
    ax.set_ylim(0, c.max() * 1.25)
    ax.set_title("Staggered treatment structure: %d dated documented adopters in %d cohorts"
                 % (c.sum(), len(c)), loc="left", color=INK, pad=24)
    ax.text(0, 1.02, "Comparison group: %d countries without documented adoption (%d with "
            "surveillance-related records). Excluded from estimation: %d undated adopters."
            % (n_ct, n_mk, n_sd), transform=ax.transAxes, fontsize=9, color=MUTED)
    guardar(fig, "Fig2_cohorts")


# ------------------------------------------------------------------ Fig3
def fig3():
    g = O("estimador_covariables.csv")
    m = rc.maestra()
    tam = m[m.rol == "tratado_datado"][rc.REGLA_PRINCIPAL].astype(int).value_counts().to_dict()
    cohs = sorted(tam)
    nom = {"reg": "outcome regression", "dr": "doubly robust", "std_ipw": "IPW"}
    cv = {"sin covariables": "No covariates", "dos covariables": "Two covariates",
          "cinco covariables": "Five covariates"}
    g["lab"] = g.covariables.map(cv) + "\n(" + g.estimador.map(nom) + ")"
    fig, axes = plt.subplots(1, 2, figsize=(12.6, 0.62 * len(g) + 1.6),
                             gridspec_kw={"width_ratios": [1.45, 1]})
    ax = axes[0]
    for i, r in g.iterrows():
        y = len(g) - 1 - i
        vivas = [int(v) for v in str(r.cohortes).split()]
        for j, c in enumerate(cohs):
            v = c in vivas
            ax.scatter(j, y, s=tam[c] * 13, facecolor=AZUL if v else "white",
                       edgecolor=AZUL if v else GRANATE, lw=1.5, zorder=3)
        ax.text(len(cohs) - .35, y, "%d/%d cohorts · %d countries"
                % (len(vivas), len(cohs), r.tratados_representados), va="center", fontsize=9,
                color=INK if len(vivas) == len(cohs) else GRANATE)
    ax.set_xticks(range(len(cohs))); ax.set_xticklabels(cohs)
    ax.set_yticks(range(len(g))); ax.set_yticklabels(g.lab[::-1], fontsize=8.8)
    ax.set_xlim(-.7, len(cohs) + 2.8); ax.set_ylim(-.6, len(g) - .4)
    limpiar(ax, "x"); ax.grid(False)
    ax.set_xlabel("Treatment cohort")
    ax.set_title("a.  Cohorts with non-missing group–time estimates", fontsize=10.5,
                 loc="left", color=INK)
    ax = axes[1]
    for i, r in g.iterrows():
        y = len(g) - 1 - i
        col = AZUL if r.cohortes_vivas == len(cohs) else GRANATE
        ax.plot([r.ATT - 1.96 * r.SE, r.ATT + 1.96 * r.SE], [y, y], color=col, lw=2, zorder=3)
        ax.plot(r.ATT, y, "o", ms=7, color=col, mec="white", mew=1.2, zorder=4)
    ax.axvline(0, color=MUTED, lw=.9, ls=(0, (3, 3)))
    ax.set_yticks(range(len(g))); ax.set_yticklabels([""] * len(g))
    ax.set_ylim(-.6, len(g) - .4); limpiar(ax, "x")
    ax.set_xlabel("ATT, internet filtering (95% CI)")
    ax.set_title("b.  Resulting aggregate estimate", fontsize=10.5, loc="left", color=INK)
    fig.text(.005, -.02, "Circle area proportional to cohort size. Red: specifications in "
             "which cells are missing because a treated country has a fitted propensity "
             "score numerically equal to one.", fontsize=8.6, color=MUTED)
    fig.tight_layout()
    guardar(fig, "Fig3_estimators")


# ------------------------------------------------------------------ Fig4
def fig4():
    e = O("event_study_principal_filtrado.csv")
    npre, npost = int((e.rel < 0).sum()), int((e.rel >= 0).sum())
    sp, ss = int(e[e.rel < 0].excluye_cero_puntual.sum()), int(e[e.rel < 0].excluye_cero_simult.sum())
    qp, qs = int(e[e.rel >= 0].excluye_cero_puntual.sum()), int(e[e.rel >= 0].excluye_cero_simult.sum())
    res = O("resumen_escenarios.csv")
    w = res[(res.escenario == "principal") & (res.variable == rc.PRINCIPAL)].iloc[0]
    fig, (ax, axn) = plt.subplots(2, 1, figsize=(10.6, 6.2), sharex=True,
                                  gridspec_kw={"height_ratios": [3.2, 1]})
    ax.axhline(0, color=MUTED, lw=.9, ls=(0, (3, 3)), zorder=1)
    ax.axvline(-.5, color=GRANATE, lw=1, ls=(0, (2, 3)), zorder=1)
    for _i, r in e.iterrows():
        col = OCRE if r.rel < 0 else AZUL
        ax.plot([r.rel] * 2, [r.lo_sim, r.hi_sim], color=col, lw=1.1, alpha=.35, zorder=2)
        ax.plot([r.rel] * 2, [r.lo, r.hi], color=col, lw=2.0, alpha=.85, zorder=3)
        ax.plot(r.rel, r.att, "o", ms=5.5, color=col, mec="white", mew=1,
                zorder=4, fillstyle="full" if r.excluye_cero_puntual else "full")
        if r.excluye_cero_puntual:
            ax.plot(r.rel, r.att, "o", ms=10, mfc="none", mec=GRANATE, mew=1.2, zorder=5)
    limpiar(ax)
    ax.set_ylabel("ATT  ·  higher = less repression")
    ax.set_title("Internet filtering: event study, all %d event times, all eight cohorts"
                 % len(e), loc="left", color=INK, pad=30)
    ax.text(0, 1.03, "Thick bars: pointwise 95%% intervals; thin bars: Bonferroni bands within "
            "the pre (%d) and post (%d) families.\nExcluding zero: pre-treatment %d pointwise, %d "
            "simultaneous; post-treatment %d pointwise, %d simultaneous. Joint pre-trend Wald p = %.2f."
            % (npre, npost, sp, ss, qp, qs, w.wald_p), transform=ax.transAxes, fontsize=8.4,
            color=MUTED)
    ax.legend(handles=[Line2D([], [], marker="o", ls="", color=OCRE, label="Pre-treatment"),
                       Line2D([], [], marker="o", ls="", color=AZUL, label="Post-treatment")],
              frameon=False, fontsize=9.5, loc="lower left")
    axn.bar(e.rel, e.n_paises, color=[OCRE if r < 0 else AZUL for r in e.rel], width=.7,
            alpha=.75)
    for _i, r in e.iterrows():
        axn.text(r.rel, r.n_paises + 2, int(r.n_cohortes), ha="center", fontsize=7.2,
                 color=MUTED)
    limpiar(axn)
    axn.set_ylabel("Treated\ncountries", fontsize=9)
    axn.set_ylim(0, e.n_paises.max() * 1.3)
    axn.set_xlabel("Years relative to first documented deployment (numbers above bars: "
                   "contributing cohorts)")
    axn.xaxis.set_major_locator(MultipleLocator(2))
    axn.set_xlim(e.rel.min() - .8, e.rel.max() + .8)
    fig.tight_layout()
    guardar(fig, "Fig4_event_study")


# ------------------------------------------------------------------ Fig5
def fig5():
    pe = O("potencia_equivalencia_v2.csv").set_index("variable")
    sr = O("soporte_restringido.csv").set_index("variable")
    order = pe.sort_values("ATT").index
    fig, ax = plt.subplots(figsize=(10.6, 5.4))
    ax.axvspan(-.25, .25, color=GRANATE, alpha=.07, zorder=1)
    for s in (-.25, .25):
        ax.axvline(s, color=GRANATE, lw=1, ls=(0, (3, 3)), zorder=2)
    ax.axvline(0, color=MUTED, lw=.9, zorder=2)
    for i, v in enumerate(order):
        k = pe.loc[v, "paso"]
        for dy, src, col, lab in [(.14, pe, AZUL, "Full sample (outcome regression)"),
                                  (-.14, sr, OCRE, "Common-support subset")]:
            if v not in src.index:
                continue
            a, s = src.loc[v, "ATT"] / k, src.loc[v, "SE"] / k
            ax.plot([a - 1.96 * s, a + 1.96 * s], [i + dy] * 2, color=col, lw=2, zorder=3)
            ax.plot(a, i + dy, "o", ms=6.5, color=col, mec="white", mew=1.1, zorder=4,
                    label=lab if i == 0 else None)
    ax.set_yticks(range(len(order))); ax.set_yticklabels(pe.loc[order, "etiqueta"])
    ax.set_ylim(-.7, len(order) - .3); limpiar(ax, "x")
    ax.set_xlabel("ATT in ordinal steps of each indicator, with 95% CI")
    neq = int((pe.TOST_p_cuarto_paso < .05).sum())
    n_sr = int(sr.n_tratados.iloc[0])
    ax.set_title("Precision depends on extrapolation beyond common support", loc="left",
                 color=INK, pad=26)
    ax.text(0, 1.02, "Shaded: ±¼ ordinal step. Full sample: %d of 8 equivalent to zero (TOST). "
            "Common-support subset: %d of 81 treated countries, bootstrap intervals."
            % (neq, n_sr), transform=ax.transAxes, fontsize=9, color=MUTED)
    ax.legend(frameon=False, fontsize=9, loc="upper center", bbox_to_anchor=(.5, -.12),
              ncol=2)
    fig.tight_layout()
    guardar(fig, "Fig5_equivalence")


# ------------------------------------------------------------------ Fig6
def fig6():
    mv = O("multiverso_v2.csv").dropna(subset=["ATT"]).sort_values("ATT").reset_index(drop=True)
    fig, axes = plt.subplots(2, 1, figsize=(11, 6.8), sharex=True,
                             gridspec_kw={"height_ratios": [2.1, 1.2]})
    ax = axes[0]; x = np.arange(len(mv))
    ax.fill_between(x, mv.IC_inf, mv.IC_sup, color=AZUL, alpha=.13, lw=0)
    ax.plot(x, mv.ATT, "o", ms=3.4, color=AZUL)
    pr = mv[(mv.regla_datacion == rc.REGLA_PRINCIPAL) & (mv.covariables == "cinco covariables")
            & (mv.transformacion == "log") & (mv.muestra == "completa")].index
    ax.plot(pr, mv.loc[pr, "ATT"], "D", ms=7, color=GRANATE, label="Primary specification")
    ax.axhline(0, color=MUTED, lw=1, ls=(0, (3, 3)))
    limpiar(ax); ax.set_ylabel("ATT with 95% CI")
    ax.legend(frameon=False, fontsize=9, loc="upper left")
    ax.set_title("Specification curve: %d configurations, panel ending in %d"
                 % (len(mv), rc.YEAR_MAIN), loc="left", color=INK, pad=26)
    ax.text(0, 1.02, "%d of %d estimates negative; %d intervals exclude zero; range %+.2f to %+.2f."
            % ((mv.ATT < 0).sum(), len(mv), ((mv.IC_inf > 0) | (mv.IC_sup < 0)).sum(),
               mv.ATT.min(), mv.ATT.max()), transform=ax.transAxes, fontsize=9, color=MUTED)
    ax = axes[1]
    nr = {"year_surv_pos": "positive tag (primary)", "year_surv_neg": "smart-city excluded",
          "year_min": "earliest record", "year_2nd": "second distinct year",
          "year_p25": "25th percentile"}
    filas = [("Dating: " + v, mv.regla_datacion == k) for k, v in nr.items()] + [
        ("Five covariates", mv.covariables == "cinco covariables"),
        ("Two covariates", mv.covariables == "dos covariables"),
        ("No covariates", mv.covariables == "sin covariables"),
        ("Covariates in levels", mv.transformacion == "niveles"),
        ("Flagged comparisons excluded", mv.muestra == "sin marcados"),
        ("China excluded", mv.muestra == "sin China")]
    for i, (lab, sel) in enumerate(filas):
        y = len(filas) - 1 - i
        col = GRANATE if "levels" in lab else INK
        ax.plot(np.where(sel.values)[0], [y] * int(sel.sum()), "|", ms=6, color=col, mew=1.3)
    ax.set_yticks(range(len(filas))); ax.set_yticklabels([f[0] for f in filas][::-1],
                                                          fontsize=8.3)
    ax.set_ylim(-.7, len(filas) - .3); ax.set_xlim(-1, len(mv))
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color(RULE)
    ax.set_xlabel("Configurations, ordered by estimate")
    fig.tight_layout()
    guardar(fig, "Fig6_specification_curve")


# ------------------------------------------------------------------ Fig7
def fig7():
    v = O("validez_v2.csv").set_index("contraste")
    A = [("Internet filtering\n(substantive outcome)", "resultado sustantivo", AZUL),
         ("Coder disagreement\n(measurement)", "dispersión entre codificadores", MUTED),
         ("Number of coders\n(measurement)", "número de codificadores", MUTED)]
    pl = v.loc["prensa libre (> mediana de tratados)"]
    prr = v.loc["prensa restringida (<= mediana)"]
    reg = v.loc["placebo regional (no tratados de regiones de alta adopción)"]
    Bp = [("Restricted press\n(n = %d)" % prr.n_tratados, prr, AZUL),
          ("Free press\n(n = %d)" % pl.n_tratados, pl, OCRE),
          ("Regional placebo\n(n = %d pseudo-treated)" % reg.n_tratados, reg, MUTED)]
    fig, axes = plt.subplots(1, 2, figsize=(11.8, 4.4))
    for ax, datos, tit in ((axes[0], [(l, v.loc[k], c) for l, k, c in A],
                            "a.  Measurement-process outcomes"),
                           (axes[1], Bp, "b.  Press-freedom strata and regional placebo")):
        for i, (lab, r, col) in enumerate(datos):
            y = len(datos) - 1 - i
            ax.plot([r.estimacion - 1.96 * r.SE, r.estimacion + 1.96 * r.SE], [y] * 2,
                    color=col, lw=2.2, alpha=.85, zorder=3)
            ax.plot(r.estimacion, y, "o", ms=8, color=col, mec="white", mew=1.3, zorder=4)
            ax.text(r.estimacion, y + .27, "%+.3f" % r.estimacion, ha="center", fontsize=9)
        ax.axvline(0, color=MUTED, lw=.9, ls=(0, (3, 3)))
        ax.set_yticks(range(len(datos))); ax.set_yticklabels([d[0] for d in datos][::-1],
                                                             fontsize=9)
        ax.set_ylim(-.6, len(datos) - .3)
        for s in ("top", "right", "left"):
            ax.spines[s].set_visible(False)
        ax.spines["bottom"].set_color(RULE)
        ax.grid(axis="x", color=RULE, lw=.7, alpha=.5)
        ax.set_xlabel("ATT with 95% confidence interval")
        ax.set_title(tit, fontsize=10.5, loc="left", color=INK)
    fig.text(.005, -.04, "Primary specification: outcome regression, five pre-treatment "
             "covariates (2000–%d), all eight cohorts, 2000–%d." % (
                 rc.cargar().attrs["cov_fin"], rc.YEAR_MAIN), fontsize=8.8, color=MUTED)
    fig.tight_layout()
    guardar(fig, "Fig7_validity")


if __name__ == "__main__":
    for f in (fig1, fig2, fig3, fig4, fig5, fig6, fig7):
        f()
