"""Alias por apellido del actor para las causas de la cartera."""
from __future__ import annotations

from pathlib import Path

from cartera import Causa
from ingesta import _PALABRAS_GENERICAS

# Apellidos muy comunes o palabras que aparecen en fallos y documentos ajenos: un alias asi se lleva lo que no es.
NO_APELLIDOS = {"comisaria", "fiscalia", "juzgado", "pizza", "sanchez", "gonzalez", "rodriguez", "fernandez",
                "lopez", "martinez", "gomez", "perez", "garcia", "romero", "benitez", "ramirez", "ojeda", "acosta"}


def _apellido(carpeta: str) -> str | None:
    for parte in carpeta.split("-")[1:]:
        if len(parte) >= 5 and not parte.isdigit() and parte not in _PALABRAS_GENERICAS and parte not in NO_APELLIDOS:
            return parte
        break
    return None


def aliases_desde_cartera(causas: list[Causa], casos_dir: Path) -> tuple[list[dict], list[str]]:
    """Un alias por apellido, solo si ese apellido aparece en una unica carpeta de 01_Expedientes.

    Devuelve (aliases, apellidos ambiguos). Las causas con apellido repetido se distinguen
    por numero de expediente, no por nombre.
    """
    carpetas = [d.name for d in casos_dir.iterdir() if d.is_dir()]
    aliases, ambiguos, vistos = [], [], set()
    for c in causas:
        if not c.carpeta:
            continue
        principal = c.carpeta.split("/")[0]
        if principal in vistos:
            continue
        vistos.add(principal)
        ap = _apellido(principal)
        if not ap:
            continue
        if sum(1 for n in carpetas if ap in n.split("-")[1:]) != 1:
            ambiguos.append(ap)
            continue
        aliases.append({
            "pattern": rf"(?<![a-z]){ap}(?![a-z])",
            "caso": principal,
            "expte": c.expte.clave,
            "origen": "cartera",
        })
    return aliases, sorted(set(ambiguos))
