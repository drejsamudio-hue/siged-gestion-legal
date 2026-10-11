import pytest

from cartera import Causa, normalizar_expte
from cartera_alta import agregar, compilar_patron, escanear, expte_en_nombre, parsear_lista


def _e(texto):
    return normalizar_expte(texto)


def test_lista_acepta_varios_formatos_y_separa_las_invalidas():
    texto = "111111/2022\n222222/2023 ROBLES c/ SOSA s/ Daños\n333333 / 2021; PAZ c/ RUIZ\n\nabc\n44/1900\n"
    items, invalidas = parsear_lista(texto)
    assert [(e.clave, c) for e, c in items] == [
        ("111111/2022", None), ("222222/2023", "ROBLES c/ SOSA s/ Daños"), ("333333/2021", "PAZ c/ RUIZ")]
    assert invalidas == ["abc", "44/1900"]


def test_agregar_no_pisa_repetidas_y_evita_carpetas_iguales():
    existente = Causa(expte=_e("111111/2022"), caratula="ROBLES c/ SOSA", carpeta="2022-robles-sosa")
    items = [(_e("111111/2022"), "OTRA"), (_e("222222/2022"), "ROBLES c/ SOSA"), (_e("333333/2022"), None)]
    todas, r = agregar([existente], items, "lista")
    assert r == {"agregadas": ["222222/2022", "333333/2022"], "repetidas": ["111111/2022"]}
    nuevas = {c.expte.clave: c for c in todas[1:]}
    assert nuevas["222222/2022"].carpeta_prevista == "2022-robles-sosa-222222"
    assert nuevas["333333/2022"].carpeta_prevista == "2022-expte-333333-2022"
    assert nuevas["222222/2022"].fuentes == ["lista"] and todas[0].caratula == "ROBLES c/ SOSA"


@pytest.mark.parametrize("nombre,esperado", [
    ("Expte 123456-2022 cedula", "123456/2022"),
    ("escrito_45678_2021", "45678/2021"),
    ("12-05-2023 audiencia", None),
    ("foto 2023-05-12", None),
    ("sin numero", None),
])
def test_expte_en_nombre_evita_fechas(nombre, esperado):
    e = expte_en_nombre(nombre)
    assert (e.clave if e else None) == esperado


def test_patron_propio_y_validacion():
    rx = compilar_patron(r"EXP(\d+)\.(\d{4})")
    assert expte_en_nombre("EXP987.2020 sentencia", rx).clave == "987/2020"
    for malo in (r"(\d+", "sin grupos", "x" * 201):
        with pytest.raises(ValueError):
            compilar_patron(malo)


def test_escanear_por_carpeta_y_archivo_sin_tocar_nada(tmp_path):
    (tmp_path / "Causa 111111-2022").mkdir()
    (tmp_path / "Causa 111111-2022" / "escrito.txt").write_text("x", encoding="utf-8")
    (tmp_path / "Causa 111111-2022" / "otro.txt").write_text("x", encoding="utf-8")
    (tmp_path / "suelto_222222_2023.pdf").write_text("x", encoding="utf-8")
    (tmp_path / "nada.txt").write_text("x", encoding="utf-8")
    antes = sorted(p.name for p in tmp_path.rglob("*"))
    r = escanear(tmp_path, claves_en_cartera={"222222/2023"})
    por = {c["expte"]: c for c in r["causas"]}
    assert por["111111/2022"]["archivos"] == 2 and por["111111/2022"]["origen"] == "carpeta"
    assert por["222222/2023"]["en_cartera"] is True and por["222222/2023"]["origen"] == "archivo"
    assert r["revisados"] == 4 and not r["truncado"]
    assert sorted(p.name for p in tmp_path.rglob("*")) == antes


def test_escanear_respeta_las_fuentes_y_la_profundidad(tmp_path):
    hondo = tmp_path / "a" / "b" / "c"
    hondo.mkdir(parents=True)
    (hondo / "doc 111111-2022.txt").write_text("x", encoding="utf-8")
    assert escanear(tmp_path, fuentes=("carpeta",))["causas"] == []
    assert escanear(tmp_path, fuentes=("archivo",), profundidad=2)["causas"] == []
    assert len(escanear(tmp_path, fuentes=("archivo",))["causas"]) == 1


def test_escanear_por_texto_toma_expediente_y_caratula(tmp_path):
    (tmp_path / "escrito.txt").write_text(
        "Expte. N° 345678/2022 - ROBLES MARCOS c/ SOSA LUIS s/ Daños y perjuicios. " * 3, encoding="utf-8")
    r = escanear(tmp_path, fuentes=("texto",))
    assert [c["expte"] for c in r["causas"]] == ["345678/2022"] and r["causas"][0]["origen"] == "texto"
