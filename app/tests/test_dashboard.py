import json
import time
from pathlib import Path

import pytest

import dashboard as D
import ingesta as I
from cartera import Causa, guardar, normalizar_expte

CUERPO = "Providencia del juzgado. Se tiene presente lo manifestado por la parte y se ordena el traslado. " * 2


@pytest.fixture
def base(tmp_path, monkeypatch):
    b = tmp_path / "SIGED"
    for d in ("01_Expedientes/2022-perez-gomez/01_siged", "01_Expedientes/2023-vidal-luna/01_siged",
              "_INBOX", "_SISTEMA", "03_Doctrina/consumo/dano-punitivo"):
        (b / d).mkdir(parents=True)
    rutas = {"BASE": b, "INBOX": b / "_INBOX", "CASOS": b / "01_Expedientes", "SISTEMA": b / "_SISTEMA",
             "RUTEO_CSV": b / "_SISTEMA" / "INGESTA_RUTEO.csv", "TANDAS_CSV": b / "_SISTEMA" / "TANDAS.csv",
             "CARTERA_JSON": b / "_SISTEMA" / "cartera.json", "ALIAS_CARTERA": b / "_SISTEMA" / "aliases_cartera.json",
             "ALIAS_FILE": tmp_path / "sin_aliases.json"}
    for nombre, valor in rutas.items():
        monkeypatch.setattr(I, nombre, valor)
        if hasattr(D, nombre):
            monkeypatch.setattr(D, nombre, valor)
    monkeypatch.setattr(I, "_exptes_cache", None)
    monkeypatch.setattr(I, "_indice_cache", (-1.0, I.IndiceCartera([])))
    monkeypatch.setattr(D, "JUSTI_DIR", tmp_path / "justi")
    monkeypatch.setattr(D, "LOG_FILE", b / "_SISTEMA" / "dashboard_log.json")
    guardar([Causa(normalizar_expte("111111/2022"), id_expediente="555555", caratula="PEREZ c/ GOMEZ",
                   carpeta="2022-perez-gomez"),
             Causa(normalizar_expte("222222/2024"), caratula="LUNA c/ SOL", carpeta_prevista="2024-luna-sol")],
           b / "_SISTEMA" / "cartera.json")
    return b


@pytest.fixture
def cliente():
    return D.app.test_client()


def test_cartera_muestra_estado_y_carpetas(base, cliente):
    causas = {c["expte"]: c for c in cliente.get("/api/cartera").get_json()["causas"]}
    assert causas["111111/2022"]["existe"] and causas["111111/2022"]["accion"] == "ok"
    assert causas["222222/2024"]["prevista"] == "2024-luna-sol" and not causas["222222/2024"]["existe"]


def test_escritorio_marca_lo_que_falta_en_la_cartera(base, cliente, tmp_path):
    (tmp_path / "justi" / "2026-09-26").mkdir(parents=True)
    (tmp_path / "justi" / "2026-09-26" / "escritorio.json").write_text(json.dumps([
        {"id_expediente": "555555", "numero": {"texto": "111111/2022"}, "designacion": "PEREZ c/ GOMEZ"},
        {"id_expediente": "999999", "numero": {"texto": "333333/2023"}, "designacion": "PEÃ‘A c/ SOSA"},
    ]), encoding="utf-8")
    filas = cliente.get("/api/escritorio").get_json()["filas"]
    assert [f["en_cartera"] for f in filas] == [True, False]
    assert filas[1]["designacion"] == "PEÑA c/ SOSA"


def test_simular_revisar_aplicar_y_deshacer(base, cliente, tmp_path):
    origen = tmp_path / "descargas"
    origen.mkdir()
    (origen / "cedula 111111-2022.txt").write_text(CUERPO, encoding="utf-8")
    (origen / "otro 111111-2022.txt").write_text(CUERPO, encoding="utf-8")

    sim = cliente.post("/api/simular", json={"origen": str(origen)}).get_json()
    for _ in range(100):
        estado = cliente.get(f"/api/simular/{sim['id']}").get_json()
        if estado["estado"] != "corriendo":
            break
        time.sleep(0.05)
    assert estado["estado"] == "listo" and estado["total"] == 2

    assert cliente.get("/api/propuestas").get_json()[0]["nombre"] == sim["csv"]
    filas = cliente.get(f"/api/propuestas/{sim['csv']}").get_json()["filas"]
    assert all(f["causa"] == "2022-perez-gomez" for f in filas)
    corregida = str(base / "01_Expedientes" / "2023-vidal-luna" / "01_siged")
    for f in filas:
        if f["nombre"].startswith("otro"):
            f["accion"] = "queda"
        else:
            f["destino"] = corregida
    r = cliente.post(f"/api/propuestas/{sim['csv']}/aplicar", json={"filas": filas}).get_json()
    assert (r["movidos"], r["tanda"]) == (1, "t0001")
    assert (base / "01_Expedientes" / "2023-vidal-luna" / "01_siged" / "cedula 111111-2022.txt").exists()
    assert (origen / "otro 111111-2022.txt").exists()

    h = cliente.get("/api/historial").get_json()
    assert h["total_movimientos"] == 1 and h["tandas"][0]["id"] == "t0001"
    d = cliente.post("/api/tandas/deshacer", json={"primera": 0, "ultima": 0}).get_json()
    assert d["restaurados"] == 1 and (origen / "cedula 111111-2022.txt").exists()


def test_aplicar_rechaza_destinos_fuera_de_la_base_y_nombres_raros(base, cliente, tmp_path):
    (base / "_SISTEMA" / "REORG_x.csv").write_text("archivo,destino,motivo,detalle,confianza,accion\n", encoding="utf-8")
    fuera = [{"archivo": "a", "destino": str(tmp_path / "fuera"), "accion": "mover"}]
    assert cliente.post("/api/propuestas/REORG_x.csv/aplicar", json={"filas": fuera}).status_code == 400
    assert cliente.get("/api/propuestas/..%2Fcartera.json").status_code == 404
    assert cliente.post("/api/tandas/deshacer", json={"primera": 0, "ultima": 5}).status_code == 400


def test_soltar_copia_al_inbox_y_simula(base, cliente):
    import io
    datos = {"archivos": [(io.BytesIO(CUERPO.encode()), "cédula 111111-2022.txt"),
                          (io.BytesIO(b"x"), "../malo.txt")]}
    r = cliente.post("/api/soltar", data=datos, content_type="multipart/form-data").get_json()
    assert r["guardados"] == 2
    carpeta = base / "_INBOX" / "_soltados" / r["id"]
    assert sorted(p.name for p in carpeta.iterdir()) == ["cédula 111111-2022.txt", "malo.txt"]
    for _ in range(100):
        if cliente.get(f"/api/simular/{r['id']}").get_json()["estado"] != "corriendo":
            break
        time.sleep(0.05)
    filas = cliente.get(f"/api/propuestas/{r['csv']}").get_json()["filas"]
    assert any(f["causa"] == "2022-perez-gomez" for f in filas)


def test_aliases_de_la_cartera_se_muestran_aparte(base, cliente):
    (base / "_SISTEMA" / "aliases_cartera.json").write_text(
        json.dumps({"aliases": [{"pattern": "vidal", "caso": "2023-vidal-luna"}]}), encoding="utf-8")
    assert cliente.get("/api/aliases/cartera").get_json()[0]["caso"] == "2023-vidal-luna"


def test_carpetas_fuera_de_la_cartera_mia_y_ajena(base, cliente):
    ajena = base / "01_Expedientes" / "2009-ruiz-sosa" / "01_siged"
    ajena.mkdir(parents=True)
    (ajena / "fallo.txt").write_text("VISTOS Y CONSIDERANDO. RESUELVE: rechazar. Superior Tribunal de Justicia. " * 10,
                                     encoding="utf-8")
    nombres = [f["carpeta"] for f in cliente.get("/api/fuera").get_json()]
    assert "2009-ruiz-sosa" in nombres and "2023-vidal-luna" in nombres and "2022-perez-gomez" not in nombres
    assert cliente.post("/api/fuera/mia", json={"carpeta": "2023-vidal-luna"}).get_json()["ok"]
    assert "2023-vidal-luna" not in [f["carpeta"] for f in cliente.get("/api/fuera").get_json()]
    r = cliente.post("/api/fuera/ajena", json={"carpeta": "2009-ruiz-sosa"}).get_json()
    filas = cliente.get(f"/api/propuestas/{r['csv']}").get_json()["filas"]
    assert filas[0]["motivo"] == "jurisprudencia" and "02_Jurisprudencia" in filas[0]["destino"]
    assert cliente.post("/api/fuera/ajena", json={"carpeta": "../_SISTEMA"}).status_code == 404


def test_aplicar_rechaza_archivos_que_no_estan_en_la_simulacion(base, cliente, tmp_path):
    (base / "_SISTEMA" / "REORG_y.csv").write_text(
        "archivo,destino,motivo,detalle,confianza,accion\n", encoding="utf-8")
    ajeno = tmp_path / "ajeno.txt"
    ajeno.write_text("x", encoding="utf-8")
    filas = [{"archivo": str(ajeno), "destino": str(base / "01_Expedientes" / "2022-perez-gomez"), "accion": "mover"}]
    r = cliente.post("/api/propuestas/REORG_y.csv/aplicar", json={"filas": filas})
    assert r.status_code == 400 and ajeno.exists()


def test_post_con_origin_de_otro_sitio_se_rechaza(base, cliente):
    r = cliente.post("/api/tandas/deshacer", json={"primera": 0, "ultima": 0},
                     headers={"Origin": "http://sitio-ajeno.example"})
    assert r.status_code == 403
    r = cliente.post("/api/tandas/deshacer", json={"primera": 0, "ultima": 5},
                     headers={"Origin": "http://localhost"})
    assert r.status_code == 400


def _config_valida(tmp_path, **cambios):
    return {"estudio": "Estudio Prueba", "ubicacion": "Ciudad", "apellidos": "Robles, Marcos",
            "base": str(tmp_path / "mis-expedientes"), **cambios}


@pytest.fixture
def config_tmp(tmp_path, monkeypatch):
    import config as C
    monkeypatch.setattr(C, "CONFIG_PATH", tmp_path / "cfg" / "config.json")
    reinicios = []
    monkeypatch.setattr(D, "_reiniciar", lambda: reinicios.append(1))
    return C, reinicios


def test_config_sin_guardar_pide_configuracion(base, cliente, config_tmp):
    r = cliente.get("/api/config").get_json()
    assert r["configurado"] is False and r["estudio"] == ""


def test_config_guarda_crea_la_base_y_pide_reinicio(base, cliente, config_tmp, tmp_path):
    C, reinicios = config_tmp
    r = cliente.post("/api/config", json=_config_valida(tmp_path))
    assert r.status_code == 200 and reinicios == [1]
    guardado = json.loads(C.CONFIG_PATH.read_text(encoding="utf-8"))
    assert guardado["apellidos"] == ["robles", "marcos"] and guardado["estudio"] == "Estudio Prueba"
    assert (tmp_path / "mis-expedientes").is_dir()


@pytest.mark.parametrize("cambio", [
    {"estudio": ""}, {"apellidos": ""}, {"apellidos": "ro, 123"}, {"base": "relativa/carpeta"},
    {"base": ""}, {"estudio": "x" * 81},
])
def test_config_rechaza_datos_invalidos_sin_escribir(base, cliente, config_tmp, tmp_path, cambio):
    C, reinicios = config_tmp
    r = cliente.post("/api/config", json=_config_valida(tmp_path, **cambio))
    assert r.status_code == 400 and not C.CONFIG_PATH.exists() and reinicios == []


def test_config_rechaza_la_raiz_del_disco(base, cliente, config_tmp, tmp_path):
    raiz = Path(tmp_path.anchor)
    assert cliente.post("/api/config", json=_config_valida(tmp_path, base=str(raiz))).status_code == 400


def test_apellidos_del_entorno_pisan_a_los_del_archivo(monkeypatch):
    import config as C
    monkeypatch.setattr(C, "_CFG", {"apellidos": ["Robles", "Marcos"]})
    monkeypatch.delenv("ORGANIZADOR_APELLIDOS", raising=False)
    assert C._apellidos() == ("robles", "marcos")
    monkeypatch.setenv("ORGANIZADOR_APELLIDOS", "Sosa")
    assert C._apellidos() == ("sosa",)


def test_cartera_alta_manual_edicion_y_baja(base, cliente):
    r = cliente.post("/api/cartera", json={"expte": "333333/2023", "caratula": "ROBLES c/ SOSA s/ Daños"})
    assert r.status_code == 200 and r.get_json()["agregadas"] == ["333333/2023"]
    assert cliente.post("/api/cartera", json={"expte": "333333/2023"}).status_code == 409
    assert cliente.post("/api/cartera", json={"expte": "mal"}).status_code == 400

    fila = next(c for c in cliente.get("/api/cartera").get_json()["causas"] if c["expte"] == "333333/2023")
    assert fila["prevista"] == "2023-robles-sosa" and fila["fuentes"] == ["manual"]

    assert cliente.patch("/api/cartera", json={"expte": "333333/2023", "caratula": "PAZ c/ RUIZ s/ Cobro"}).status_code == 200
    fila = next(c for c in cliente.get("/api/cartera").get_json()["causas"] if c["expte"] == "333333/2023")
    assert fila["prevista"] == "2023-paz-ruiz"

    assert cliente.delete("/api/cartera", json={"expte": "333333/2023"}).status_code == 200
    assert cliente.delete("/api/cartera", json={"expte": "333333/2023"}).status_code == 404
    assert (base / "01_Expedientes" / "2022-perez-gomez").is_dir()


def test_cartera_alta_por_lista_informa_repetidas_e_invalidas(base, cliente):
    texto = "111111/2022\n555555/2024 LUNA c/ SOL\nxx\n"
    r = cliente.post("/api/cartera/lista", json={"texto": texto}).get_json()
    assert r["agregadas"] == ["555555/2024"] and r["repetidas"] == ["111111/2022"] and r["invalidas"] == ["xx"]
    assert cliente.post("/api/cartera/lista", json={"texto": "  "}).status_code == 400


def test_cartera_escanear_propone_y_agrega_solo_lo_elegido(base, cliente, tmp_path):
    origen = tmp_path / "mis_pdfs"
    (origen / "Causa 666666-2024").mkdir(parents=True)
    (origen / "Causa 666666-2024" / "a.txt").write_text("x", encoding="utf-8")
    (origen / "escrito 111111-2022.txt").write_text("x", encoding="utf-8")
    antes = cliente.get("/api/cartera").get_json()["causas"]
    ya = len(antes)
    r = cliente.post("/api/cartera/escanear", json={"carpeta": str(origen)}).get_json()
    por = {c["expte"]: c for c in r["causas"]}
    assert por["666666/2024"]["en_cartera"] is False and por["111111/2022"]["en_cartera"] is True
    assert cliente.get("/api/cartera").get_json()["causas"] == antes  # escanear no escribe

    a = cliente.post("/api/cartera/escanear/agregar", json={"causas": [{"expte": "666666/2024"}]}).get_json()
    assert a["agregadas"] == ["666666/2024"]
    assert len(cliente.get("/api/cartera").get_json()["causas"]) == ya + 1


def test_cartera_escanear_rechaza_carpeta_inexistente_patron_malo_y_sin_fuentes(base, cliente, tmp_path):
    assert cliente.post("/api/cartera/escanear", json={"carpeta": str(tmp_path / "no")}).status_code == 404
    assert cliente.post("/api/cartera/escanear", json={"carpeta": str(tmp_path), "patron": "(sin cerrar"}).status_code == 400
    assert cliente.post("/api/cartera/escanear", json={"carpeta": str(tmp_path), "fuentes": ["x"]}).status_code == 400


def test_tessdata_junto_al_exe_si_existe(tmp_path, monkeypatch):
    import config as C
    (tmp_path / "tessdata").mkdir()
    (tmp_path / "tessdata" / "spa.traineddata").write_bytes(b"x")
    monkeypatch.setattr(C, "CONFIG_PATH", tmp_path / "cfg" / "config.json")
    monkeypatch.setenv("USERPROFILE", str(tmp_path / "home"))
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setattr(C.sys, "frozen", True, raising=False)
    monkeypatch.setattr(C.sys, "executable", str(tmp_path / "Organizador.exe"))
    assert C._tessdata() == tmp_path / "tessdata"
    monkeypatch.setattr(C.sys, "frozen", False, raising=False)
    assert C._tessdata() == tmp_path / "cfg" / "tessdata"


# ── OCR: instalacion del idioma desde una fuente ────────────────────────────

@pytest.fixture
def espejo(tmp_path):
    """Servidor local que hace de repositorio de idiomas, para no tocar internet en los tests."""
    import functools
    import http.server
    import threading

    web = tmp_path / "web"
    web.mkdir()
    (web / "bueno.traineddata").write_bytes(b"x" * 600_000)
    (web / "chico.traineddata").write_bytes(b"x" * 1000)
    manejador = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(web))
    manejador.log_message = lambda *a, **k: None
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), manejador)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_address[1]}"
    srv.shutdown()


def test_ocr_instalar_descarga_y_deja_disponible(base, cliente, tmp_path, monkeypatch, espejo):
    import extractor
    carpeta = tmp_path / "tessdata_usuario"
    monkeypatch.setattr(extractor, "TESSDATA", carpeta)
    monkeypatch.setenv("ORGANIZADOR_TESSDATA_URL", f"{espejo}/bueno.traineddata")
    assert cliente.get("/api/ocr").get_json()["disponible"] is False
    r = cliente.post("/api/ocr/instalar", json={})
    assert r.status_code == 200 and r.get_json()["disponible"] is True
    assert (carpeta / "spa.traineddata").stat().st_size == 600_000
    assert not list(carpeta.glob("*.part"))


def test_ocr_instalar_rechaza_archivo_chico_y_no_deja_restos(base, cliente, tmp_path, monkeypatch, espejo):
    import extractor
    carpeta = tmp_path / "tessdata_usuario"
    monkeypatch.setattr(extractor, "TESSDATA", carpeta)
    monkeypatch.setenv("ORGANIZADOR_TESSDATA_URL", f"{espejo}/chico.traineddata")
    assert cliente.post("/api/ocr/instalar", json={}).status_code == 502
    assert not list(carpeta.glob("*"))
    monkeypatch.setenv("ORGANIZADOR_TESSDATA_URL", f"{espejo}/no-existe.traineddata")
    assert cliente.post("/api/ocr/instalar", json={}).status_code == 502


def test_ocr_instalar_no_pisa_uno_que_ya_funciona_si_la_descarga_falla(base, cliente, tmp_path, monkeypatch, espejo):
    import extractor
    carpeta = tmp_path / "tessdata_usuario"
    carpeta.mkdir()
    (carpeta / "spa.traineddata").write_bytes(b"previo")
    monkeypatch.setattr(extractor, "TESSDATA", carpeta)
    monkeypatch.setenv("ORGANIZADOR_TESSDATA_URL", f"{espejo}/chico.traineddata")
    assert cliente.post("/api/ocr/instalar", json={}).status_code == 502
    assert (carpeta / "spa.traineddata").read_bytes() == b"previo"


def test_ocr_solo_acepta_https_o_local():
    import ocr_setup
    with pytest.raises(ValueError):
        ocr_setup.instalar(Path("."), "http://sitio-ajeno.example/spa.traineddata")


def test_tessdata_prefiere_la_carpeta_del_usuario(tmp_path, monkeypatch):
    import config as C
    monkeypatch.setattr(C, "CONFIG_PATH", tmp_path / "cfg" / "config.json")
    monkeypatch.setenv("USERPROFILE", str(tmp_path / "home"))
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    assert C._tessdata() == tmp_path / "cfg" / "tessdata"
    (tmp_path / "home" / "tessdata").mkdir(parents=True)
    (tmp_path / "home" / "tessdata" / "spa.traineddata").write_bytes(b"x")
    assert C._tessdata() == tmp_path / "home" / "tessdata"
    (tmp_path / "cfg" / "tessdata").mkdir(parents=True)
    (tmp_path / "cfg" / "tessdata" / "spa.traineddata").write_bytes(b"x")
    assert C._tessdata() == tmp_path / "cfg" / "tessdata"


def test_ocr_huella_correcta_instala_y_distinta_rechaza(tmp_path, espejo):
    import hashlib
    import ocr_setup
    huella = hashlib.sha256(b"x" * 600_000).hexdigest()
    ok = ocr_setup.instalar(tmp_path / "a", f"{espejo}/bueno.traineddata", sha256=huella)
    assert ok.is_file()
    with pytest.raises(ValueError, match="huella"):
        ocr_setup.instalar(tmp_path / "b", f"{espejo}/bueno.traineddata", sha256="0" * 64)
    assert not list((tmp_path / "b").glob("*"))


def test_ocr_fuente_oficial_exige_la_huella_conocida(tmp_path, monkeypatch):
    import ocr_setup
    pedidos = []

    class Falsa:
        def __init__(self, datos):
            self.datos = datos

        def read(self, n):
            d, self.datos = self.datos[:n], self.datos[n:]
            return d

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    monkeypatch.setattr(ocr_setup.urllib.request, "urlopen",
                        lambda req, timeout: pedidos.append(req.full_url) or Falsa(b"y" * 600_000))
    with pytest.raises(ValueError, match="huella"):
        ocr_setup.instalar(tmp_path / "c", ocr_setup.URL_OFICIAL)
    assert pedidos == [ocr_setup.URL_OFICIAL] and not list((tmp_path / "c").glob("*"))


def test_dos_simulaciones_seguidas_no_comparten_id_ni_csv(base, cliente, tmp_path):
    for n in ("a", "b"):
        (tmp_path / n).mkdir()
        (tmp_path / n / f"doc 111111-2022 {n}.txt").write_text(CUERPO, encoding="utf-8")
    r1 = cliente.post("/api/simular", json={"origen": str(tmp_path / "a")}).get_json()
    r2 = cliente.post("/api/simular", json={"origen": str(tmp_path / "b")}).get_json()
    assert r1["id"] != r2["id"] and r1["csv"] != r2["csv"]
    for r in (r1, r2):
        for _ in range(100):
            if cliente.get(f"/api/simular/{r['id']}").get_json()["estado"] != "corriendo":
                break
            time.sleep(0.05)
    nombres = {Path(f["archivo"]).parent.name
               for r in (r1, r2) for f in cliente.get(f"/api/propuestas/{r['csv']}").get_json()["filas"]}
    assert nombres == {"a", "b"}


def test_json_con_elementos_que_no_son_objetos_da_400_no_500(base, cliente):
    assert cliente.post("/api/aliases", json=[None, "x", 3]).status_code == 400
    (base / "_SISTEMA" / "REORG_z.csv").write_text("archivo,destino,motivo,detalle,confianza,accion\n", encoding="utf-8")
    assert cliente.post("/api/propuestas/REORG_z.csv/aplicar", json={"filas": [None, "x"]}).status_code == 400


def test_inventario_coincide_con_el_recorrido_directo_y_se_actualiza_al_mover(base, cliente, tmp_path):
    casa = base / "01_Expedientes" / "2022-perez-gomez"
    (casa / "01_siged").mkdir(exist_ok=True)
    (casa / "01_siged" / "a.pdf").write_bytes(b"x")
    (casa / "01_siged" / "b.PDF").write_bytes(b"x")
    (casa / "suelto.txt").write_bytes(b"x")
    (base / "01_Expedientes" / "2023-vidal-luna" / "c.docx").write_bytes(b"x")
    D._invalidar_inventario()

    esperado = sum(1 for f in (base / "01_Expedientes").rglob("*") if f.is_file())
    assert cliente.get("/api/stats").get_json()["total_archivos"] == esperado
    exp = {e["nombre"]: e for e in cliente.get("/api/expedientes").get_json()}
    assert exp["2022-perez-gomez"]["total"] == 3
    assert exp["2022-perez-gomez"]["subcarpetas"] == {"01_siged": 2, "(raíz)": 1}
    assert exp["2022-perez-gomez"]["extensiones"] == {".pdf": 2, ".txt": 1}
    assert cliente.get("/api/tipos").get_json() == {".pdf": 2, ".txt": 1, ".docx": 1}

    origen = tmp_path / "entrada"
    origen.mkdir()
    (origen / "nuevo 111111-2022.txt").write_text(CUERPO, encoding="utf-8")
    sim = cliente.post("/api/simular", json={"origen": str(origen)}).get_json()
    for _ in range(100):
        if cliente.get(f"/api/simular/{sim['id']}").get_json()["estado"] != "corriendo":
            break
        time.sleep(0.05)
    filas = cliente.get(f"/api/propuestas/{sim['csv']}").get_json()["filas"]
    assert cliente.post(f"/api/propuestas/{sim['csv']}/aplicar", json={"filas": filas}).get_json()["movidos"] == 1
    assert cliente.get("/api/stats").get_json()["total_archivos"] == esperado + 1


def test_altas_simultaneas_no_se_pisan(base, cliente, monkeypatch):
    import threading
    agregar = D.cartera_alta.agregar

    def lento(*a, **k):
        r = agregar(*a, **k)
        time.sleep(0.05)
        return r
    monkeypatch.setattr(D.cartera_alta, "agregar", lento)
    exptes = [f"{900000 + i}/2024" for i in range(6)]
    hilos = [threading.Thread(target=lambda e=e: D.app.test_client().post("/api/cartera", json={"expte": e}))
             for e in exptes]
    for h in hilos:
        h.start()
    for h in hilos:
        h.join()
    cargadas = {c["expte"] for c in cliente.get("/api/cartera").get_json()["causas"]}
    assert set(exptes) <= cargadas


def test_editar_caratula_no_repite_la_carpeta_prevista_de_otra_causa(base, cliente):
    cliente.post("/api/cartera", json={"expte": "333333/2023", "caratula": "PAZ c/ RUIZ"})
    cliente.post("/api/cartera", json={"expte": "444444/2023", "caratula": "LOPEZ c/ DIAZ"})
    cliente.patch("/api/cartera", json={"expte": "444444/2023", "caratula": "PAZ c/ RUIZ"})
    previstas = [c["prevista"] for c in cliente.get("/api/cartera").get_json()["causas"] if c["prevista"]]
    assert len(previstas) == len(set(previstas))


def test_delete_y_patch_con_origin_ajeno_se_rechazan(base, cliente):
    ajeno = {"Origin": "http://sitio-ajeno.example"}
    assert cliente.delete("/api/cartera", json={"expte": "111111/2022"}, headers=ajeno).status_code == 403
    assert cliente.patch("/api/cartera", json={"expte": "111111/2022", "caratula": "X"}, headers=ajeno).status_code == 403


def test_soltar_descarta_nombres_reservados_de_windows(base, cliente):
    import io
    datos = {"archivos": [(io.BytesIO(b"x"), "CON.txt"), (io.BytesIO(b"x"), "nul"), (io.BytesIO(b"x"), "bueno.txt")]}
    r = cliente.post("/api/soltar", data=datos, content_type="multipart/form-data")
    assert r.status_code == 200 and r.get_json()["guardados"] == 1


@pytest.mark.parametrize("cuerpo", [{"patron": 123}, {"profundidad": [3]}, {"fuentes": 3}])
def test_escanear_con_entradas_mal_formadas_da_400(base, cliente, tmp_path, cuerpo):
    r = cliente.post("/api/cartera/escanear", json={"carpeta": str(tmp_path), **cuerpo})
    assert r.status_code == 400


def test_abre_el_navegador_solo_cuando_el_servidor_responde(monkeypatch):
    respuestas = iter([False, False, True])
    abiertos = []
    monkeypatch.setattr(D, "_ya_corre", lambda p: next(respuestas))
    monkeypatch.setattr(D.time, "sleep", lambda s: None)
    monkeypatch.setattr(D.webbrowser, "open", abiertos.append)
    D._abrir_cuando_responda("http://localhost:5999", 5999)
    assert abiertos == ["http://localhost:5999"]


def test_no_abre_el_navegador_si_el_servidor_nunca_responde(monkeypatch):
    abiertos = []
    monkeypatch.setattr(D, "_ya_corre", lambda p: False)
    monkeypatch.setattr(D.time, "sleep", lambda s: None)
    monkeypatch.setattr(D.webbrowser, "open", abiertos.append)
    D._abrir_cuando_responda("http://localhost:5999", 5999)
    assert abiertos == []


def test_la_pagina_no_pide_nada_a_internet_y_las_fuentes_se_sirven(cliente):
    import re
    html = cliente.get("/").get_data(as_text=True)
    assert not re.search(r"(src|href)=\"https?://", html)
    css = cliente.get("/static/fonts/fonts.css")
    assert css.status_code == 200
    archivos = re.findall(r"url\(([^)]+\.woff2)\)", css.get_data(as_text=True))
    assert archivos and all(cliente.get(f"/static/fonts/{a}").status_code == 200 for a in archivos)


def test_las_fuentes_viajan_con_su_licencia_y_dentro_del_exe():
    raiz = Path(D.__file__).resolve().parent
    assert sorted(p.name for p in (raiz / "static" / "fonts").glob("OFL-*.txt")) == [
        "OFL-dm-serif-display.txt", "OFL-ibm-plex-mono.txt", "OFL-inter.txt"]
    assert r"app\static;static" in (raiz.parent / "construir_exe.bat").read_text(encoding="utf-8")


def test_contraste_y_foco_visible():
    html = (Path(D.__file__).resolve().parent / "dashboard_app.html").read_text(encoding="utf-8")
    assert "--ink-muted: #4E6886;" in html and "#385A78" not in html and "#38526E" not in html
    assert ".btn:focus-visible" in html and ".nav-item:focus-visible" in html
