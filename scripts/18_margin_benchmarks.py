# -*- coding: utf-8 -*-
"""
Referente empirico de los margenes de equivalencia (punto 5 del editor).

El editor pregunta por que un cuarto o un quinto de paso ordinal deberia
contar como un efecto medio despreciable, y si hay algun patron de referencia
que lo haga interpretable. No existe un estandar externo para las escalas
latentes del Digital Society Project, de modo que el margen es convencional.
Lo que si se puede dar es un referente medido dentro de los propios datos, y
es lo que calcula este script, por indicador:

  cuarto_sobre_sd      el cuarto de paso como fraccion de la desviacion tipica
                       entre paises, que es la escala en la que se interpretan
                       habitualmente las diferencias estandarizadas
  pct_mayores          porcentaje de los cambios interanuales dentro de un
                       mismo pais, en valor absoluto, que superan el cuarto de
                       paso; es decir, cuanto de inusual es un movimiento de
                       ese tamano en estas series
  mediana_cambio       mediana del cambio interanual absoluto

Los indicadores son codificaciones expertas y se mueven poco: la mediana del
cambio interanual es cero en los ocho. El referente debe leerse asi: un efecto
medio por debajo del margen es menor que la gran mayoria de los movimientos
anuales que estas series registran, no que sea despreciable en algun sentido
sustantivo establecido fuera de los datos.

Salida: results/referencia_margenes.csv
"""
import os
import pandas as pd
import common as rc

ESC = "escala_latente_ordinal.csv"


def main():
    esc = pd.read_csv(os.path.join(rc.OUT, ESC))
    pan = pd.read_csv(rc.PANEL)
    # la ventana de estimacion son los 158 paises que entran en las
    # comparaciones, no los 179 del panel integrado: con los 179 el recuento
    # de transiciones (3.920) excede el maximo posible de la muestra
    maestra = pd.read_csv(os.path.join(rc.OUT, "tabla_maestra_v2.csv"))
    est = set(maestra.country_text_id[maestra.rol.isin(
        ["tratado_datado", "control_limpio", "control_marcado"])])
    pan = pan[(pan.year >= 2000) & (pan.year <= 2022)
              & (pan.country_text_id.isin(est))]

    filas = []
    for _, r in esc.iterrows():
        v, paso, sd = r.variable, r.paso_medias, r.sd_entre_paises
        s = pan[["country_text_id", "year", v]].dropna()
        s = s.sort_values(["country_text_id", "year"])
        dif = s.groupby("country_text_id")[v].diff().dropna().abs()
        for nombre, frac in (("un cuarto", 4.0), ("un quinto", 5.0)):
            m = paso / frac
            filas.append(dict(
                variable=v, etiqueta=r.etiqueta, margen=nombre,
                paso_ordinal=paso, margen_latente=m,
                margen_sobre_sd_entre_paises=m / sd,
                pct_cambios_anuales_mayores=100.0 * (dif > m).mean(),
                mediana_cambio_anual=dif.median(),
                n_transiciones=int(len(dif))))

    d = pd.DataFrame(filas)
    sal = os.path.join(rc.OUT, "referencia_margenes.csv")
    d.to_csv(sal, index=False)

    for nombre in ("un cuarto", "un quinto"):
        g = d[d.margen == nombre]
        print("%s de paso: %.2f a %.2f de la DE entre paises; "
              "supera el %.1f%% a %.1f%% de los cambios interanuales"
              % (nombre, g.margen_sobre_sd_entre_paises.min(),
                 g.margen_sobre_sd_entre_paises.max(),
                 100 - g.pct_cambios_anuales_mayores.max(),
                 100 - g.pct_cambios_anuales_mayores.min()))
    print("mediana del cambio interanual absoluto: %.3f en los ocho indicadores"
          % d.mediana_cambio_anual.max())
    print("  -> referencia_margenes.csv")


if __name__ == "__main__":
    main()
