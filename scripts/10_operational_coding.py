# -*- coding: utf-8 -*-
"""
Etapa 20m — Codificacion manual del estado operativo de los registros que
fijan la fecha de tratamiento (Supplementary Table 3; Revisor 2).

Protocolo (fijado antes de leer las fuentes):
  Implemented      la fuente informa de un sistema instalado, en uso,
                   desplegado o puesto en marcha (incluye pilotos en marcha)
  Contract         acuerdo firmado, venta, compra o adjudicacion, sin
                   evidencia de operacion
  Announcement     planes, negociaciones, memorandos, autorizacion legal o
                   anuncios de uso futuro
  Project          proyecto aprobado o en preparacion, sin contrato ni
                   operacion acreditados
  Retrospective    fuente posterior que describe un despliegue anterior y
                   permite fecharlo
  Not established  la fuente no es accesible, no menciona al pais o no
                   documenta un despliegue estatal; no se infiere nada

Base de la clasificacion: texto completo de la fuente (original o Internet
Archive) o, si no es accesible, el resumen almacenado en la biblioteca
Zotero. Lectura realizada el 2026-10-12. Las citas son extractos breves.

Salida: outputs/results/codificacion_estado_operativo.csv

Uso:  python scripts/10_operational_coding.py
"""
import os
import pandas as pd
import common as rc

T, Z, N = "Full text", "Zotero abstract", "Source not accessible"
NE = "Not established"
COD = [
 ("Algeria", "TUWEI5I6", "Contract", "the equipment has been sold in recent years to the governments of Saudi Arabia, UAE, Oman, Qatar, Algeria and Morocco", "", T),
 ("Angola", "W3MBKK3B", NE, "Angola is not mentioned in the accessible part of the article (paywall)", "", T),
 ("Argentina", "QGKDNAPU", "Announcement", "representatives of Huawei met with Governor Alfredo Cornejo of the province of Mendoza ... to present new technological [solutions]", "", T),
 ("Argentina", "YIVVXZJ6", "Implemented", "The country's largest airport has installed a new system from Vision-Box that uses ABC eGates with biometric technology", "2018", T),
 ("Australia", "FSINPLYV", "Announcement", "The Australian Government will monitor social media in real time as part of a new initiative", "", T),
 ("Austria", "R8FMB3AS", "Implemented", "Vienna International Airport has installed 25 automated border control (ABC) eGates", "2017", T),
 ("Bahrain", "52YWFAA3", NE, "only states that a former police commissioner has been a consultant to the government of Bahrain since 2012", "", T),
 ("Bangladesh", "FAH3N9H2", "Implemented", "the authorities have monitored various platforms ... the government announced the formation of a nine-member monitoring cell", "2018", T),
 ("Belarus", "5KHAP2UE", "Contract", "X-Infotech and Emperor Technology won the tender to supply Belarus with the hardware and software ... biometric", "2020 (planned)", T),
 ("Belgium", "HP4L9MWG", "Announcement", "The police will soon begin using facial recognition cameras at Brussels Airport", "", Z),
 ("Bolivia", "XUZSQQST", NE, "Bolivia is not mentioned in the accessible abstract; full text not accessible", "", N),
 ("Botswana", "7A6VP6LX", "Implemented", "Huawei was assisting municipal authorities in Francistown ... with the installation of cameras; agreement with Botswana Police in November 2017", "2019 (installation); 2017 (agreement)", T),
 ("Brazil", "AYYT2DLV", "Implemented", "the Operations Center of the City of Rio ... Video streams in from subway stations and major intersections", "", T),
 ("Burma/Myanmar", "I5NPHY2M", "Announcement", "The regional government will sign a deal with Huawei next month to establish Mandalay as a 'Safe City'", "", T),
 ("Burma/Myanmar", "UEDJ3BGM", "Project", "a Safe City project designed in cooperation with Huawei was announced ... plans for the installation of Huawei CCTV monitoring systems", "", T),
 ("Cambodia", "YZWM2FRG", "Announcement", "China's Ministry of Public Security vows to help Cambodia install CCTV security cameras across the Kingdom", "", Z),
 ("Canada", "R53KK7ZH", "Implemented", "Passengers arriving at Ottawa can now verify their identity ... using new self-service border control kiosks", "2017", T),
 ("Canada", "U296CC97", "Implemented", "domestic law enforcement agencies in Canada and Australia are also using its technology", "", T),
 ("Canada", "YD2X3LUH", "Contract", "documents ... suggest Palantir counts Canada's federal government and Calgary Police among its customers", "", T),
 ("China", "SQQ2DGK5", NE, "multi-country academic review; full text not accessible (publisher bot check) and the abstract does not mention the country", "", N),
 ("Colombia", "2YWHFVX9", "Announcement", "Buscamos contribuir al desarrollo de Medellin a traves de la implementacion de nuevas tecnologias", "", T),
 ("Colombia", "SQQ2DGK5", NE, "multi-country academic review; full text not accessible (publisher bot check) and the abstract does not mention the country", "", N),
 ("Czechia", "LI8NHXIK", "Project", "The Czech government has approved the acquisition of a new security system that features facial recognition technology to be deployed", "", T),
 ("Denmark", "L6Q695DY", "Contract", "the Danish police and PET had purchased an intelligence-led policing platform from Palantir Technologies", "2016 (purchase)", T),
 ("Dominican Republic", "SX6NIS3P", "Announcement", "the Interior Police in Santo Domingo have announced new ballistics and firearm technology, which includes fingerprints and facial recognition", "", T),
 ("Ecuador", "XUZSQQST", "Implemented", "CEIEC helps countries build national security control centers. 'Ecuador is one of the most secure countries in Latin America'", "", Z),
 ("Egypt", "CL9KLZ7F", "Announcement", "Cairo Governor ... instructed local authorities ... to oversee the installation of surveillance cameras", "", T),
 ("France", "SQQ2DGK5", NE, "multi-country academic review; full text not accessible (publisher bot check) and the abstract does not mention the country", "", N),
 ("Georgia", "DWEH3K6X", "Implemented", "This surveillance system, which began operation in June ... 400 CCTV cameras were installed across major cities", "2017", T),
 ("Georgia", "KJGPNC5M", "Implemented", "The system began operation in June of this year, and works in combination with 400 CCTV surveillance cameras", "2017", T),
 ("Germany", "JNZPAB4R", "Contract", "set to begin work on the EasyPASS project, following a fresh contract award by the German Border Police", "2014 (planned)", T),
 ("Greece", "SQQ2DGK5", NE, "multi-country academic review; full text not accessible (publisher bot check) and the abstract does not mention the country", "", N),
 ("Hungary", "H4NLIIAA", "Implemented", "Lasting six months, trials are taking place in Hungary, Greece and Latvia (pilot)", "2018 (trial)", T),
 ("India", "I6PXX64J", "Implemented", "the Surat City Police Department started the 'Safe City Project'", "", Z),
 ("Indonesia", "4KQ7G2II", NE, "source not accessible and the stored abstract contains no information on the system", "", N),
 ("Iran", "YDW8MS3J", "Contract", "A Chinese telecommunications equipment company has sold Iran's largest tele[communications firm a surveillance system]", "", Z),
 ("Iraq", "QUILYR3V", "Announcement", "Iraqi Intelligence Service partner with Huawei to install facial recognition cameras across Baghdad as a trial", "", Z),
 ("Israel", "5U72SHKY", "Announcement", "visitors to Jerusalem's al-Aqsa mosque compound will soon be 'scanned by a facial-recognition surveillance system'", "", T),
 ("Italy", "SQQ2DGK5", NE, "multi-country academic review; full text not accessible (publisher bot check) and the abstract does not mention the country", "", N),
 ("Jamaica", "XBNED2D6", "Announcement", "Jamaica's Passport, Immigration and Citizenship Agency (PICA) is introducing a facial recognition component to its passport production", "", Z),
 ("Japan", "C74ZRYGQ", "Implemented", "ABC eGates are in use at four major airports - Narita, Haneda, Chubu Centrair and Kansai", "", T),
 ("Kazakhstan", "BAMG8FH9", "Implemented", "В Алматы тоже начали тестировать 'Сергек' (Almaty has also begun testing Sergek)", "2018 (testing)", Z),
 ("Kazakhstan", "F4VCF8FY", "Implemented", "Face recognition system launched in Astana administration building", "2018", T),
 ("Kazakhstan", "FN3YRKDZ", "Project", "Since 2017 the Kazakh Information and Communications Ministry has been elaborating the National information space automated monitoring project", "", Z),
 ("Kazakhstan", "VQKLVFB9", NE, "only listed among countries where Chinese firms are 'attracting customers'; no system described", "", T),
 ("Kenya", "8YXPW94G", "Contract", "The Integrated Public Safety Communication and Surveillance System being implemented by Safaricom ... would be completed within the next four months", "2014 (planned)", T),
 ("Kenya", "HV2CBBLI", "Contract", "Safaricom said on Tuesday it had signed a [security contract with the government]", "", Z),
 ("Kyrgyzstan", "VQKLVFB9", NE, "only listed among countries where Chinese firms are 'attracting customers'; no system described", "", T),
 ("Lebanon", "FVBM734L", "Implemented", "Completed last year, the $33 million project ... 2000 cameras ... both run around the clock", "2015", T),
 ("Malaysia", "UVGMNPLE", "Announcement", "launched the Royal Malaysian Police's Smart Lock-Up which is on display at the Defence Services Asia Exhibition", "", Z),
 ("Malaysia", "Y67UYU4E", "Announcement", "Authorities here are mooting predictive policing as a new means of curbing terrorism", "", Z),
 ("Mexico", "SQQ2DGK5", NE, "multi-country academic review; the accessible text mentions Mexico only in an author affiliation", "", T),
 ("Mexico", "VCNNNTDE", "Retrospective", "The C4I4 originated in 2001 as a pilot effort ... Mexico City has one of the world's most ambitious urban surveillance programs", "2001 (origin of the C4I4 centre)", T),
 ("Mongolia", "UBF2EAGF", NE, "academic paper on a face-recognition method using a Mongolian face database; no state deployment", "", Z),
 ("Morocco", "SQQ2DGK5", NE, "multi-country academic review; full text not accessible (publisher bot check) and the abstract does not mention the country", "", N),
 ("Namibia", "FSQQ22E8", "Implemented", "launched the police Automated Biometric Identification System (N-ABIS) ... includes ... automated facial recognition", "2016", T),
 ("Netherlands", "E5KKSVJB", "Announcement", "the City of Groningen has signed an MoU with Huawei, in a bid to explore the possibility of developing Groningen into a smart city", "", Z),
 ("New Zealand", "PHHLDDRU", "Retrospective", "the GCSB worked in 2012 and 2013 to implement a mass metadata surveillance system", "2012-2013 (implementation work)", T),
 ("North Korea", "JDB2BY3D", NE, "reports North Korean export of facial recognition products abroad; no domestic deployment documented", "", T),
 ("North Korea", "W3TRZDTW", NE, "reports a South Korean working with North Korean technicians on facial recognition; no deployment documented", "", T),
 ("Pakistan", "K38HQ3E2", "Implemented", "the first phase of Punjab Safe City Project had been completed in Lahore ... monitoring ... was being carried out on the screens", "2016", T),
 ("Panama", "SWTZIIXD", "Retrospective", "FaceFirst entered the transportation security sector at Panama's Tocumen International Airport ... The program was subsequently expanded", "", T),
 ("Papua New Guinea", "6VBJGHJI", "Announcement", "Papua New Guinea set to implement predictive policing software", "", Z),
 ("Paraguay", "VIYX5PX8", "Contract", "la empresa adjudicada para la implementacion del sistema es Seguridad, Vigilancia y Tecnologia del Paraguay", "", T),
 ("Peru", "FXFJWFPG", "Implemented", "The first stage was completed in 2016 with the deployment of an integrated monitoring and control platform ... six ABC eGates", "2016", T),
 ("Philippines", "JPIN35DY", "Contract", "IBM and the Davao City Government today announced an agreement to help the city scale-up its existing Public Safety and Security Command Center", "", T),
 ("Poland", "7TDQ5SZU", NE, "describes a plan by the German state of Saxony for the border region; no Polish deployment", "", T),
 ("Poland", "FR9FIP9S", "Contract", "Lithuania and Poland will soon be using secunet easygates at both countries' international airports", "", T),
 ("Qatar", "QUHWRLQA", "Implemented", "The 62 vb i-match eGates are now in use at Hamad", "2014", T),
 ("Romania", "XFFLCRWW", "Implemented", "Between 8 November - 15 December 2016 ... the functionality of the automated control gates at the border is being tested (pilot)", "2016 (pilot)", T),
 ("Russia", "EYERP9SI", "Implemented", "The Russian capital is using the technology ... in 5,000 cameras ... It has been in place for almost a year", "2016", T),
 ("Russia", "I4LF9DYS", "Implemented", "Over the past six years, the city has contracted with telecommunications operators to install more than 130,000 cameras", "", T),
 ("Russia", "RYHSQYJE", "Implemented", "Moscow uses NTechLab's system to identify criminal suspects across a network of 160,000 surveillance cameras", "", T),
 ("Russia", "VX8KL5MM", "Implemented", "Over 160,000 CCTV cameras have been connected to the face recognition system", "2017", T),
 ("Saudi Arabia", "SQQ2DGK5", NE, "multi-country academic review; full text not accessible (publisher bot check) and the abstract does not mention the country", "", N),
 ("Serbia", "6YNKBPG8", "Implemented", "hundreds of video cameras with the power to identify and track individuals started appearing in the streets of Belgrade", "", Z),
 ("Serbia", "BICGNFP5", "Implemented", "cameras with facial recognition and license-plate reading software, installed in about 800 locations around Belgrade", "", T),
 ("Serbia", "P4HJLBTA", "Implemented", "Since deployment of Serbia's first Safe City project, the Huawei Safe City Solution helps police solve cases", "", T),
 ("Singapore", "KRHU6C7C", "Implemented", "a one-year programme where private sector companies work with the Government to integrate advanced analytic capabilities into the existing video monitoring systems (pilot)", "2013 (pilot)", T),
 ("South Africa", "7FNNU96Y", NE, "academic article on Cape Town; full text not accessible and the abstract does not describe a specific system", "", N),
 ("South Korea", "BSUSL3TQ", "Implemented", "installing an ever-increasing number of close-circuit television cameras ... In 2013 South Korea had more than 565,00[0]", "", T),
 ("Spain", "Y6YLTMRJ", "Implemented", "The Automated Border Control systems at Madrid-Barajas and Barcelona-El Prat airports have been updated and improved", "", T),
 ("Sri Lanka", "GIJ6TGTN", NE, "reports a misidentification in a list of bombing suspects; the accessible text does not describe a surveillance system", "", T),
 ("Sweden", "NKC5SI7D", "Implemented", "At its core, the Security Project was an investment in Sweden's largest CCTV system", "", Z),
 ("Switzerland", "MNWASHUA", NE, "vendor profile; no Swiss deployment described in the accessible text", "", T),
 ("Taiwan", "7DP9CX4B", "Retrospective", "The e-gate system was opened to Taiwanese nationals in March 2011 and to foreign residents in September 2012", "2011", T),
 ("Tajikistan", "FICMJIZF", "Announcement", "parliamentarians passed legislation that grants the country's security services the right to monitor and control citizens' online activities", "", T),
 ("Thailand", "SV6MZZRB", "Announcement", "Megvii has appointed a distributor in Thailand and is negotiating ... the distributor has demonstrated Megvii's Face++ to police departments", "", T),
 ("Türkiye", "SQQ2DGK5", NE, "multi-country academic review; full text not accessible (publisher bot check) and the abstract does not mention the country", "", N),
 ("Uganda", "FS3T345H", "Implemented", "The government of Uganda has launched a program to verify the identities of the more than 1 million refugees ... with biometrics (fingerprints and iris)", "2018", T),
 ("Ukraine", "VQKLVFB9", "Implemented", "Huawei and HikVision installed 4,100 surveillance cameras in Kyiv ... Over 60 of the cameras ... have facial recognition capabilities", "", T),
 ("United Arab Emirates", "TUWEI5I6", "Contract", "the equipment has been sold in recent years to the governments of Saudi Arabia, UAE, Oman, Qatar, Algeria and Morocco", "", T),
 ("United Kingdom", "J8SXKDTW", "Implemented", "An obscure unit within London's Metropolitan Police Service has been monitoring ... almost 9,000 political campaigners ... using social media surveillance", "", T),
 ("United States of America", "5PK4UDCB", NE, "vendor marketing page; the archived page no longer describes a specific deployment", "", T),
 ("Uruguay", "KX66JQIB", "Implemented", "Montevideo's Carrasco International Airport has implemented self-service Automated Border Control", "2016", T),
 ("Uzbekistan", "N2YEJZCW", "Project", "Huawei Tech Investment Tashkent company is implementing a 'Safe tourism' pilot project in Bukhara city", "", Z),
 ("Uzbekistan", "VQKLVFB9", NE, "only listed among countries where Chinese firms are 'attracting customers'; no system described", "", T),
 ("Venezuela", "XUZSQQST", NE, "Venezuela is not mentioned in the accessible abstract; full text not accessible", "", N),
 ("Vietnam", "KK97KAMA", "Implemented", "Vietnam said ... it has set up a web monitoring unit that can scan up to 100 million news items per day", "2018", Z),
 ("Zambia", "G8LXKTSY", NE, "describes billboards for Chinese surveillance cameras and a Huawei-built data centre; no surveillance deployment by the state", "", T),
 ("Zambia", "PVYRIZID", "Implemented", "Employees embedded with cybersecurity forces in Uganda and Zambia intercepted encrypted communications and used cell data to track opponents", "", Z),
 ("Zimbabwe", "BQLMWUHV", "Announcement", "the police ... is due to introduce powerful night vision surveillance cameras across Harare", "", T),
]


def main():
    ev = pd.read_csv(os.path.join(rc.OUT, "evidencias_registro_datador.csv"))
    ev = ev[ev.rol == "tratado_datado"]
    c = pd.DataFrame(COD, columns=["country_name", "key", "estado_operativo", "evidencia_textual",
                                   "anio_despliegue_segun_fuente", "base_codificacion"])
    m = ev[["country_text_id", "country_name", "key"]].merge(c, on=["country_name", "key"],
                                                             how="outer", indicator=True)
    assert (m._merge == "both").all(), m[m._merge != "both"]
    assert len(m) == len(ev) == 102
    # El ano citado por la fuente no siempre es un ano de operacion: se separa
    # el ano (o periodo) de aquello a lo que se refiere.
    REF = [("planned", "Planned operation"), ("purchase", "Purchase"),
           ("agreement", "Agreement"), ("testing", "Pilot or test"),
           ("trial", "Pilot or test"), ("pilot", "Pilot or test"),
           ("origin", "Start of operation (origin of the system)"),
           ("installation", "Installation"),
           ("implementation", "Implementation work")]

    def separar(v):
        v = str(v).strip()
        if not v or v == "nan":
            return "", ""
        prim = v.split(";")[0].strip()
        anio = prim.split("(")[0].strip()
        q = prim[prim.find("(") + 1:prim.rfind(")")].lower() if "(" in prim else ""
        ref = next((r for k, r in REF if k in q), "Operation" if not q else q)
        if ";" in v:                       # p. ej. instalacion 2019; acuerdo 2017
            ref += "; " + "; ".join(x.strip() for x in v.split(";")[1:])
        return anio, ref

    m[["anio_mencionado", "referencia_anio"]] = m.anio_despliegue_segun_fuente.apply(
        lambda v: pd.Series(separar(v)))
    m["nota"] = ""
    m.loc[m.key == "UBF2EAGF", "nota"] = ("No URL in the library; identifier: "
                                          "doi:10.1109/ICISCE.2017.103 (ICISCE 2017). The "
                                          "title refers to the Mongol ethnic group "
                                          "('nationality'), not to a deployment by the state "
                                          "of Mongolia.")
    m.drop(columns="_merge").to_csv(os.path.join(rc.OUT, "codificacion_estado_operativo.csv"),
                                    index=False)
    print("filas codificadas:", len(m))
    print(m.estado_operativo.value_counts().to_string())
    print(m.base_codificacion.value_counts().to_string())
    # nivel país: mejor evidencia entre los registros que fijan la fecha
    orden = ["Implemented", "Retrospective", "Contract", "Project", "Announcement",
             "Not established"]
    m["rango"] = m.estado_operativo.map({k: i for i, k in enumerate(orden)})
    p = m.sort_values("rango").groupby("country_name").first()
    print("\nPAÍSES (81) según la mejor evidencia de sus registros datadores:")
    print(p.estado_operativo.value_counts().reindex(orden).to_string())
    p[["country_text_id", "estado_operativo"]].to_csv(
        os.path.join(rc.OUT, "estado_operativo_por_pais.csv"))


if __name__ == "__main__":
    main()
