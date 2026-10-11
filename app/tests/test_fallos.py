from fallos import fichar

FONDO = (
    "SUPERIOR TRIBUNAL DE JUSTICIA DE LA PROVINCIA DE MISIONES. En la ciudad de Posadas, a los 12 dias del mes de "
    "marzo de 2023, en los autos \"PEREZ JUAN c/ GOMEZ SA s/ Danos y perjuicios\" Expte. N 123/2021. VISTOS Y "
    "CONSIDERANDO: que la relacion de consumo de la ley 24.240 y el art. 52 bis imponen el dano punitivo. "
    "Por ello, RESUELVE: hacer lugar al recurso y condenar a la demandada. " * 3
)
FORMAL = (
    "CAMARA DE APELACIONES EN LO CIVIL Y COMERCIAL, Sala II, Posadas, Misiones. Posadas, 05/06/2022. VISTOS: los "
    "autos \"LOPEZ ANA c/ SOSA LUIS s/ Ejecutivo\". CONSIDERANDO: que el recurso fue interpuesto el dia 20. "
    "Por ello, SE RESUELVE: declarar extemporaneo el recurso de apelacion interpuesto y rechazarlo. "
)


def test_ficha_de_un_fallo_de_fondo():
    f = fichar(FONDO, "fallo.pdf")
    assert f.tribunal == "stj_misiones" and f.fuerza.startswith("1-")
    assert f.fecha == "2023-03-12" and f.expte == "123/2021"
    assert "PEREZ JUAN" in f.caratula
    assert f.rama == "consumo" and "ley 24.240" in f.normas
    assert f.rechazo_formal == ""


def test_rechazo_por_extemporaneo_se_detecta_en_la_parte_resolutiva():
    f = fichar(FORMAL, "resolucion.pdf")
    assert f.rechazo_formal == "extemporaneo"
    assert f.sala == "II" and f.fecha == "2022-06-05"
    assert "extemporaneo" in f.evidencia


def test_mencionar_la_extemporaneidad_en_los_considerandos_no_basta():
    t = ("CAMARA DE APELACIONES, Posadas, Misiones. CONSIDERANDO: la demandada alega que la demanda seria "
         "extemporanea, lo que no es asi. Por ello, RESUELVE: hacer lugar a la demanda y condenar al pago. ")
    assert fichar(t, "x.pdf").rechazo_formal == ""


def test_desierto_un_recurso_pero_fondo_resuelto_en_otro_no_es_rechazo_llano():
    t = ("CAMARA DE APELACIONES, Posadas, Misiones. CONSIDERANDO: ... Por ello, RESUELVE: 1) declarar desierto el "
         "recurso de nulidad. 2) hacer lugar al recurso de apelacion y revocar la sentencia. ")
    assert fichar(t, "x.pdf").rechazo_formal == ""


def test_fallo_del_stj_que_cita_a_la_corte_es_del_stj():
    t = ("SUPERIOR TRIBUNAL DE JUSTICIA DE LA PROVINCIA DE MISIONES. Posadas, 3 de mayo de 2021. VISTOS. "
         "CONSIDERANDO: conforme la Corte Suprema de Justicia de la Nacion en Fallos 330:1. "
         "Por ello, el Superior Tribunal de Justicia RESUELVE: rechazar el recurso de inaplicabilidad. ")
    assert fichar(t, "x.pdf").tribunal == "stj_misiones"


def test_tribunal_superior_de_otra_provincia_no_es_el_stj_de_misiones():
    t = "TRIBUNAL SUPERIOR DE JUSTICIA DE CORDOBA. Sala Civil. Cordoba, 3 de mayo de 2021. RESUELVE: rechazar. "
    assert fichar(t, "x.pdf").tribunal == "tribunal_otra_jurisdiccion"
