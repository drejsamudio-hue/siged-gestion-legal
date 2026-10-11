import json
import re

from cartera import Causa, cargar, guardar, normalizar_expte
from cartera_alias import aliases_desde_cartera
from cartera_cli import main


def armar_base(tmp_path):
    base = tmp_path / "SIGED"
    casos = base / "01_Expedientes"
    for nombre in ("2022-quiroga-juan-gomez", "2020-quiroga-pedro-lopez", "2021-vidal-luna", "2019-expte-222222-2019"):
        (casos / nombre / "01_siged").mkdir(parents=True)
    return base, casos


def test_alias_solo_para_apellidos_unicos(tmp_path):
    _, casos = armar_base(tmp_path)
    causas = [
        Causa(normalizar_expte("111111/2022"), carpeta="2022-quiroga-juan-gomez"),
        Causa(normalizar_expte("333333/2021"), carpeta="2021-vidal-luna"),
    ]
    aliases, ambiguos = aliases_desde_cartera(causas, casos)
    assert ambiguos == ["quiroga"]
    assert [a["caso"] for a in aliases] == ["2021-vidal-luna"]
    rx = re.compile(aliases[0]["pattern"], re.I)
    assert rx.search("escrito_vidal_contesta") and rx.search("Vidal2")
    assert not rx.search("vidalia") and not rx.search("svidal")


def test_flujo_completo_importar_cruzar_aliases(tmp_path):
    base, casos = armar_base(tmp_path)
    log = tmp_path / "justi.log"
    log.write_text("[1] 333333/2021 ✅ ANALIZADO\n    VIDAL c/ LUNA — Danos\n"
                   "[2] 222222/2019 ✅ ANALIZADO\n    PAZ c/ MORENO — Danos\n"
                   "[3] 999999/2024 ✅ ANALIZADO\n    NUEVO c/ CASO — Danos\n", encoding="utf-8")
    propios = tmp_path / "propios.txt"
    propios.write_text("333333-2021\n990011-15\n", encoding="utf-8")

    main(["--base", str(base), "importar", "--log", str(log), "--propios", str(propios)], mapa={})
    causas = cargar(base / "_SISTEMA" / "cartera.json")
    assert [c.expte.clave for c in causas] == ["333333/2021", "222222/2019", "999999/2024"]
    assert causas[0].fuentes == ["justi-log", "propios-txt"]

    main(["--base", str(base), "cruzar"], mapa={"333333/2021": "2021-vidal-luna"})
    assert not (casos / "2024-nuevo-caso").exists()
    informe = (base / "_SISTEMA" / "CARTERA_CRUCE.md").read_text(encoding="utf-8")
    assert "`2024-nuevo-caso`" in informe and "`990011-15`" in informe
    assert cargar(base / "_SISTEMA" / "cartera.json")[0].carpeta == "2021-vidal-luna"
    assert (casos / "2019-expte-222222-2019").exists()

    main(["--base", str(base), "cruzar", "--aplicar"], mapa={"333333/2021": "2021-vidal-luna"})
    assert (casos / "2024-nuevo-caso" / "00_escritos_propios").is_dir()
    assert (casos / "2019-paz-moreno").is_dir() and not (casos / "2019-expte-222222-2019").exists()

    main(["--base", str(base), "aliases"], mapa={})
    aliases = json.loads((base / "_SISTEMA" / "aliases_cartera.json").read_text(encoding="utf-8"))["aliases"]
    assert {a["caso"] for a in aliases} == {"2021-vidal-luna", "2024-nuevo-caso"}  # "paz" tiene menos de 5 letras


def test_alias_omite_apellidos_de_menos_de_cinco_letras(tmp_path):
    casos = tmp_path / "01_Expedientes"
    for nombre in ("2022-diaz-luna", "2021-vidal-luna"):
        (casos / nombre).mkdir(parents=True)
    causas = [
        Causa(normalizar_expte("111111/2022"), carpeta="2022-diaz-luna"),
        Causa(normalizar_expte("333333/2021"), carpeta="2021-vidal-luna"),
    ]
    aliases, _ = aliases_desde_cartera(causas, casos)
    assert [a["caso"] for a in aliases] == ["2021-vidal-luna"]


def test_quitar_saca_causas_de_la_cartera_y_avisa_de_las_desconocidas(tmp_path, capsys):
    base, _ = armar_base(tmp_path)
    ruta = base / "_SISTEMA" / "cartera.json"
    guardar([Causa(normalizar_expte("111111/2022")), Causa(normalizar_expte("111111/2022 bis1/24")),
             Causa(normalizar_expte("333333/2021"))], ruta)

    main(["--base", str(base), "quitar", "111111/2022", "111111-2022 bis1/24", "555555/2020", "basura"], mapa={})

    assert [c.expte.clave_completa for c in cargar(ruta)] == ["333333/2021"]
    salida = capsys.readouterr().out
    assert "555555/2020" in salida and "basura" in salida
    assert "Quitadas: 2" in salida


def test_quitar_no_toca_la_cartera_si_no_hay_coincidencias(tmp_path):
    base, _ = armar_base(tmp_path)
    ruta = base / "_SISTEMA" / "cartera.json"
    guardar([Causa(normalizar_expte("333333/2021"))], ruta)
    antes = ruta.read_text(encoding="utf-8")
    main(["--base", str(base), "quitar", "444444/2020"], mapa={})
    assert ruta.read_text(encoding="utf-8") == antes


def test_alias_de_un_bis_apunta_al_principal(tmp_path):
    _, casos = armar_base(tmp_path)
    causas = [Causa(normalizar_expte("333333/2021 bis1/22"), carpeta="2021-vidal-luna/bis1-22")]
    aliases, _ = aliases_desde_cartera(causas, casos)
    assert [a["caso"] for a in aliases] == ["2021-vidal-luna"]


def test_cruzar_guarda_la_carpeta_prevista_y_sin_crear_solo_renombra(tmp_path):
    base, casos = armar_base(tmp_path)
    log = tmp_path / "justi.log"
    log.write_text("[1] 222222/2019 ✅ ANALIZADO\n    PAZ c/ MORENO — Danos\n"
                   "[2] 999999/2024 ✅ ANALIZADO\n    NUEVO c/ CASO — Danos\n", encoding="utf-8")
    main(["--base", str(base), "importar", "--log", str(log)], mapa={})
    main(["--base", str(base), "cruzar"], mapa={})
    causas = {c.expte.clave: c for c in cargar(base / "_SISTEMA" / "cartera.json")}
    assert causas["999999/2024"].carpeta_prevista == "2024-nuevo-caso"
    assert causas["222222/2019"].carpeta_prevista is None
    assert causas["222222/2019"].carpeta == "2019-expte-222222-2019"

    main(["--base", str(base), "cruzar", "--aplicar", "--sin-crear"], mapa={})
    assert (casos / "2019-paz-moreno").is_dir() and not (casos / "2019-expte-222222-2019").exists()
    assert not (casos / "2024-nuevo-caso").exists()

    (casos / "2024-nuevo-caso" / "01_siged").mkdir(parents=True)  # creada a demanda por la ingesta
    main(["--base", str(base), "cruzar"], mapa={})
    causas = {c.expte.clave: c for c in cargar(base / "_SISTEMA" / "cartera.json")}
    assert (causas["999999/2024"].carpeta, causas["999999/2024"].carpeta_prevista) == ("2024-nuevo-caso", None)
    (casos / "2024-nuevo-caso" / "01_siged").rmdir()
    (casos / "2024-nuevo-caso").rmdir()
    causas["999999/2024"].carpeta, causas["999999/2024"].carpeta_prevista = None, None
    guardar(list(causas.values()), base / "_SISTEMA" / "cartera.json")

    main(["--base", str(base), "cruzar", "--aplicar"], mapa={})
    causas = {c.expte.clave: c for c in cargar(base / "_SISTEMA" / "cartera.json")}
    assert (casos / "2024-nuevo-caso").is_dir()
    assert (causas["999999/2024"].carpeta, causas["999999/2024"].carpeta_prevista) == ("2024-nuevo-caso", None)


def test_alias_omite_apellidos_comunes_y_palabras_institucionales(tmp_path):
    casos = tmp_path / "01_Expedientes"
    for nombre in ("2022-sanchez-luna", "2024-comisaria-decima", "2021-vidal-luna"):
        (casos / nombre).mkdir(parents=True)
    causas = [Causa(normalizar_expte(n), carpeta=c) for n, c in
              (("111111/2022", "2022-sanchez-luna"), ("222222/2024", "2024-comisaria-decima"), ("333333/2021", "2021-vidal-luna"))]
    aliases, _ = aliases_desde_cartera(causas, casos)
    assert [a["caso"] for a in aliases] == ["2021-vidal-luna"]
