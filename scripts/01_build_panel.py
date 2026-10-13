#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Paso 01 — Construccion del panel analitico (etapas 02-03 del proyecto).

Cruza AIGS (tratamiento) x DSP v8 (dependientes) x V-Dem v16 (controles)
en un panel pais-anio 2000-2025 y escribe:

  outputs/results/panel_analitico.csv           panel completo, 179 paises x 26 anios
  outputs/results/covariables_pretratamiento.csv medias 2000-2015 por pais (etapa 10)
  outputs/results/proveedores_frecuencia.csv     paises proveedores parseados
  outputs/results/panel_resumen.csv              resumen de columnas del panel

Respeta las cuatro decisiones de la etapa 02:
  1. Aplica CELL_FIX y NAME_FIX antes de cruzar, con asercion de 179 paises.
  2. Marca (no elimina) Palestine/Gaza y South Sudan como fuera de la
     muestra principal por periodo previo insuficiente.
  3. Usa la escala latente como dependiente y conserva _ord solo descriptivo.
  4. Modela proveedor con indicadores no excluyentes y parsea el texto libre.

Ademas escribe aigs_corrections_log.csv con las celdas corrompidas del
archivo publicado del AIGS y su correccion.

Uso:  python scripts/01_build_panel.py
"""
import csv, io, os, sys, statistics as st, collections, datetime

csv.field_size_limit(10 ** 7)

import common as rc
OUT = os.path.dirname(rc.PANEL)
LOGS = rc.LOGS
AIGS_XLSX, DSP_CSV, VDEM_CSV = rc.AIGS_XLSX, rc.DSP_CSV, rc.VDEM_CSV

YEAR_MIN, YEAR_MAX = 2000, 2025
ONSET = 2016          # inicio comun, ruta A (cruce observado en v2smgovsmmon)
PRE_END = 2015        # ultimo anio del periodo previo
MIN_PRE_YEARS = 12    # minimo de anios previos para entrar en la muestra principal

NAME_FIX = {"Czech Republic": "Czechia", "Turkey": "Türkiye"}
CELL_FIX = {
    "UnitElectoral Democracy States of AmeriClosed Autocracy":
        "United States of America",
    "South KorElectoral Autocracy, SwElectoral Democracyen, Russia":
        "South Korea, Sweden, Russia",
}

DSP_VARS = ["v2smgovsmmon", "v2smgovfilprc", "v2smgovdom", "v2smpardom",
            "v2smgovshut", "v2smgovsm", "v2smgovsmcenprc", "v2smarrest"]
DSP_SUFFIX = ["", "_ord", "_codelow", "_codehigh", "_sd", "_nr"]

VDEM_VARS = ["v2x_polyarchy", "v2x_libdem", "v2x_regime", "v2x_civlib",
             "v2x_rule", "v2svstterr", "v2stfisccap", "v2x_freexp_altinf",
             "v2mecenefm", "v2xme_altinf", "e_gdppc", "e_pop",
             "e_regionpol_6C"]

AIGS_TECH = [("Safe City System", "tech_safecity"),
             ("Facial Recognition System", "tech_facial"),
             ("Smart Policing", "tech_smartpolicing"),
             ("Social Media Surveillance", "tech_socialmedia")]
AIGS_VENDOR = [("China Tech", "vendor_china"), ("US Tech", "vendor_us")]

_log = []


def log(m):
    line = "[%s] %s" % (datetime.datetime.now().strftime("%H:%M:%S"), m)
    print(line)
    _log.append(line)


def die(m):
    log("ABORTA: %s" % m)
    sys.exit(1)


def fx(v):
    return CELL_FIX.get(str(v).strip(), str(v).strip()) if v is not None else ""


def num(s):
    s = (s or "").strip()
    if s == "":
        return ""
    try:
        return float(s)
    except ValueError:
        return ""


def write_csv(name, header, rows):
    p = os.path.join(OUT, name)
    with io.open(p, "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(header)
        w.writerows(rows)
    log("  -> %s (%d filas x %d cols)" % (name, len(rows), len(header)))


# --------------------------------------------------------------------------
def corrections_log(wb):
    """Registra las celdas corrompidas del archivo publicado y su correccion."""
    filas = []
    for hoja in wb.sheetnames:
        ws = wb[hoja]
        hdr = [c.value for c in ws[1]]
        for rr in range(2, ws.max_row + 1):
            for cc in range(1, ws.max_column + 1):
                v = ws.cell(rr, cc).value
                if isinstance(v, str) and v.strip() in CELL_FIX:
                    filas.append([hoja, rr, hdr[cc - 1], v.strip(), CELL_FIX[v.strip()]])
    write_csv("aigs_corrections_log.csv", ["sheet", "row", "column", "published_value",
                                           "corrected_value"], filas)
    if len(filas) < 2:
        die("se esperaban al menos 2 celdas corrompidas en el AIGS publicado")


def load_aigs():
    """Devuelve dict nombre_corregido -> registro de tratamiento."""
    log("1. AIGS — tratamiento")
    import openpyxl
    wb = openpyxl.load_workbook(AIGS_XLSX, data_only=True)
    corrections_log(wb)

    s2 = list(wb["Digital Repression Inde + V-Dem"].iter_rows(values_only=True))
    h2 = s2[0]
    i_flag = list(h2).index("AIGS?")
    universo = {}
    for r in s2[1:]:
        if not r[0]:
            continue
        universo[fx(r[0])] = 1 if str(r[i_flag]).strip().lower() == "x" else 0
    log("   universo hoja 2: %d paises, %d adoptantes"
        % (len(universo), sum(universo.values())))

    s1 = list(wb["AIGS 2022"].iter_rows(values_only=True))
    h1 = list(s1[0])
    idx = {h: i for i, h in enumerate(h1) if h}
    det = {}
    vendor_countries = collections.Counter()
    for r in s1[1:]:
        if not r[0]:
            continue
        c = fx(r[0])
        rec = {}
        dose = 0
        for col, key in AIGS_TECH:
            on = 1 if r[idx[col]] not in (None, "") else 0
            rec[key] = on
            dose += on
        rec["aigs_dose"] = dose
        for col, key in AIGS_VENDOR:
            rec[key] = 1 if r[idx[col]] not in (None, "") else 0
        raw = fx(r[idx["Other Countries"]]) if r[idx["Other Countries"]] else ""
        rec["vendor_other"] = 1 if raw else 0
        rec["vendor_other_list"] = raw
        for part in [p.strip() for p in raw.split(",") if p.strip()]:
            vendor_countries[part] += 1
        rec["belt_road"] = 1 if r[idx["Member of Belt & Road Initiative"]] not in (None, "") else 0
        rec["china_odi_rank"] = num(str(r[idx["China ODI Rank (EIU)"]] or ""))
        rec["mil_exp_2018"] = num(str(r[idx["Military Expenditures (USD) 2018"]] or ""))
        det[c] = rec

    # coherencia: los adoptantes detallados deben ser exactamente los marcados
    marcados = set(k for k, v in universo.items() if v == 1)
    if set(det) != marcados:
        die("adoptantes hoja1 (%d) != hoja2 (%d); solo1=%s solo2=%s"
            % (len(det), len(marcados), sorted(set(det) - marcados)[:5],
               sorted(marcados - set(det))[:5]))
    if "United States of America" not in det:
        die("EE.UU. ausente tras CELL_FIX — la correccion no se aplico")
    log("   adoptantes con detalle: %d  (coherentes con la bandera)" % len(det))

    write_csv("proveedores_frecuencia.csv", ["pais_proveedor", "n_paises_cliente"],
              sorted(vendor_countries.items(), key=lambda kv: -kv[1]))
    return universo, det


# --------------------------------------------------------------------------
def load_dsp():
    log("2. DSP v8 — dependientes")
    rd = csv.reader(io.open(DSP_CSV, encoding="utf-8", newline=""))
    hdr = next(rd)
    I = {h: i for i, h in enumerate(hdr)}
    cols = [v + s for v in DSP_VARS for s in DSP_SUFFIX]
    faltan = [c for c in cols if c not in I]
    if faltan:
        die("columnas DSP ausentes: %s" % faltan[:8])
    data, names = {}, {}
    for r in rd:
        y = int(r[I["year"]])
        tid = r[I["country_text_id"]].strip()
        names[tid] = r[I["country_name"]].strip()
        data[(tid, y)] = {c: num(r[I[c]]) for c in cols}
        data[(tid, y)]["country_id"] = r[I["country_id"]].strip()
        data[(tid, y)]["COWcode"] = r[I["COWcode"]].strip()
    log("   %d celdas pais-anio | %d paises" % (len(data), len(names)))
    return data, names, cols


# --------------------------------------------------------------------------
def load_vdem():
    log("3. V-Dem v16 — controles")
    rd = csv.reader(io.open(VDEM_CSV, encoding="utf-8", newline=""))
    hdr = next(rd)
    I = {h: i for i, h in enumerate(hdr)}
    faltan = [v for v in VDEM_VARS if v not in I]
    if faltan:
        die("columnas V-Dem ausentes: %s" % faltan)
    itid, iy = I["country_text_id"], I["year"]
    data = {}
    for r in rd:
        try:
            y = int(r[iy])
        except ValueError:
            continue
        if not (YEAR_MIN <= y <= YEAR_MAX):
            continue
        data[(r[itid].strip(), y)] = {v: num(r[I[v]]) for v in VDEM_VARS}
    log("   %d celdas pais-anio en %d-%d" % (len(data), YEAR_MIN, YEAR_MAX))
    return data


# --------------------------------------------------------------------------
def build(universo, det, dsp, names, dsp_cols, vdem):
    log("4. Cruce y construccion del panel")

    # AIGS entra por nombre: mapear nombre -> country_text_id via DSP
    name2tid = {}
    for tid, nm in names.items():
        name2tid[nm] = tid
    resuelto, perdidos = {}, []
    for nm, flag in universo.items():
        key = NAME_FIX.get(nm, nm)
        tid = name2tid.get(key)
        if tid is None:
            perdidos.append(nm)
        else:
            resuelto[tid] = (nm, key, flag)
    if perdidos:
        die("AIGS sin correspondencia en DSP: %s" % perdidos)
    if len(resuelto) != 179:
        die("se esperaban 179 paises tras el cruce, hay %d" % len(resuelto))
    log("   AIGS -> DSP: %d/%d paises resueltos" % (len(resuelto), len(universo)))

    # anios disponibles por pais
    years_by = collections.defaultdict(list)
    for (tid, y) in dsp:
        years_by[tid].append(y)

    header = (["country_text_id", "country_name", "country_id", "COWcode",
               "year", "region"] +
              ["aigs_adopter", "aigs_dose"] +
              [k for _c, k in AIGS_TECH] +
              ["vendor_china", "vendor_us", "vendor_other", "vendor_other_list",
               "belt_road", "china_odi_rank", "mil_exp_2018"] +
              ["post_onset", "event_time", "treat_post"] +
              dsp_cols + VDEM_VARS +
              ["n_years_country", "n_pre_years", "sample_main"])

    rows, sin_vdem = [], 0
    excluidos = set()
    for tid, (nm_orig, nm_fix, flag) in sorted(resuelto.items()):
        ys = sorted(years_by[tid])
        n_pre = len([y for y in ys if y <= PRE_END])
        main = 1 if n_pre >= MIN_PRE_YEARS else 0
        if not main:
            excluidos.add(names[tid])
        d = det.get(nm_fix, {})
        for y in ys:
            cell = dsp[(tid, y)]
            v = vdem.get((tid, y))
            if v is None:
                sin_vdem += 1
                v = {k: "" for k in VDEM_VARS}
            post = 1 if y >= ONSET else 0
            row = [tid, names[tid], cell["country_id"], cell["COWcode"], y,
                   v.get("e_regionpol_6C", ""),
                   flag, d.get("aigs_dose", 0)]
            row += [d.get(k, 0) for _c, k in AIGS_TECH]
            row += [d.get("vendor_china", 0), d.get("vendor_us", 0),
                    d.get("vendor_other", 0), d.get("vendor_other_list", ""),
                    d.get("belt_road", 0), d.get("china_odi_rank", ""),
                    d.get("mil_exp_2018", "")]
            row += [post, y - ONSET, flag * post]
            row += [cell[c] for c in dsp_cols]
            row += [v.get(k, "") for k in VDEM_VARS]
            row += [len(ys), n_pre, main]
            rows.append(row)

    if sin_vdem:
        log("   aviso: %d celdas sin correspondencia en V-Dem" % sin_vdem)
    if len(rows) != len(dsp):
        die("filas del panel (%d) != celdas DSP (%d)" % (len(rows), len(dsp)))
    dups = len(rows) - len(set((r[0], r[4]) for r in rows))
    if dups:
        die("%d duplicados (country_text_id, year)" % dups)

    i_ad, i_main = header.index("aigs_adopter"), header.index("sample_main")
    n_paises = len(set(r[0] for r in rows))
    n_adopt = len(set(r[0] for r in rows if r[i_ad] == 1))
    n_main = len(set(r[0] for r in rows if r[i_main] == 1))
    log("   panel: %d filas | %d paises | %d adoptantes" % (len(rows), n_paises, n_adopt))
    log("   muestra principal: %d paises (excluidos por <%d anios previos: %s)"
        % (n_main, MIN_PRE_YEARS, ", ".join(sorted(excluidos)) or "ninguno"))
    if n_paises != 179 or n_adopt != 97:
        die("se esperaban 179 paises y 97 adoptantes")

    # coherencia dosis vs tecnologias
    i_dose = header.index("aigs_dose")
    i_tech = [header.index(k) for _c, k in AIGS_TECH]
    mal = sum(1 for r in rows if r[i_dose] != sum(r[i] for i in i_tech))
    if mal:
        die("%d filas con aigs_dose incoherente con las tecnologias" % mal)
    log("   coherencia dosis-tecnologias: correcta en las %d filas" % len(rows))

    write_csv("panel_analitico.csv", header, rows)
    return header, rows


# --------------------------------------------------------------------------
def pretreatment(header, rows):
    """Medias previas al tratamiento por pais, para el balanceo de la etapa 10."""
    log("5. Covariables previas al tratamiento (2000-%d)" % PRE_END)
    I = {h: i for i, h in enumerate(header)}
    VARS = ["v2x_polyarchy", "v2x_libdem", "v2x_rule", "v2svstterr",
            "v2stfisccap", "v2x_freexp_altinf", "e_gdppc", "e_pop"]
    acc = collections.defaultdict(lambda: collections.defaultdict(list))
    meta = {}
    for r in rows:
        if r[I["year"]] > PRE_END:
            continue
        tid = r[I["country_text_id"]]
        meta[tid] = (r[I["country_name"]], r[I["region"]], r[I["aigs_adopter"]],
                     r[I["aigs_dose"]], r[I["sample_main"]])
        for v in VARS:
            x = r[I[v]]
            if x != "":
                acc[tid][v].append(x)
    hdr = (["country_text_id", "country_name", "region", "aigs_adopter",
            "aigs_dose", "sample_main"] +
           ["pre_" + v for v in VARS] + ["pre_n_obs"])
    out = []
    for tid in sorted(acc):
        nm, reg, ad, dose, main = meta[tid]
        row = [tid, nm, reg, ad, dose, main]
        for v in VARS:
            vals = acc[tid][v]
            row.append(round(st.mean(vals), 5) if vals else "")
        row.append(len(acc[tid]["v2x_polyarchy"]))
        out.append(row)
    write_csv("covariables_pretratamiento.csv", hdr, out)

    # tabla de balance con diferencias estandarizadas (muestra principal)
    log("   balance previo al tratamiento (muestra principal, dif. estandarizada):")
    J = {h: i for i, h in enumerate(hdr)}
    bal = []
    for v in VARS:
        a = [r[J["pre_" + v]] for r in out if r[J["aigs_adopter"]] == 1
             and r[J["sample_main"]] == 1 and r[J["pre_" + v]] != ""]
        b = [r[J["pre_" + v]] for r in out if r[J["aigs_adopter"]] == 0
             and r[J["sample_main"]] == 1 and r[J["pre_" + v]] != ""]
        if not (a and b) or len(a) < 2 or len(b) < 2:
            continue
        ma, mb = st.mean(a), st.mean(b)
        sa, sb = st.pstdev(a), st.pstdev(b)
        pooled = ((sa ** 2 + sb ** 2) / 2.0) ** 0.5
        smd = (ma - mb) / pooled if pooled else 0.0
        # |SMD| > 0.25 se considera desbalance serio en la literatura de matching
        flag = "SERIO" if abs(smd) > 0.25 else ("moderado" if abs(smd) > 0.1 else "")
        bal.append([v, len(a), len(b), round(ma, 4), round(mb, 4),
                    round(ma - mb, 4), round(smd, 3), flag])
        log("      %-20s dif %+10.3f | SMD %+6.3f %s" % (v, ma - mb, smd, flag))
    write_csv("balance_pretratamiento.csv",
              ["variable", "n_adoptantes", "n_no_adoptantes", "media_adoptantes",
               "media_no_adoptantes", "diferencia", "dif_estandarizada",
               "desbalance"], bal)
    n_serio = sum(1 for r in bal if r[7] == "SERIO")
    log("   %d de %d covariables con desbalance serio (|SMD|>0.25)"
        % (n_serio, len(bal)))
    return out


def summarize(header, rows):
    log("6. Resumen del panel")
    I = {h: i for i, h in enumerate(header)}
    out = []
    for h in header:
        col = [r[I[h]] for r in rows]
        nn = [c for c in col if c != ""]
        numeric = [c for c in nn if isinstance(c, float) or isinstance(c, int)]
        if numeric and len(numeric) == len(nn):
            out.append([h, len(nn), round(100.0 * (len(col) - len(nn)) / len(col), 2),
                        round(min(numeric), 4), round(max(numeric), 4),
                        round(st.mean(numeric), 4)])
        else:
            out.append([h, len(nn), round(100.0 * (len(col) - len(nn)) / len(col), 2),
                        "", "", ""])
    write_csv("panel_resumen.csv",
              ["columna", "n_no_nulo", "pct_missing", "min", "max", "media"], out)


def main():
    for d in (OUT, LOGS):
        if not os.path.isdir(d):
            os.makedirs(d)
    log("=== Etapa 03 — construccion del panel analitico ===")
    log("    inicio comun=%d | periodo previo hasta %d | min anios previos=%d"
        % (ONSET, PRE_END, MIN_PRE_YEARS))
    universo, det = load_aigs()
    dsp, names, dsp_cols = load_dsp()
    vdem = load_vdem()
    header, rows = build(universo, det, dsp, names, dsp_cols, vdem)
    summarize(header, rows)
    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    with io.open(os.path.join(LOGS, "panel_%s.log" % stamp), "w",
                 encoding="utf-8") as fh:
        fh.write("\n".join(_log) + "\n")
    log("=== fin ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
