from cartera_fuentes import desde_escritorio, desde_log_justi, desde_propios_txt


def test_desde_escritorio():
    filas = [
        {"id_expediente": "900", "numero": {"texto": "123456/2022 (EX 12/2013)"},
         "designacion": "PEREZ c/ GOMEZ s/ Danos", "origen": "Juzgado Civil 1", "resaltado": True},
        {"id_expediente": "901", "numero": {"texto": "sin formato"}},
    ]
    out = desde_escritorio(filas)
    assert len(out) == 1
    assert (out[0].id_expediente, out[0].caratula, out[0].dependencia) == ("900", "PEREZ c/ GOMEZ s/ Danos", "Juzgado Civil 1")
    assert out[0].fuentes == ["justi-escritorio"]


LOG = """\
[1] 111111/2024 ✅ ANALIZADO
    Juzgado Civil y Comercial N° (Posadas)
    ALERTA: 🟡 SEGUIMIENTO
[2] 222222/2019 ✅ ANALIZADO
    PAZ c/ MORENO — Daños y Perjuicios
    Despacho 28/07/2026: Intima caducidad
[3] 333333/2022 (EX 12/2013) ✅ ANALIZADO
    ALERTA: Sin alertas urgentes
[EXTRA] 444444/2008 bis2/19 ✅ ANALIZADO
    SOSA c/ SUC. LEDESMA — Ejecución de Honorarios
    Estado: Ejecución — Orden de Pago / Embargo

RESUMEN DE ALERTAS
  • 222222/2019 (PAZ c/ MORENO) — Elevado a Cámara ayer.
"""


def test_desde_escritorio_repara_la_doble_codificacion_de_siged():
    filas = [{"id_expediente": "902", "numero": {"texto": "123456/2022"},
              "designacion": "PEÃ‘A c/ GÃ“MEZ s/ DaÃ±os", "origen": "Juzgado de GarantÃ\xadas"},
             {"id_expediente": "903", "numero": {"texto": "123457/2022"}, "designacion": "PEÑA c/ LUNA s/ Daños"}]
    a, b = desde_escritorio(filas)
    assert (a.caratula, a.dependencia) == ("PEÑA c/ GÓMEZ s/ Daños", "Juzgado de Garantías")
    assert b.caratula == "PEÑA c/ LUNA s/ Daños"


def test_desde_log_justi_toma_numero_y_caratula():
    out = {c.expte.clave_completa: c for c in desde_log_justi(LOG)}
    assert list(out) == ["111111/2024", "222222/2019", "333333/2022", "444444/2008 bis2/19"]
    assert out["111111/2024"].caratula is None
    assert out["222222/2019"].caratula == "PAZ c/ MORENO"
    assert out["333333/2022"].expte.ex == "12/2013"
    assert out["444444/2008 bis2/19"].caratula == "SOSA c/ SUC. LEDESMA"


def test_desde_propios_txt_separa_invalidas():
    txt = "# comentario\n\n123456-2024\n990011-15\n7654321-2024\n"
    causas, invalidas = desde_propios_txt(txt)
    assert [c.expte.clave for c in causas] == ["123456/2024", "7654321/2024"]
    assert invalidas == ["990011-15"]


def test_desde_escritorio_acepta_numero_como_texto_plano():
    out = desde_escritorio([{"id_expediente": "902", "numero": "123456/2022"}, {"numero": None}, {}])
    assert [c.expte.clave for c in out] == ["123456/2022"]
