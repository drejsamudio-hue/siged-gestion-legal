"""Dashboard interactivo para el organizador de expedientes.

Uso:
    python dashboard.py              # arranca en http://localhost:5050
    python dashboard.py --port 8080  # puerto custom
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import uuid
import urllib.request
import webbrowser
import re
import subprocess
import sys
import threading
import time
from collections import Counter
from datetime import datetime
from pathlib import Path

from flask import Flask, abort, jsonify, request, send_file

sys.path.insert(0, str(Path(__file__).parent))
import ingesta  # noqa: E402
import cartera_alta  # noqa: E402
import ocr_setup  # noqa: E402
from cartera import cargar as cargar_cartera, guardar as guardar_cartera, normalizar_expte  # noqa: E402
from cartera_cruce import cruzar  # noqa: E402
from cartera_fuentes import _reparar  # noqa: E402
from extractor import extraer_universal  # noqa: E402
from ingesta import (  # noqa: E402
    ALIAS_FILE, BASE, CASOS, INBOX, NO_CLASIFICADOS, RUTEO_CSV,
    archivos_pendientes, destino_de, mover, validar_alias,
)

LOG_FILE = BASE / "_SISTEMA" / "dashboard_log.json"
import config as cfg  # noqa: E402
from config import JUSTI_DIR  # noqa: E402
RE_APELLIDO = re.compile(r"^[a-záéíóúñü]{3,30}$", re.I)
RE_PROPUESTA = re.compile(r"^REORG_[\w.-]+\.csv$")
COLUMNAS = ["archivo", "destino", "motivo", "detalle", "confianza", "accion", "extracto"]
HTML_FILE = Path(__file__).parent / "dashboard_app.html"

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 1024 * 1024 * 1024


@app.before_request
def _solo_local():
    # Frena DNS rebinding: otra web no puede hablarle a la API aunque resuelva a 127.0.0.1.
    if request.host.split(":")[0] not in {"localhost", "127.0.0.1"}:
        abort(403)
    origen = request.headers.get("Origin")
    if request.method not in {"GET", "HEAD", "OPTIONS"} and origen and origen.split("://", 1)[-1] != request.host:
        abort(403)


def _leer_aliases() -> dict:
    if not ALIAS_FILE.exists():
        return {"aliases": []}
    return json.loads(ALIAS_FILE.read_text(encoding="utf-8"))


def _log_action(action: str, details: dict):
    log = []
    if LOG_FILE.exists():
        try:
            log = json.loads(LOG_FILE.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            pass
    log.append({"ts": datetime.now().isoformat(), "action": action, **details})
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    LOG_FILE.write_text(json.dumps(log[-500:], ensure_ascii=False, indent=2), encoding="utf-8")


def _rel(p: Path) -> str:
    try:
        return str(p.relative_to(BASE))
    except ValueError:
        return str(p)


def _causa(carpeta: Path) -> str | None:
    try:
        return carpeta.relative_to(CASOS).parts[0]
    except (ValueError, IndexError):
        return None


@app.route("/")
def index():
    return send_file(str(HTML_FILE))


def _nuevo_id() -> str:
    return datetime.now().strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:6]


def _reiniciar() -> None:
    """Relanza el proceso para que tome la configuracion nueva (BASE y demas se fijan al importar)."""
    def _go():
        time.sleep(1.0)
        flags = getattr(subprocess, "CREATE_NEW_CONSOLE", 0)
        congelado = getattr(sys, "frozen", False)
        args = sys.argv[1:] if congelado else sys.argv
        # Sin esto, el .exe hijo reutiliza la carpeta temporal del padre, que se borra al salir este.
        env = {**os.environ, "PYINSTALLER_RESET_ENVIRONMENT": "1"} if congelado else None
        subprocess.Popen([sys.executable, *args], creationflags=flags, close_fds=True, env=env)
        os._exit(0)
    threading.Thread(target=_go, daemon=True).start()


@app.route("/api/config")
def api_config_get():
    return jsonify({"configurado": cfg.CONFIGURADO, "estudio": cfg.ESTUDIO, "ubicacion": cfg.UBICACION,
                    "apellidos": list(cfg.APELLIDOS_PROPIOS), "base": str(BASE)})


@app.route("/api/config", methods=["POST"])
def api_config_post():
    d = request.get_json(silent=True)
    if not isinstance(d, dict):
        return jsonify({"error": "Se esperaba un objeto JSON"}), 400
    estudio, ubicacion, base = (str(d.get(k) or "").strip() for k in ("estudio", "ubicacion", "base"))
    crudo = d.get("apellidos") or []
    apellidos = [a.strip().lower() for a in (crudo.split(",") if isinstance(crudo, str) else crudo)
                 if isinstance(a, str) and a.strip()]
    if not estudio or len(estudio) > 80 or len(ubicacion) > 80:
        return jsonify({"error": "Falta el nombre del estudio (hasta 80 caracteres)"}), 400
    if not apellidos or not all(RE_APELLIDO.match(a) for a in apellidos):
        return jsonify({"error": "Escribi al menos un apellido, solo letras, separados por coma"}), 400
    destino = Path(base)
    if not base or not destino.is_absolute() or destino.parent == destino:
        return jsonify({"error": "La carpeta base tiene que ser una ruta completa, no la raiz del disco"}), 400
    try:
        destino.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        return jsonify({"error": f"No se pudo crear la carpeta base: {exc}"}), 400
    cfg.guardar_config({"estudio": estudio, "ubicacion": ubicacion, "apellidos": apellidos, "base": str(destino)})
    _reiniciar()
    return jsonify({"ok": True, "reiniciando": True})


def _estado_ocr() -> dict:
    import extractor
    return {"disponible": extractor.ocr_disponible(), "carpeta": str(extractor.TESSDATA),
            "fuente": ocr_setup.url_descarga(), "pagina": ocr_setup.PAGINA_OFICIAL, "archivo": ocr_setup.ARCHIVO}


@app.route("/api/ocr")
def api_ocr():
    return jsonify(_estado_ocr())


@app.route("/api/ocr/instalar", methods=["POST"])
def api_ocr_instalar():
    """Descarga el idioma espanol del repositorio oficial de Tesseract. Solo corre si el usuario lo pide."""
    import extractor
    try:
        ocr_setup.instalar(extractor.TESSDATA)
    except (OSError, ValueError) as exc:
        return jsonify({"error": f"No se pudo descargar: {exc}"}), 502
    _log_action("ocr_instalar", {"carpeta": str(extractor.TESSDATA)})
    return jsonify(_estado_ocr())


_inv: dict = {"t": 0.0, "datos": None}
INVENTARIO_TTL = 10.0


def _inventario() -> dict[str, list[tuple[str, str, float]]]:
    """Archivos de cada causa en un solo recorrido: {causa: [(subcarpeta, extension, mtime)]}.

    Se reutiliza unos segundos entre las consultas de una misma apertura y se descarta al mover o deshacer.
    """
    ahora = time.time()
    if _inv["datos"] is None or _inv.get("base") != str(CASOS) or ahora - _inv["t"] > INVENTARIO_TTL:
        datos = {}
        for d in CASOS.iterdir():
            if not d.is_dir():
                continue
            lista = []
            for dirpath, _, nombres in os.walk(d):
                rel = os.path.relpath(dirpath, d)
                sub = "(raíz)" if rel == "." else rel.split(os.sep)[0]
                for nombre in nombres:
                    try:
                        mtime = os.stat(os.path.join(dirpath, nombre)).st_mtime
                    except OSError:
                        continue
                    lista.append((sub, os.path.splitext(nombre)[1].lower(), mtime))
            datos[d.name] = lista
        _inv.update(t=ahora, datos=datos, base=str(CASOS))
    return _inv["datos"]


def _invalidar_inventario() -> None:
    _inv["datos"] = None


def _contar(carpeta: str) -> int:
    inv = _inventario()
    if carpeta in inv:
        return len(inv[carpeta])
    return sum(1 for f in (CASOS / carpeta).rglob("*") if f.is_file())


@app.route("/api/stats")
def api_stats():
    inv = _inventario()
    casos_dirs = list(inv)
    total_archivos = sum(len(v) for v in inv.values())
    inbox = len(archivos_pendientes(INBOX)) \
        if INBOX.exists() else 0
    return jsonify({
        "total_causas": len(casos_dirs),
        "total_archivos": total_archivos,
        "inbox_pendientes": inbox,
        "aliases_configurados": len(_leer_aliases().get("aliases", [])),
    })


@app.route("/api/expedientes")
def api_expedientes():
    q = request.args.get("q", "").lower()
    inventario = _inventario()
    casos = []
    for d in sorted(CASOS.iterdir()):
        if not d.is_dir() or (q and q not in d.name.lower()):
            continue
        files = inventario.get(d.name, [])
        subs = Counter(f[0] for f in files)
        last_mod = max((f[2] for f in files), default=0)
        casos.append({
            "nombre": d.name,
            "total": len(files),
            "subcarpetas": dict(subs),
            "extensiones": dict(Counter(f[1] for f in files).most_common(5)),
            "ultima_mod": datetime.fromtimestamp(last_mod).isoformat() if last_mod else None,
        })
    return jsonify(casos)


@app.route("/api/aliases", methods=["GET"])
def api_aliases_get():
    return jsonify(_leer_aliases().get("aliases", []))


@app.route("/api/aliases", methods=["POST"])
def api_aliases_post():
    nuevos = request.get_json(silent=True)
    if not isinstance(nuevos, list):
        return jsonify({"ok": False, "errores": ["Se esperaba una lista"]}), 400
    errores = []
    for i, a in enumerate(nuevos, 1):
        if not isinstance(a, dict):
            errores.append(f"Fila {i}: se esperaba un objeto con pattern y caso")
            continue
        err = validar_alias(str(a.get("pattern", "")), str(a.get("caso", "")))
        if err:
            errores.append(f"Fila {i} ({a.get('pattern', '')}): {err}")
    if errores:
        return jsonify({"ok": False, "errores": errores}), 400

    data = _leer_aliases()
    data["aliases"] = [{"pattern": a["pattern"], "caso": a["caso"]} for a in nuevos]
    ALIAS_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    _log_action("alias_update", {"count": len(nuevos)})
    return jsonify({"ok": True, "count": len(nuevos)})


@app.route("/api/log")
def api_log():
    if not LOG_FILE.exists():
        return jsonify([])
    try:
        return jsonify(json.loads(LOG_FILE.read_text(encoding="utf-8"))[-50:])
    except (OSError, json.JSONDecodeError):
        return jsonify([])


@app.route("/api/tipos")
def api_tipos():
    exts = Counter(e for lista in _inventario().values() for _, e, _ in lista)
    exts.update(f.suffix.lower() for f in CASOS.iterdir() if f.is_file())
    return jsonify(dict(exts.most_common(20)))


# ── Cartera y escritorio ─────────────────────────────────────────────

def _sistema() -> Path:
    return ingesta.SISTEMA


@app.route("/api/cartera")
def api_cartera():
    ruta = _sistema() / "cartera.json"
    if not ruta.exists():
        return jsonify({"causas": [], "resumen": {}})
    causas = cargar_cartera(ruta)
    cruces = {id(x.causa): x for x in cruzar(causas, CASOS, ingesta._mapa_exptes())}
    out = []
    for c in causas:
        x = cruces.get(id(c))
        carpeta = c.carpeta or c.carpeta_prevista
        existe = bool(carpeta) and (CASOS / carpeta).is_dir()
        out.append({
            "expte": c.expte.clave_completa, "id": c.id_expediente, "caratula": c.caratula,
            "dependencia": c.dependencia, "carpeta": c.carpeta, "prevista": c.carpeta_prevista,
            "existe": existe, "bis": c.expte.bis is not None, "fuentes": c.fuentes,
            "accion": x.accion if x else None, "nota": x.nota if x else "",
            "archivos": _contar(carpeta) if existe else 0,
        })
    return jsonify({"causas": out, "resumen": dict(Counter(c["accion"] for c in out))})


_cartera_lock = threading.Lock()


def _cargar_cartera() -> list:
    ruta = _sistema() / "cartera.json"
    return cargar_cartera(ruta) if ruta.exists() else []


def _json_objeto():
    d = request.get_json(silent=True)
    return d if isinstance(d, dict) else {}


def _agregar_a_cartera(items, fuente: str, dependencia: str | None = None) -> dict:
    with _cartera_lock:
        todas, resumen = cartera_alta.agregar(_cargar_cartera(), items, fuente, dependencia)
        if resumen["agregadas"]:
            guardar_cartera(todas, _sistema() / "cartera.json")
            ingesta._exptes_cache = None
            _log_action("cartera_alta", {"fuente": fuente, "agregadas": len(resumen["agregadas"])})
    return resumen


@app.route("/api/cartera", methods=["POST"])
def api_cartera_alta():
    d = _json_objeto()
    e = normalizar_expte(str(d.get("expte") or "").strip())
    if e is None:
        return jsonify({"error": "Expediente invalido. Usa el formato NNNN/AAAA, por ejemplo 1234/2023"}), 400
    r = _agregar_a_cartera([(e, str(d.get("caratula") or "").strip() or None)], "manual",
                           str(d.get("dependencia") or "").strip() or None)
    if r["repetidas"]:
        return jsonify({"error": f"{e.clave_completa} ya esta en la cartera"}), 409
    return jsonify(r)


@app.route("/api/cartera", methods=["PATCH"])
def api_cartera_editar():
    d = _json_objeto()
    e = normalizar_expte(str(d.get("expte") or ""))
    with _cartera_lock:
        causas = _cargar_cartera()
        c = next((x for x in causas if e and x.expte.clave_completa == e.clave_completa), None)
        if c is None:
            return jsonify({"error": "Esa causa no esta en la cartera"}), 404
        if "caratula" in d:
            c.caratula = str(d["caratula"] or "").strip() or None
            if not c.carpeta and not (c.carpeta_prevista and (CASOS / c.carpeta_prevista).is_dir()):
                ocupadas = {n for x in causas if x is not c for n in (x.carpeta, x.carpeta_prevista) if n}
                c.carpeta_prevista = cartera_alta.carpeta_libre(c, ocupadas)
        if "dependencia" in d:
            c.dependencia = str(d["dependencia"] or "").strip() or None
        guardar_cartera(causas, _sistema() / "cartera.json")
    _log_action("cartera_editar", {"expte": c.expte.clave_completa})
    return jsonify({"ok": True})


@app.route("/api/cartera", methods=["DELETE"])
def api_cartera_baja():
    """Saca la causa de la cartera. No toca ninguna carpeta ni archivo."""
    e = normalizar_expte(str(_json_objeto().get("expte") or ""))
    with _cartera_lock:
        causas = _cargar_cartera()
        resto = [x for x in causas if not (e and x.expte.clave_completa == e.clave_completa)]
        if e is None or len(resto) == len(causas):
            return jsonify({"error": "Esa causa no esta en la cartera"}), 404
        guardar_cartera(resto, _sistema() / "cartera.json")
        ingesta._exptes_cache = None
    _log_action("cartera_baja", {"expte": e.clave_completa})
    return jsonify({"ok": True})


@app.route("/api/cartera/lista", methods=["POST"])
def api_cartera_lista():
    texto = str(_json_objeto().get("texto") or "")
    if len(texto) > 200_000:
        return jsonify({"error": "La lista es demasiado larga"}), 400
    items, invalidas = cartera_alta.parsear_lista(texto)
    if not items and not invalidas:
        return jsonify({"error": "La lista esta vacia"}), 400
    r = _agregar_a_cartera(items, "lista")
    return jsonify({**r, "invalidas": invalidas})


@app.route("/api/cartera/escanear", methods=["POST"])
def api_cartera_escanear():
    d = _json_objeto()
    carpeta = Path(str(d.get("carpeta") or "").strip())
    if not carpeta.is_dir():
        return jsonify({"error": f"No existe la carpeta: {carpeta}"}), 404
    pedidas = d.get("fuentes") or ["carpeta", "archivo"]
    fuentes = tuple(f for f in pedidas if f in cartera_alta.FUENTES) if isinstance(pedidas, list) else ()
    if not fuentes:
        return jsonify({"error": "Elegi al menos una fuente: carpeta, archivo o texto"}), 400
    try:
        profundidad = max(1, min(int(d.get("profundidad") or 6), 12))
        r = cartera_alta.escanear(carpeta, fuentes, d.get("patron"), profundidad,
                                  {c.expte.clave_completa for c in _cargar_cartera()})
    except (ValueError, TypeError) as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify(r)


@app.route("/api/cartera/escanear/agregar", methods=["POST"])
def api_cartera_escanear_agregar():
    filas = _json_objeto().get("causas")
    if not isinstance(filas, list) or not filas:
        return jsonify({"error": "No hay causas para agregar"}), 400
    items = []
    for f in filas:
        e = normalizar_expte(str(f.get("expte") or "")) if isinstance(f, dict) else None
        if e is not None:
            items.append((e, str(f.get("caratula") or "").strip() or None))
    return jsonify(_agregar_a_cartera(items, "escaneo"))


def _ultimo_escritorio() -> Path | None:
    candidatos = sorted(JUSTI_DIR.glob("*/escritorio.json")) if JUSTI_DIR.exists() else []
    return candidatos[-1] if candidatos else None


@app.route("/api/escritorio")
def api_escritorio():
    ruta = _ultimo_escritorio()
    if ruta is None:
        return jsonify({"archivo": None, "filas": []})
    ruta_cartera = _sistema() / "cartera.json"
    causas = cargar_cartera(ruta_cartera) if ruta_cartera.exists() else []
    claves = {c.expte.clave_completa for c in causas}
    ids = {c.id_expediente for c in causas if c.id_expediente}
    filas = []
    for f in json.loads(ruta.read_text(encoding="utf-8")):
        numero = f.get("numero")
        texto = numero.get("texto", "") if isinstance(numero, dict) else (numero or "")
        e = normalizar_expte(texto) if isinstance(texto, str) else None
        idx = str(f.get("id_expediente") or "")
        filas.append({
            "numero": texto, "id": idx, "designacion": _reparar(f.get("designacion")),
            "origen": _reparar(f.get("origen")), "resaltado": bool(f.get("resaltado")),
            "en_cartera": (e is not None and e.clave_completa in claves) or idx in ids,
        })
    return jsonify({"archivo": str(ruta), "filas": filas})


# ── Historial y tandas ───────────────────────────────────────────────

@app.route("/api/historial")
def api_historial():
    filas = ingesta.leer_ruteo()
    q = request.args.get("q", "").lower()
    tandas = []
    for t in reversed(ingesta.tandas_historicas(filas, ingesta.leer_tandas())):
        a, b = int(t["primera_fila"]), int(t["ultima_fila"])
        sel = filas[a:b + 1]
        if q and not any(q in (f["origen"] + f["destino"]).lower() for f in sel):
            continue
        areas = Counter(Path(_rel(Path(f["destino"]))).parts[0] for f in sel)
        tandas.append({**t, "motivos": dict(Counter(f["motivo"] for f in sel).most_common()),
                       "areas": dict(areas.most_common(4))})
    aplicado = _sistema() / "CARTERA_APLICADO.csv"
    renombres = list(csv.DictReader(aplicado.open(encoding="utf-8"))) if aplicado.exists() else []
    return jsonify({"total_movimientos": len(filas), "tandas": tandas, "carpetas": renombres[::-1]})


@app.route("/api/historial/filas")
def api_historial_filas():
    a, b = request.args.get("primera", type=int), request.args.get("ultima", type=int)
    filas = ingesta.leer_ruteo()
    if a is None or b is None or not 0 <= a <= b < len(filas):
        return jsonify({"error": "rango invalido"}), 400
    return jsonify([{**f, "origen_rel": _rel(Path(f["origen"])), "destino_rel": _rel(Path(f["destino"]))}
                    for f in filas[a:b + 1]])


@app.route("/api/tandas/deshacer", methods=["POST"])
def api_deshacer():
    datos = request.get_json(silent=True) or {}
    a, b = datos.get("primera"), datos.get("ultima")
    total = len(ingesta.leer_ruteo())
    if not (isinstance(a, int) and isinstance(b, int) and 0 <= a <= b < total):
        return jsonify({"error": "rango invalido"}), 400
    r = ingesta.deshacer_filas(a, b)
    _invalidar_inventario()
    _log_action("deshacer", {"filas": f"{a}-{b}", "restaurados": r["restaurados"]})
    return jsonify(r)


# ── Simulacion y propuestas ──────────────────────────────────────────

_simulaciones: dict[str, dict] = {}


def _extracto(p: Path, largo: int = 160) -> str:
    """Lo primero que el organizador leyo del archivo (texto, OCR o nada): explica el destino propuesto."""
    try:
        texto, err = extraer_universal(p)
    except Exception:  # noqa: BLE001
        return ""
    if not texto:
        return f"[{err or 'sin texto'}]"
    return " ".join(texto.split())[:largo]


def _simular(sid: str, origen: Path) -> None:
    estado = _simulaciones[sid]
    try:
        archivos = archivos_pendientes(origen)
        estado["total"] = len(archivos)
        filas = []
        for p in archivos:
            d = destino_de(p)
            queda = d.motivo in NO_CLASIFICADOS
            filas.append([p, d.carpeta, d.motivo, d.detalle, d.confianza, "queda" if queda else "mover", _extracto(p)])
            estado["hechos"] += 1
        with (_sistema() / estado["csv"]).open("w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f)
            w.writerow(COLUMNAS)
            w.writerows(filas)
        estado["estado"] = "listo"
    except Exception as exc:  # noqa: BLE001
        estado.update(estado="error", error=str(exc))


@app.route("/api/simular", methods=["POST"])
def api_simular():
    origen = Path((request.get_json(silent=True) or {}).get("origen", ""))
    if not origen.is_dir():
        return jsonify({"error": f"No existe la carpeta: {origen}"}), 404
    sid = _nuevo_id()
    _simulaciones[sid] = {"id": sid, "origen": str(origen), "csv": f"REORG_{sid}.csv",
                          "total": None, "hechos": 0, "estado": "corriendo", "error": None}
    threading.Thread(target=_simular, args=(sid, origen), daemon=True).start()
    return jsonify(_simulaciones[sid])


@app.route("/api/simular/<sid>")
def api_simular_estado(sid):
    if sid not in _simulaciones:
        return jsonify({"error": "simulacion desconocida"}), 404
    return jsonify(_simulaciones[sid])


def _ruta_propuesta(nombre: str) -> Path | None:
    ruta = _sistema() / nombre
    return ruta if RE_PROPUESTA.match(nombre) and ruta.is_file() else None


@app.route("/api/propuestas")
def api_propuestas():
    out = []
    for ruta in sorted(_sistema().glob("REORG_*.csv"), key=lambda p: p.stat().st_mtime, reverse=True):
        try:
            filas = ingesta._leer_propuestas(ruta)
        except (OSError, csv.Error, IndexError):
            continue
        a_mover = [f for f in filas if (f.get("accion") or "").lower() == "mover"]
        out.append({"nombre": ruta.name,
                    "fecha": datetime.fromtimestamp(ruta.stat().st_mtime).isoformat(timespec="minutes"),
                    "filas": len(filas), "a_mover": len(a_mover),
                    "pendientes": sum(1 for f in a_mover if Path(f.get("archivo") or "").is_file())})
    return jsonify(out)


@app.route("/api/propuestas/<nombre>")
def api_propuesta(nombre):
    ruta = _ruta_propuesta(nombre)
    if ruta is None:
        return jsonify({"error": "propuesta desconocida"}), 404
    filas = []
    for i, f in enumerate(ingesta._leer_propuestas(ruta)):
        p, d = Path(f.get("archivo") or ""), Path(f.get("destino") or "")
        filas.append({"i": i, **{k: f.get(k) or "" for k in COLUMNAS}, "nombre": p.name,
                      "existe": p.is_file(), "destino_rel": _rel(d), "causa": _causa(d)})
    return jsonify({"nombre": nombre, "base": str(BASE), "filas": filas,
                    "fecha": datetime.fromtimestamp(ruta.stat().st_mtime).isoformat(timespec="minutes"),
                    "vieja": datetime.now().timestamp() - ruta.stat().st_mtime > 24 * 3600})


@app.route("/api/propuestas/<nombre>/aplicar", methods=["POST"])
def api_propuesta_aplicar(nombre):
    ruta = _ruta_propuesta(nombre)
    if ruta is None:
        return jsonify({"error": "propuesta desconocida"}), 404
    filas = (request.get_json(silent=True) or {}).get("filas")
    if not isinstance(filas, list):
        return jsonify({"error": "Se esperaba la lista de filas"}), 400
    base = BASE.resolve()
    for i, f in enumerate(filas, 1):
        if not isinstance(f, dict):
            return jsonify({"error": f"Fila {i}: se esperaba un objeto"}), 400
    for f in filas:
        if f.get("accion") == "mover" and not Path(f.get("destino") or "").resolve().is_relative_to(base):
            return jsonify({"error": f"Destino fuera de {BASE}: {f.get('destino')}"}), 400
    simulados = {fila.get("archivo") for fila in ingesta._leer_propuestas(ruta)}
    for f in filas:
        if f.get("accion") == "mover" and f.get("archivo") not in simulados:
            return jsonify({"error": f"Archivo que no esta en la simulacion: {f.get('archivo')}"}), 400
    with ruta.open("w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=COLUMNAS, extrasaction="ignore")
        w.writeheader()
        w.writerows(filas)
    r = ingesta.aplicar_filas(filas, nombre)
    _invalidar_inventario()
    _log_action("aplicar", {"propuesta": nombre, "movidos": r["movidos"], "tanda": r["tanda"]})
    return jsonify(r)


@app.route("/api/carpetas")
def api_carpetas():
    """Destinos para corregir una fila: carpetas de causa y temas de jurisprudencia, doctrina y legislacion."""
    out = ["05_Modelos_y_Escritos"]
    for area in ("02_Jurisprudencia", "03_Doctrina", "04_Legislacion"):
        raiz = BASE / area
        if raiz.is_dir():
            out += [_rel(d) for d in raiz.glob("*/*") if d.is_dir()]
    if CASOS.is_dir():
        out += [_rel(d / s) for d in CASOS.iterdir() if d.is_dir() for s in ("00_escritos_propios", "01_siged")]
    return jsonify(sorted(out))

@app.route("/api/aliases/cartera")
def api_aliases_cartera():
    ruta = ingesta.ALIAS_CARTERA
    if not ruta.exists():
        return jsonify([])
    try:
        return jsonify(json.loads(ruta.read_text(encoding="utf-8")).get("aliases", []))
    except (OSError, json.JSONDecodeError):
        return jsonify([])


NOMBRE_INVALIDO = set('<>:"/\\|?*')
RESERVADOS_WINDOWS = {"CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1, 10)), *(f"LPT{i}" for i in range(1, 10))}


@app.route("/api/soltar", methods=["POST"])
def api_soltar():
    """Copia los archivos soltados en el navegador a _INBOX/_soltados/<fecha> y los simula."""
    archivos = request.files.getlist("archivos")
    if not archivos:
        return jsonify({"error": "No llegaron archivos"}), 400
    sid = _nuevo_id()
    carpeta = INBOX / "_soltados" / sid
    carpeta.mkdir(parents=True, exist_ok=True)
    guardados = 0
    for a in archivos:
        nombre = Path(a.filename or "").name.strip()
        if (not nombre or nombre.startswith(".") or NOMBRE_INVALIDO & set(nombre)
                or nombre.split(".")[0].strip().upper() in RESERVADOS_WINDOWS):
            continue
        a.save(str(ingesta.destino_unico(carpeta / nombre)))
        guardados += 1
    if not guardados:
        return jsonify({"error": "Ningun nombre de archivo valido"}), 400
    _simulaciones[sid] = {"id": sid, "origen": str(carpeta), "csv": f"REORG_{sid}.csv",
                          "total": None, "hechos": 0, "estado": "corriendo", "error": None}
    threading.Thread(target=_simular, args=(sid, carpeta), daemon=True).start()
    _log_action("soltar", {"archivos": guardados, "carpeta": str(carpeta)})
    return jsonify({**_simulaciones[sid], "guardados": guardados})


# ── Carpetas fuera de la cartera ─────────────────────────────────────

def _propias_sin_numero() -> list[str]:
    ruta = _sistema() / "carpetas_propias.json"
    try:
        return json.loads(ruta.read_text(encoding="utf-8")) if ruta.exists() else []
    except (OSError, json.JSONDecodeError):
        return []


@app.route("/api/fuera")
def api_fuera():
    """Carpetas de 01_Expedientes que no estan en la cartera ni fueron marcadas como propias."""
    ruta_cartera = _sistema() / "cartera.json"
    causas = cargar_cartera(ruta_cartera) if ruta_cartera.exists() else []
    en_cartera = {(c.carpeta or c.carpeta_prevista or "").split("/")[0] for c in causas}
    propias = set(_propias_sin_numero())
    senales = {}
    analisis = _sistema() / "PROPIEDAD_CARPETAS.csv"
    if analisis.exists():
        senales = {r["carpeta"]: r for r in csv.DictReader(analisis.open(encoding="utf-8-sig"))}
    out = []
    for d in sorted(x for x in CASOS.iterdir() if x.is_dir()):
        if d.name in en_cartera or d.name in propias:
            continue
        s = senales.get(d.name, {})
        out.append({"carpeta": d.name, "archivos": _contar(d.name),
                    "clase": s.get("clase", "sin analizar"), "matricula": s.get("matricula") or "0",
                    "apellido": s.get("apellido") or "0"})
    return jsonify(out)


def _carpeta_valida(nombre: str) -> Path | None:
    d = CASOS / (nombre or "")
    return d if nombre and "/" not in nombre and "\\" not in nombre and d.is_dir() else None


@app.route("/api/fuera/mia", methods=["POST"])
def api_fuera_mia():
    d = _carpeta_valida((request.get_json(silent=True) or {}).get("carpeta"))
    if d is None:
        return jsonify({"error": "carpeta desconocida"}), 404
    propias = _propias_sin_numero()
    if d.name not in propias:
        propias.append(d.name)
        (_sistema() / "carpetas_propias.json").write_text(json.dumps(sorted(propias), ensure_ascii=False, indent=2),
                                                         encoding="utf-8")
    _log_action("carpeta_propia", {"carpeta": d.name})
    return jsonify({"ok": True})


@app.route("/api/fuera/ajena", methods=["POST"])
def api_fuera_ajena():
    """Arma una propuesta para sacar la carpeta de 01_Expedientes; se revisa y aplica en Tandas."""
    d = _carpeta_valida((request.get_json(silent=True) or {}).get("carpeta"))
    if d is None:
        return jsonify({"error": "carpeta desconocida"}), 404
    filas = []
    for p in (x for x in d.rglob("*") if x.is_file()):
        dd = ingesta.destino_ajeno(p, d.name)
        filas.append([p, dd.carpeta, dd.motivo, dd.detalle, dd.confianza, "mover", _extracto(p)])
    nombre = f"REORG_AJENA_{_nuevo_id()}.csv"
    with (_sistema() / nombre).open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(COLUMNAS)
        w.writerows(filas)
    return jsonify({"csv": nombre, "archivos": len(filas)})


def _abrir_cuando_responda(url: str, puerto: int) -> None:
    for _ in range(40):
        if _ya_corre(puerto):
            webbrowser.open(url)
            return
        time.sleep(0.5)


def _ya_corre(puerto: int) -> bool:
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{puerto}/api/config", timeout=2) as r:
            return r.status == 200
    except OSError:
        return False


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=5050)
    ap.add_argument("--no-abrir", action="store_true", help="No abrir el navegador al iniciar")
    args = ap.parse_args()
    url = f"http://localhost:{args.port}"
    if _ya_corre(args.port):
        print(f"El organizador ya esta abierto en {url}")
        if not args.no_abrir:
            webbrowser.open(url)
        sys.exit(0)
    ingesta.asegurar_estructura()
    print(f"Organizador: {url}")
    print("No cierres esta ventana mientras lo uses.")
    if not args.no_abrir:
        threading.Thread(target=_abrir_cuando_responda, args=(url, args.port), daemon=True).start()
    for _ in range(15):
        try:
            app.run(host="127.0.0.1", port=args.port, debug=False)
            break
        except OSError:
            time.sleep(1)
