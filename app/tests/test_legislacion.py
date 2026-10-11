from fase3_juris import BASE, clasificar

LEY_NACIONAL = (
    "Boletin Oficial de la Republica Argentina. Primera seccion. Legislacion y avisos oficiales.\n"
    "El Senado y Camara de Diputados de la Nacion Argentina reunidos en Congreso, etc. sancionan con fuerza de Ley:\n"
    "ARTICULO 1 - Objeto. La presente ley regula el analisis genetico humano. Las provincias, incluida Misiones, "
    "adhieren.\nARTICULO 2 - Comuniquese al Poder Ejecutivo nacional."
)
LEY_MISIONES = (
    "Digesto juridico. La Camara de Representantes de la Provincia de Misiones sanciona con fuerza de Ley:\n"
    "ARTICULO 1.- Crease el registro provincial.\nARTICULO 2.- Comuniquese al Poder Ejecutivo."
)
DECRETO = (
    "Decreto 70/2023. VISTO el expediente y CONSIDERANDO que resulta necesario. "
    "Por ello, EL PRESIDENTE DE LA NACION ARGENTINA DECRETA: ARTICULO 1 - Derogase la ley."
)
SENTENCIA = "VISTOS: estos autos. CONSIDERANDO: que el articulo 1 de la ley 24.240 se aplica. RESUELVE: hacer lugar."


def test_ley_con_encabezado_del_boletin_va_a_legislacion_nacional():
    assert clasificar(LEY_NACIONAL) == (BASE / "04_Legislacion" / "nacion", "legislacion_nacion")


def test_ley_provincial_va_a_misiones():
    assert clasificar(LEY_MISIONES) == (BASE / "04_Legislacion" / "misiones", "legislacion_misiones")


def test_decreto_con_vistos_y_considerando_es_legislacion():
    assert clasificar(DECRETO)[1] == "legislacion_nacion"


def test_sentencia_que_cita_un_articulo_no_es_legislacion():
    assert not clasificar(SENTENCIA)[1].startswith("legislacion")
