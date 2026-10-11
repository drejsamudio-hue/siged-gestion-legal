from cartera import Causa, normalizar_expte
from cartera_cruce import Cruce, aplicar, carpetas_sin_causa, cruzar, nombre_carpeta, reporte_md


def causa(numero, caratula=None, **kw):
    return Causa(normalizar_expte(numero), caratula=caratula, **kw)


def test_nombre_carpeta_desde_caratula():
    assert nombre_carpeta(causa("111111/2022", "PEREZ JUAN c/ GOMEZ SA s/ Danos")) == "2022-perez-juan-gomez"
    assert nombre_carpeta(causa("111111/2019", "PAZ c/ MORENO — Daños y Perjuicios")) == "2019-paz-moreno"
    assert nombre_carpeta(causa("111111/2017", "PEREYRA LUNA s/ SUCESORIO")) == "2017-pereyra-luna-sucesorio"
    assert nombre_carpeta(causa("111111/2024")) == "2024-expte-111111-2024"


def armar(tmp_path, *carpetas):
    casos = tmp_path / "01_Expedientes"
    for nombre in carpetas:
        (casos / nombre / "01_siged").mkdir(parents=True)
    return casos


def test_cruce_clasifica_ok_crear_renombrar_revisar(tmp_path):
    casos = armar(tmp_path, "2022-perez-gomez", "2019-expte-222222-2019", "2020-otra-causa")
    causas = [
        causa("111111/2022", "PEREZ c/ GOMEZ"),
        causa("222222/2019", "PAZ c/ MORENO"),
        causa("333333/2021", "VIDAL c/ LUNA"),
        causa("7654321/2024"),
    ]
    mapa = {"111111/2022": "2022-perez-gomez"}
    cruces = {x.causa.expte.clave: x for x in cruzar(causas, casos, mapa)}
    assert (cruces["111111/2022"].accion, cruces["111111/2022"].via) == ("ok", "mapa")
    assert (cruces["222222/2019"].accion, cruces["222222/2019"].destino) == ("renombrar", "2019-paz-moreno")
    assert (cruces["222222/2019"].via, cruces["222222/2019"].carpeta) == ("nombre", "2019-expte-222222-2019")
    assert (cruces["333333/2021"].accion, cruces["333333/2021"].destino) == ("crear", "2021-vidal-luna")
    assert cruces["7654321/2024"].accion == "revisar"
    assert carpetas_sin_causa(casos, list(cruces.values())) == ["2020-otra-causa"]


def test_bis_existente_dentro_del_principal_queda_ok(tmp_path):
    casos = armar(tmp_path, "2023-perez-gomez")
    (casos / "2023-perez-gomez" / "bis1-24").mkdir()
    causas = [causa("111112/2023", "PEREZ c/ GOMEZ"), causa("111112/2023 bis1/24", "PEREZ c/ GOMEZ")]
    cruces = cruzar(causas, casos, {"111112/2023": "2023-perez-gomez"})
    assert [x.accion for x in cruces] == ["ok", "ok"]
    assert [x.carpeta for x in cruces] == ["2023-perez-gomez", "2023-perez-gomez/bis1-24"]


def test_carpeta_prevista_ya_creada_se_adopta_y_su_bis_va_adentro(tmp_path):
    casos = armar(tmp_path, "2024-vidal-luna")
    causas = [causa("111111/2024", "VIDAL c/ LUNA", carpeta_prevista="2024-vidal-luna"),
              causa("111111/2024 bis1/25", "VIDAL c/ LUNA")]
    cruces = cruzar(causas, casos, {})
    assert [(x.accion, x.via) for x in cruces] == [("ok", "prevista"), ("crear", "principal")]
    assert cruces[0].carpeta == "2024-vidal-luna"
    assert cruces[1].destino == "2024-vidal-luna/bis1-25"


def test_aplicar_crea_renombra_y_registra(tmp_path):
    casos = armar(tmp_path, "2019-expte-222222-2019")
    causas = [causa("222222/2019", "PAZ c/ MORENO"), causa("333333/2021", "VIDAL c/ LUNA")]
    cruces = cruzar(causas, casos, {})
    log = tmp_path / "aplicado.csv"
    hechos, conflictos = aplicar(cruces, casos, log)
    assert conflictos == []
    assert sorted(h[0] for h in hechos) == ["crear", "renombrar"]
    assert (casos / "2019-paz-moreno" / "01_siged").is_dir()
    assert not (casos / "2019-expte-222222-2019").exists()
    assert (casos / "2021-vidal-luna" / "00_escritos_propios").is_dir()
    assert [c.carpeta for c in causas] == ["2019-paz-moreno", "2021-vidal-luna"]
    assert len(log.read_text(encoding="utf-8").splitlines()) == 3


def test_aplicar_no_fusiona_si_el_destino_existe(tmp_path):
    casos = armar(tmp_path, "2019-expte-222222-2019", "2019-paz-moreno")
    cruces = cruzar([causa("222222/2019", "PAZ c/ MORENO")], casos, {})
    hechos, conflictos = aplicar(cruces, casos, tmp_path / "aplicado.csv")
    assert hechos == []
    assert conflictos == [("2019-expte-222222-2019", "2019-paz-moreno", "el destino ya existe")]
    assert (casos / "2019-expte-222222-2019").is_dir()


def test_reporte_menciona_cada_grupo(tmp_path):
    casos = armar(tmp_path, "2020-otra-causa")
    cruces = cruzar([causa("333333/2021", "VIDAL c/ LUNA")], casos, {})
    md = reporte_md(cruces, carpetas_sin_causa(casos, cruces), [("123450/2022", "123460/2022")], ["990011-15"])
    assert "`2021-vidal-luna`" in md
    assert "123450/2022 vs 123460/2022" in md
    assert "`990011-15`" in md
    assert "no estan en la cartera: **1**" in md


def test_cruzar_revisar_si_la_carpeta_propuesta_existe(tmp_path):
    casos = armar(tmp_path, "2021-vidal-luna")
    c = causa("333333/2021", "VIDAL c/ LUNA")
    cruces = cruzar([c], casos, {})
    assert len(cruces) == 1
    assert cruces[0].accion == "revisar"
    assert "ya existe una carpeta con ese nombre que no corresponde al numero" in cruces[0].nota


def test_aplicar_conflicto_si_destino_existe_en_crear(tmp_path):
    casos = armar(tmp_path, "2021-vidal-luna")
    c = causa("333333/2021", "VIDAL c/ LUNA")
    cruce = Cruce(c, None, "sin_carpeta", "crear", "2021-vidal-luna")
    hechos, conflictos = aplicar([cruce], casos, tmp_path / "aplicado.csv")
    assert hechos == []
    assert conflictos == [("", "2021-vidal-luna", "ya existe una carpeta con ese nombre")]
    assert c.carpeta is None


def test_principal_y_bis_crean_una_carpeta_juntos(tmp_path):
    casos = tmp_path / "01_Expedientes"
    casos.mkdir()
    causas = [causa("111112/2023", "PEREZ c/ GOMEZ"), causa("111112/2023 bis1/24", "PEREZ c/ GOMEZ")]
    cruces = cruzar(causas, casos, {})
    assert [x.accion for x in cruces] == ["crear", "crear"]
    assert [x.destino for x in cruces] == ["2023-perez-gomez", "2023-perez-gomez/bis1-24"]
    hechos, conflictos = aplicar(cruces, casos, tmp_path / "aplicado.csv")
    assert conflictos == []
    assert sorted(h[0] for h in hechos) == ["crear", "crear"]
    assert (casos / "2023-perez-gomez" / "00_escritos_propios").is_dir()
    assert (casos / "2023-perez-gomez" / "bis1-24" / "01_siged").is_dir()
    assert [c.carpeta for c in causas] == ["2023-perez-gomez", "2023-perez-gomez/bis1-24"]


def test_log_append_per_operation(tmp_path):
    casos = armar(tmp_path, "2019-expte-222222-2019")
    log = tmp_path / "aplicado.csv"
    causas1 = [causa("222222/2019", "PAZ c/ MORENO")]
    cruces1 = cruzar(causas1, casos, {})
    hechos1, conflictos1 = aplicar(cruces1, casos, log)
    assert len(hechos1) == 1
    lineas1 = log.read_text(encoding="utf-8").splitlines()
    assert len(lineas1) == 2
    assert lineas1[0] == "fecha,accion,origen,destino"
    causas2 = [causa("333333/2021", "VIDAL c/ LUNA")]
    cruces2 = cruzar(causas2, casos, {})
    hechos2, conflictos2 = aplicar(cruces2, casos, log)
    assert len(hechos2) == 1
    lineas2 = log.read_text(encoding="utf-8").splitlines()
    assert len(lineas2) == 3
    assert lineas2[0] == "fecha,accion,origen,destino"


def test_cruzar_revisar_si_dos_expedientes_proponen_la_misma_carpeta(tmp_path):
    casos = tmp_path / "01_Expedientes"
    casos.mkdir()
    causas = [
        causa("111111/2022", "PEREZ c/ GOMEZ"),
        causa("222222/2022", "PEREZ c/ GOMEZ"),
    ]
    cruces = cruzar(causas, casos, {})
    assert cruces[0].accion == "crear"
    assert cruces[0].destino == "2022-perez-gomez"
    assert cruces[1].accion == "revisar"
    assert "otro expediente propone el mismo nombre de carpeta" in cruces[1].nota


def test_aplicar_conflicto_si_dos_expedientes_distintos_crean_mismo_destino(tmp_path):
    casos = tmp_path / "01_Expedientes"
    casos.mkdir()
    c1 = causa("111111/2022", "PEREZ c/ GOMEZ")
    c2 = causa("222222/2022", "PEREZ c/ GOMEZ")
    cruce1 = Cruce(c1, None, "sin_carpeta", "crear", "2022-perez-gomez")
    cruce2 = Cruce(c2, None, "sin_carpeta", "crear", "2022-perez-gomez")
    hechos, conflictos = aplicar([cruce1, cruce2], casos, tmp_path / "aplicado.csv")
    assert len(hechos) == 1
    assert hechos[0] == ("crear", "", "2022-perez-gomez")
    assert len(conflictos) == 1
    assert conflictos[0] == ("", "2022-perez-gomez", "otro expediente propone el mismo nombre")
    assert c1.carpeta == "2022-perez-gomez"
    assert c2.carpeta is None


def test_reporte_lista_las_asignaciones_ok_con_su_via(tmp_path):
    casos = armar(tmp_path, "2022-perez-gomez")
    cruces = cruzar([causa("111111/2022", "PEREZ c/ GOMEZ")], casos, {"111111/2022": "2022-perez-gomez"})
    md = reporte_md(cruces, [], [], [])
    assert "## Asignadas (recibiran archivos con confianza alta)" in md
    assert "- 111111/2022 -> `2022-perez-gomez` (mapa)" in md


def test_nombre_carpeta_con_guiones_en_la_caratula():
    assert nombre_carpeta(causa("111111/2025", "ROBLES MARCOS ANDRES C/ SERVICIOS DE AGUAS DEL SUR SA -SAS- S/ Sumarísimos")) == "2025-robles-marcos-andres-servicios-aguas-sur"
    assert nombre_carpeta(causa("111111/2024", "ROLDAN PEREYRA JUAN y Otro/a C/ AGUAS DEL ESTE SOCIEDAD ANONIMA -ADE- S/ Sumarísimos")) == "2024-roldan-pereyra-juan-aguas-este-sociedad"
    assert nombre_carpeta(causa("111111/2020", "PAZ TOMAS por SOSA LUIS C/ INTRUSOS Y OCUPANTES ILEGALES S/ Desalojo")) == "2020-paz-tomas-por-intrusos-ocupantes-ilegales"


def test_bis_va_en_subcarpeta_del_principal(tmp_path):
    casos = armar(tmp_path, "2023-perez-gomez")
    causas = [causa("111112/2023", "PEREZ c/ GOMEZ"), causa("111112/2023 bis1/24", "PEREZ c/ GOMEZ s/ Incidente")]
    cruces = cruzar(causas, casos, {"111112/2023": "2023-perez-gomez"})
    principal, bis = cruces
    assert (principal.accion, principal.carpeta) == ("ok", "2023-perez-gomez")
    assert (bis.accion, bis.destino) == ("crear", "2023-perez-gomez/bis1-24")


def test_bis_usa_el_nombre_nuevo_del_principal_y_se_crea_despues_del_renombrado(tmp_path):
    casos = armar(tmp_path, "2019-expte-222222-2019")
    causas = [causa("222222/2019 bis2/20", "PAZ c/ MORENO s/ Embargo"), causa("222222/2019", "PAZ c/ MORENO")]
    cruces = cruzar(causas, casos, {})
    bis = next(x for x in cruces if x.causa.expte.bis)
    assert bis.destino == "2019-paz-moreno/bis2-20"
    hechos, conflictos = aplicar(cruces, casos, tmp_path / "aplicado.csv")
    assert conflictos == []
    assert (casos / "2019-paz-moreno" / "bis2-20" / "01_siged").is_dir()
    assert (casos / "2019-paz-moreno" / "00_escritos_propios").is_dir()
    assert not (casos / "2019-expte-222222-2019").exists()
    assert [c.carpeta for c in causas] == ["2019-paz-moreno/bis2-20", "2019-paz-moreno"]


def test_bis_sin_principal_en_la_cartera_crea_ambas_carpetas(tmp_path):
    casos = armar(tmp_path)
    casos.mkdir(exist_ok=True)
    causas = [causa("333333/2021 bis1/22", "VIDAL c/ LUNA s/ Incidente")]
    cruces = cruzar(causas, casos, {})
    assert cruces[0].destino == "2021-vidal-luna/bis1-22"
    aplicar(cruces, casos, tmp_path / "aplicado.csv")
    assert (casos / "2021-vidal-luna" / "00_escritos_propios").is_dir()
    assert (casos / "2021-vidal-luna" / "bis1-22" / "00_escritos_propios").is_dir()


def test_bis_con_principal_en_revision_va_a_revisar(tmp_path):
    casos = armar(tmp_path)
    casos.mkdir(exist_ok=True)
    causas = [causa("7654321/2024"), causa("7654321/2024 bis1/25")]
    assert [x.accion for x in cruzar(causas, casos, {})] == ["revisar", "revisar"]


def test_carpetas_sin_causa_cuenta_la_carpeta_del_principal_de_un_bis(tmp_path):
    casos = armar(tmp_path, "2023-perez-gomez", "2020-otra-causa")
    cruces = cruzar([causa("111112/2023 bis1/24", "PEREZ c/ GOMEZ")], casos, {"111112/2023": "2023-perez-gomez"})
    assert carpetas_sin_causa(casos, cruces) == ["2020-otra-causa"]
