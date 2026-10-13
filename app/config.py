"""Configuracion del organizador: variables de entorno > config.json del usuario > valores por defecto."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path


def _ruta(variable: str, defecto: str | Path) -> Path:
    return Path(os.environ.get(variable) or defecto)


CONFIG_PATH = _ruta("ORGANIZADOR_CONFIG", Path(os.environ.get("APPDATA") or Path.home()) / "Organizador" / "config.json")


def _leer() -> dict:
    try:
        datos = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return datos if isinstance(datos, dict) else {}


_CFG = _leer()
CONFIGURADO = bool(_CFG) or bool(os.environ.get("ORGANIZADOR_BASE"))
ESTUDIO = str(_CFG.get("estudio") or "")
UBICACION = str(_CFG.get("ubicacion") or "")

BASE = _ruta("ORGANIZADOR_BASE", _CFG.get("base") or Path.home() / "Organizador")
def _tessdata() -> Path:
    """Carpeta con spa.traineddata: la del usuario (donde se instala), una junto al .exe o ~/tessdata."""
    propia = CONFIG_PATH.parent / "tessdata"
    candidatas = [propia, Path.home() / "tessdata"]
    if getattr(sys, "frozen", False):
        candidatas.insert(1, Path(sys.executable).parent / "tessdata")
    return next((c for c in candidatas if (c / "spa.traineddata").is_file()), propia)


TESSDATA = _ruta("TESSDATA_PREFIX", _tessdata())
OCR_CACHE = _ruta("ORGANIZADOR_OCR_CACHE", BASE / "_SISTEMA" / "ocr_cache")
CORPUS = _ruta("ORGANIZADOR_CORPUS", BASE / "_CORPUS")


def _apellidos() -> tuple[str, ...]:
    crudo = os.environ.get("ORGANIZADOR_APELLIDOS")
    lista = crudo.split(",") if crudo is not None else _CFG.get("apellidos") or []
    if isinstance(lista, str):
        lista = lista.split(",")
    return tuple(a.strip().lower() for a in lista if isinstance(a, str) and a.strip())


APELLIDOS_PROPIOS = _apellidos()


def guardar_config(datos: dict) -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = CONFIG_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(datos, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(CONFIG_PATH)
