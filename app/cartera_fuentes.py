"""Lector de la lista manual de causas propias."""
from __future__ import annotations

from cartera import Causa, normalizar_expte


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
