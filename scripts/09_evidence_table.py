# -*- coding: utf-8 -*-
"""
Etapa 20g — Tabla de evidencias pais a pais (R2).

Para cada adoptante documentado: el registro bibliografico que fija la fecha
de tratamiento bajo la regla principal (Ec. 1) y los siguientes registros con
etiqueta positiva, con titulo, fecha de publicacion, tipo, URL, tecnologia y
numero de paises que cubre el registro.

La columna `estado_operativo` queda VACIA a proposito: distinguir sistema
implantado / contrato / anuncio / proyecto / informe retrospectivo exige leer
la fuente original y se codifica a mano (etapa 20g-manual). No se rellena con
inferencias a partir del titulo.

Salidas: evidencias_por_pais.csv (todos los registros con etiqueta positiva),
         evidencias_registro_datador.csv (una fila por pais: el registro que
         fija la fecha), plantilla de codificacion en .xlsx si openpyxl esta
         disponible.

Uso:  python scripts/09_evidence_table.py
"""
import os
import numpy as np
import pandas as pd
import common as rc

L = rc.Log("20g_evidencias")


def main():
    L("=== 20g — tabla de evidencias ===")
    m = rc.maestra()
    at = pd.read_csv(os.path.join(rc.DATING, "atribuciones_item_pais.csv"))
    z = pd.read_csv(rc.ZOTERO)
    at = at.merge(z, on="key", how="left", suffixes=("", "_item"))
    at["tags"] = at.tags.fillna("")
    at["tecnologias"] = at.tags.apply(lambda s: ";".join(sorted(
        {rc.TAGS_VIG[t.strip()] for t in s.split("|") if t.strip() in rc.TAGS_VIG})))
    pos = at[(at.tecnologias != "") & at.year.notna() & (at.year >= 2005)].copy()
    ad = m[m.elegible & (m.aigs_adopter == 1)][["country_text_id", "country_name", "rol",
                                                rc.REGLA_PRINCIPAL]]
    ev = ad.merge(pos, on="country_name", how="left")
    ev["fija_la_fecha"] = ev.year == ev[rc.REGLA_PRINCIPAL]
    ev = ev.sort_values(["country_name", "year", "key"])
    ev["orden_en_pais"] = ev.groupby("country_name").cumcount() + 1
    cols = ["country_text_id", "country_name", "rol", rc.REGLA_PRINCIPAL, "orden_en_pais",
            "fija_la_fecha", "key", "year", "date", "itemType", "title", "url",
            "tecnologias", "n_paises_item", "tags"]
    ev = ev[cols].rename(columns={rc.REGLA_PRINCIPAL: "anio_tratamiento",
                                  "year": "anio_publicacion", "date": "fecha_publicacion",
                                  "itemType": "tipo", "title": "titulo",
                                  "tags": "etiquetas_zotero"})
    ev["estado_operativo"] = ""     # implantado | contrato | anuncio | proyecto | retrospectivo
    ev["evidencia_textual"] = ""    # cita breve de la fuente que justifica el estado
    ev["anio_despliegue_segun_fuente"] = ""
    ev.to_csv(os.path.join(rc.OUT, "evidencias_por_pais.csv"), index=False)
    dat = ev[ev.fija_la_fecha]
    dat.to_csv(os.path.join(rc.OUT, "evidencias_registro_datador.csv"), index=False)

    tr = ev[ev.rol == "tratado_datado"]
    L("  adoptantes datados: %d | registros con etiqueta positiva: %d"
      % (tr.country_name.nunique(), tr.key.notna().sum()))
    L("  registros que fijan la fecha: %d en %d países (empates en el mismo año: %d países)"
      % (len(dat[dat.rol == "tratado_datado"]), dat[dat.rol == "tratado_datado"].country_name.nunique(),
         int((dat[dat.rol == "tratado_datado"].groupby("country_name").size() > 1).sum())))
    L("  tipo de documento de los registros que fijan la fecha:")
    for k, v in dat[dat.rol == "tratado_datado"].tipo.value_counts().items():
        L("    %-22s %d" % (k, v))
    L("  registros datadores que cubren >1 país (informes multipaís): %d"
      % int((dat[dat.rol == "tratado_datado"].n_paises_item > 1).sum()))
    L("  registros datadores sin URL: %d" % int(dat[dat.rol == "tratado_datado"].url.isna().sum()))
    try:
        import openpyxl  # noqa
        with pd.ExcelWriter(os.path.join(rc.OUT, "codificacion_estado_operativo.xlsx")) as xw:
            dat.to_excel(xw, sheet_name="registro_datador", index=False)
            ev.to_excel(xw, sheet_name="todos_los_registros", index=False)
        L("  -> plantilla codificacion_estado_operativo.xlsx")
    except ImportError:
        L("  (openpyxl no disponible: plantilla solo en CSV)")
    L.cerrar()


if __name__ == "__main__":
    main()
