"""Alta de causas en la cartera: a mano, por lista pegada o escaneando una carpeta."""
from __future__ import annotations

import os
import re
from pathlib import Path

from cartera import Causa, Expte, normalizar_expte
from cartera_cruce import nombre_carpeta
from extractor import extraer_universal
from fase2_expedientes import buscar_caratula, buscar_expte

MAX_ARCHIVOS = 20000
MAX_TEXTOS = 300
FUENTES = ("carpeta", "archivo", "texto")

_EN_NOMBRE = re.compile(r"(?<![\d/.\-])(\d{2,6})\s*[-_/]\s*((?:19|20)\d{2})(?!\d)")
_INICIO_LISTA = re.compile(r"^\s*(\d{1,7}\s*/\s*\d{4})(.*)$")


def compilar_patron(texto: str | None) -> re.Pattern | None:
    """Patron propio del usuario: tiene que traer dos grupos, numero y anio."""
    if texto is None:
        return None
    if not isinstance(texto, str):
        raise ValueError("El patron tiene que ser texto")
    if not texto.strip():
        return None
    if len(texto) > 200:
        raise ValueError("El patron es demasiado largo (hasta 200 caracteres)")
    try:
        rx = re.compile(texto)
    except re.error as exc:
        raise ValueError(f"Patron invalido: {exc}") from exc
    if rx.groups < 2:
        raise ValueError("El patron necesita dos grupos entre parentesis: numero y anio, por ejemplo (\\d+)-(\\d{4})")
    return rx


def expte_en_nombre(nombre: str, propio: re.Pattern | None = None) -> Expte | None:
    for rx in ([propio] if propio else []) + [_EN_NOMBRE]:
        for m in rx.finditer(nombre):
            e = normalizar_expte(f"{int(m.group(1))}/{m.group(2)}") if m.group(1).isdigit() else None
            if e is not None:
                return e
    return None


def parsear_lista(texto: str) -> tuple[list[tuple[Expte, str | None]], list[str]]:
    """Una causa por linea: 'NNNN/AAAA' y, si queres, la caratula despues (espacio, coma, tab o punto y coma)."""
    items, invalidas = [], []
    for linea in texto.splitlines():
        if not linea.strip():
            continue
        m = _INICIO_LISTA.match(linea)
        e = normalizar_expte(re.sub(r"\s+", "", m.group(1))) if m else None
        if e is None:
            invalidas.append(linea.strip())
            continue
        resto = m.group(2).strip(" \t;|,:-–—")
        items.append((e, resto or None))
    return items, invalidas


def carpeta_libre(c: Causa, ocupadas: set[str]) -> str:
    nombre = nombre_carpeta(c)
    if nombre in ocupadas:
        nombre = f"{nombre}-{c.expte.numero}"
    return nombre


def agregar(existentes: list[Causa], items: list[tuple[Expte, str | None]], fuente: str,
            dependencia: str | None = None) -> tuple[list[Causa], dict]:
    """Devuelve la cartera completa y un resumen. No pisa causas ya cargadas."""
    claves = {c.expte.clave_completa for c in existentes}
    ocupadas = {n for c in existentes for n in (c.carpeta, c.carpeta_prevista) if n}
    nuevas, repetidas = [], []
    for e, caratula in items:
        if e.clave_completa in claves:
            repetidas.append(e.clave_completa)
            continue
        c = Causa(expte=e, caratula=caratula or None, dependencia=dependencia or None, fuentes=[fuente])
        c.carpeta_prevista = carpeta_libre(c, ocupadas)
        ocupadas.add(c.carpeta_prevista)
        claves.add(e.clave_completa)
        nuevas.append(c)
    return existentes + nuevas, {"agregadas": [c.expte.clave_completa for c in nuevas], "repetidas": repetidas}


def escanear(carpeta: Path, fuentes: tuple[str, ...] = ("carpeta", "archivo"), patron: str | None = None,
             profundidad: int = 6, claves_en_cartera: set[str] | None = None) -> dict:
    """Busca numeros de expediente en nombres de carpetas, de archivos y, si se pide, dentro del texto.

    Solo lee: no mueve ni escribe nada.
    """
    propio = compilar_patron(patron)
    fuentes = tuple(f for f in fuentes if f in FUENTES)
    claves_en_cartera = claves_en_cartera or set()
    raiz = carpeta.resolve()
    hallados: dict[str, dict] = {}
    revisados = textos = 0
    truncado = False

    for dirpath, dirnames, filenames in os.walk(raiz):
        rel = Path(dirpath).relative_to(raiz)
        if len(rel.parts) >= profundidad:
            dirnames[:] = []
        for nombre in filenames:
            if revisados >= MAX_ARCHIVOS:
                truncado = True
                break
            revisados += 1
            e = caratula = None
            origen = ""
            if "archivo" in fuentes:
                e = expte_en_nombre(Path(nombre).stem, propio)
                origen = "archivo"
            if e is None and "carpeta" in fuentes:
                for parte in reversed(rel.parts):
                    e = expte_en_nombre(parte, propio)
                    if e is not None:
                        origen = "carpeta"
                        break
            if "texto" in fuentes and textos < MAX_TEXTOS:
                textos += 1
                try:
                    cuerpo, _ = extraer_universal(Path(dirpath) / nombre, 8000)
                except Exception:  # noqa: BLE001
                    cuerpo = None
                if cuerpo:
                    caratula = buscar_caratula(cuerpo)
                    if e is None:
                        clave = buscar_expte(cuerpo)
                        e = normalizar_expte(clave) if clave else None
                        origen = "texto" if e else origen
            if e is None:
                continue
            h = hallados.setdefault(e.clave_completa, {
                "expte": e.clave_completa, "archivos": 0, "ejemplos": [], "caratula": None,
                "origen": origen, "en_cartera": e.clave_completa in claves_en_cartera})
            h["archivos"] += 1
            if len(h["ejemplos"]) < 3:
                h["ejemplos"].append(str(rel / nombre))
            h["caratula"] = h["caratula"] or caratula
        if truncado:
            break

    return {"carpeta": str(raiz), "revisados": revisados, "truncado": truncado,
            "causas": sorted(hallados.values(), key=lambda h: (-h["archivos"], h["expte"]))}
