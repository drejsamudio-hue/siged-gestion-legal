"""Lectores de las fuentes que dicen cuales son las causas propias."""
from __future__ import annotations

import re

from cartera import Causa, normalizar_expte

RE_ENCABEZADO_LOG = re.compile(r"^\[(?:\d+|EXTRA)\]\s+(?P<num>\S.*?)\s+✅")
RE_CARATULA_LOG = re.compile(
    r"^\s+(?P<c>[A-ZÁÉÍÓÚÑ][^\n—]*?\s(?:c/|s/)\s[^\n—]*?)\s*(?:—|$)"
)


def _reparar(texto: str | None) -> str | None:
    """SIGED entrega UTF-8 leido como cp1252 ("PEÃ‘A"); lo que ya esta bien queda igual."""
    if not texto or "Ã" not in texto:
        return texto or None
    try:
        return texto.encode("cp1252").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return texto


def desde_escritorio(filas: list[dict]) -> list[Causa]:
    """Filas de escritorio.json de la skill justi-control (una por expediente)."""
    causas = []
    for f in filas:
        numero = f.get("numero")
        texto = numero.get("texto", "") if isinstance(numero, dict) else numero
        e = normalizar_expte(texto if isinstance(texto, str) else "")
        if e is None:
            continue
        causas.append(Causa(
            expte=e,
            id_expediente=str(f["id_expediente"]) if f.get("id_expediente") else None,
            caratula=_reparar(f.get("designacion")),
            dependencia=_reparar(f.get("origen")),
            fuentes=["justi-escritorio"],
        ))
    return causas


def desde_log_justi(texto: str) -> list[Causa]:
    causas: list[Causa] = []
    actual: Causa | None = None
    for linea in texto.splitlines():
        m = RE_ENCABEZADO_LOG.match(linea)
        if m:
            e = normalizar_expte(m.group("num"))
            actual = Causa(expte=e, fuentes=["justi-log"]) if e else None
            if actual:
                causas.append(actual)
            continue
        if actual and not actual.caratula:
            c = RE_CARATULA_LOG.match(linea)
            if c:
                actual.caratula = c.group("c").strip()
    return causas


def desde_propios_txt(texto: str) -> tuple[list[Causa], list[str]]:
    """Lista manual 'numero-anio' por linea. Devuelve (causas, lineas que no se pudieron leer)."""
    causas, invalidas = [], []
    for linea in texto.splitlines():
        s = linea.strip()
        if not s or s.startswith("#"):
            continue
        e = normalizar_expte(s)
        if e is None:
            invalidas.append(s)
        else:
            causas.append(Causa(expte=e, fuentes=["propios-txt"]))
    return causas, invalidas
