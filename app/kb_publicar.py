"""Publica al corpus local lo que la ingesta acaba de rutear (fallos y normas)."""
from __future__ import annotations

from pathlib import Path

import fallo_md
import kb_index
import norma_md
from config import CORPUS

_AMBITO = {"legislacion_misiones": "misiones", "legislacion_nacion": "nacion"}


def publicar(archivo: Path, motivo: str, detalle: str, corpus: Path = CORPUS) -> Path | None:
    if motivo == "jurisprudencia":
        destino = corpus / "fallos" / f"{archivo.stem}.md"
        if destino.exists():
            return None
        md = fallo_md.a_markdown(archivo)
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(md, encoding="utf-8")
        return destino
    if motivo == "rama" and detalle in _AMBITO:
        id_norma = kb_index.norma_id(archivo.stem) or kb_index.norma_id(fallo_md.texto_completo(archivo)[:2000])
        if not id_norma:
            return None
        ordenanza = kb_index.empieza_ordenanza(archivo.stem) or kb_index.empieza_ordenanza(
            fallo_md.texto_completo(archivo)[:2000])
        prefijo = "ordenanza" if ordenanza else "ley"
        carpeta = corpus / "legislacion" / ("municipal" if ordenanza else _AMBITO[detalle])
        if (carpeta / f"{prefijo}-{id_norma}.md").exists():
            return None
        return norma_md.convertir_norma(archivo, carpeta, id_norma, prefijo)["ruta"]
    return None
