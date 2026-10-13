from cartera import Causa, Expte, cargar, fusionar, guardar, normalizar_expte, posibles_erratas


def test_normaliza_formatos_de_siged():
    assert normalizar_expte("123456/2022") == Expte(123456, 2022)
    e = normalizar_expte("123456/2022 (EX 12/2013)")
    assert (e.numero, e.anio, e.ex) == (123456, 2022, "12/2013")
    e = normalizar_expte("111112/2023 bis1/24")
    assert (e.bis, e.bis_anio, e.clave_completa) == (1, 24, "111112/2023 bis1/24")
    assert normalizar_expte("111112-2023 bis1-2024").clave_completa == "111112/2023 bis1/24"


def test_normaliza_formato_de_la_lista_manual():
    assert normalizar_expte("123456-2024") == Expte(123456, 2024)


def test_rechaza_lo_que_no_es_un_numero():
    assert normalizar_expte("990011-15") is None
    assert normalizar_expte("hola") is None
    assert normalizar_expte("123/1850") is None


def test_numero_de_siete_digitos_es_sospechoso():
    assert normalizar_expte("7654321-2024").sospechoso
    assert not normalizar_expte("765432/2024").sospechoso


def test_fusionar_completa_datos_y_suma_fuentes():
    a = Causa(Expte(111111, 2022), id_expediente="900", fuentes=["otra"])
    b = Causa(Expte(111111, 2022, ex="5/2010"), caratula="PEREZ c/ GOMEZ", fuentes=["propios-txt"])
    c = Causa(Expte(111111, 2022, bis=1, bis_anio=23), fuentes=["propios-txt"])
    out = fusionar([a, b, c])
    assert len(out) == 2
    principal = out[0]
    assert (principal.id_expediente, principal.caratula, principal.expte.ex) == ("900", "PEREZ c/ GOMEZ", "5/2010")
    assert principal.fuentes == ["otra", "propios-txt"]


def test_detecta_errata_de_un_digito():
    causas = [Causa(normalizar_expte("123450/2022")), Causa(normalizar_expte("123460/2022")),
              Causa(normalizar_expte("123450/2021"))]
    assert posibles_erratas(causas) == [("123450/2022", "123460/2022")]


def test_guardar_y_cargar_es_reversible(tmp_path):
    c = Causa(normalizar_expte("123456/2022 (EX 12/2013)"), id_expediente="77", carpeta="2022-perez-gomez",
              fuentes=["a"])
    ruta = tmp_path / "cartera.json"
    guardar([c], ruta)
    assert cargar(ruta) == [c]
    assert cargar(tmp_path / "no-existe.json") == []


def test_guardar_no_deja_el_archivo_a_medias_si_falla(tmp_path, monkeypatch):
    import os
    import cartera as C
    ruta = tmp_path / "cartera.json"
    C.guardar([C.Causa(C.normalizar_expte("111111/2022"), caratula="PEREZ c/ GOMEZ")], ruta)
    antes = ruta.read_text(encoding="utf-8")

    def falla(*a, **k):
        raise OSError("disco lleno")
    monkeypatch.setattr(os, "replace", falla)
    try:
        C.guardar([], ruta)
    except OSError:
        pass
    assert ruta.read_text(encoding="utf-8") == antes
    assert [p.name for p in tmp_path.iterdir()] == ["cartera.json"]
