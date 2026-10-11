from pathlib import Path

from doctrina import clasificar_doctrina, ruta_doctrina

BASE_LEGAL = ("El derecho aplicable, la ley y el articulo citado, segun la doctrina y la jurisprudencia del "
              "tribunal, en la sentencia sobre la responsabilidad del contrato. ")


def texto(*frases: str, repetir: int = 1) -> str:
    return BASE_LEGAL + (" ".join(frases) + " ") * repetir


def test_libro_de_planes_de_ahorro():
    t = texto("Indice general. Capitulo I. Los planes de ahorro y el grupo cerrado. La administradora del plan "
              "cobra la cuota pura y la adjudicacion se define por sorteo.", repetir=3)
    d = clasificar_doctrina(t, "Planes de ahorro - Tratado.pdf", paginas=320)
    assert (d.tipo, d.rama, d.especialidad, d.confianza) == ("libro", "consumo", "planes-de-ahorro", "alta")


def test_compendio_por_titulo():
    t = texto("Compendio de jurisprudencia laboral. Despido, preaviso e indemnizacion por antiguedad, "
              "contrato de trabajo.", repetir=2)
    d = clasificar_doctrina(t, "Compendio jurisprudencia laboral 2020.pdf", paginas=90)
    assert (d.tipo, d.rama) == ("compendio", "laboral")


def test_nota_a_fallo():
    t = texto("Nota a fallo. El dano punitivo del art. 52 bis y la multa civil.", repetir=2)
    d = clasificar_doctrina(t, "nota-fallo.pdf", paginas=8)
    assert (d.tipo, d.rama, d.especialidad) == ("nota", "consumo", "dano-punitivo")


def test_articulo_con_aparato_de_revista():
    t = texto("Resumen. Palabras clave: usucapion, posesion. La prescripcion adquisitiva y la usucapion "
              "exigen posesion continua.", repetir=2)
    d = clasificar_doctrina(t, "usucapion.pdf", paginas=22)
    assert (d.tipo, d.rama, d.especialidad) == ("articulo", "reales", "usucapion")


def test_pieza_breve_sin_aparato_es_nota():
    t = texto("La caducidad de instancia y la perencion exigen impulso procesal.", repetir=2)
    assert clasificar_doctrina(t, "apunte.docx", paginas=6).tipo == "nota"


def test_informe_institucional():
    t = texto("Informe final 2024 de la defensoria. Estadistica de causas.", repetir=2)
    assert clasificar_doctrina(t, "informe.pdf", paginas=40).tipo == "informe"


def test_documento_de_causa_no_es_doctrina():
    assert clasificar_doctrina(texto("contenido"), "123456-2022__user0000-id9999999.pdf", paginas=50) is None
    cabecera = "JUZGADO CIVIL Y COMERCIAL N 1 SECRETARIA 2. Autos: PEREZ c/ GOMEZ. " + BASE_LEGAL
    assert clasificar_doctrina(cabecera, "escrito.pdf", paginas=5) is None


def test_anexo_numerado_es_documento_de_causa():
    t = texto("Nota a fallo. El dano punitivo del art. 52 bis y la multa civil.", repetir=2)
    assert clasificar_doctrina(t, "anexo_0042.pdf", paginas=8) is None
    assert clasificar_doctrina(t, "Anexo 7.pdf", paginas=8) is None
    assert clasificar_doctrina(t, "anexos del dano punitivo.pdf", paginas=8) is not None


def test_documento_no_juridico_no_es_doctrina():
    manual = "Manual de servicio de la moto. Cambio de aceite, bujias y cilindrada del motor. " * 40
    assert clasificar_doctrina(manual, "manual-servicio.pdf", paginas=150) is None


def test_sin_especialidad_clara_va_a_general_con_confianza_baja():
    d = clasificar_doctrina(texto("Consideraciones generales."), "reflexiones.pdf", paginas=30)
    assert (d.rama, d.especialidad, d.confianza) == ("general", "sin-especialidad", "baja")


def test_paginas_desconocidas_se_estiman_por_el_texto():
    largo = texto("Los planes de ahorro y el grupo cerrado.", repetir=1200)
    assert clasificar_doctrina(largo, "obra.docx", paginas=0).tipo == "articulo"
    assert clasificar_doctrina(texto("Nota a fallo. Dano punitivo."), "n.md", paginas=0).tipo == "nota"


def test_ruta_de_destino():
    d = clasificar_doctrina(texto("Nota a fallo. Dano punitivo, art. 52 bis, multa civil.", repetir=3), "n.pdf", paginas=5)
    assert ruta_doctrina(d, Path("X:/SIGED")) == Path("X:/SIGED/03_Doctrina/consumo/dano-punitivo")


def test_nombre_con_guiones_cuenta_como_palabras():
    d = clasificar_doctrina(BASE_LEGAL + "Portada.", "LOPEZ-ROSAS-Historia-Constitucional-Argentina.pdf", paginas=694)
    assert (d.tipo, d.rama, d.especialidad, d.confianza) == ("libro", "constitucional", "historia-y-teoria", "media")


def test_tema_de_un_fallo():
    from doctrina import tema_de
    t = texto("Regulacion de honorarios conforme la ley XII N 4, base arancelaria y escala del arancel.", repetir=3)
    assert tema_de(t, "fallo honorarios.pdf") == ("honorarios", "regulacion-arancelaria")
    assert tema_de("Texto sin palabras de ninguna especialidad. " * 5, "fallo.pdf") == ("general", "sin-especialidad")
