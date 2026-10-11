"""Convierte el PDF de una ley a Markdown dividido por articulo (`## Articulo N`) con front-matter simple,
para el corpus local de legislacion (`legislacion/**/ley-{id}.md`)."""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import fallo_md  # noqa: E402

RE_ARTICULO = re.compile(
    r"^\s*art(?:[ií]culo|\.)?\s*(\d+)\s*[º°o]?\s*(bis|ter|qu[aá]ter|quinquies)?\b[\s.\-–:]*(.*)$", re.I
)


def a_markdown_norma(texto: str, titulo: str, id_norma: str) -> str:
    previo: list[str] = []
    arts: list[tuple[str, list[str]]] = []
    for linea in fallo_md.limpiar(texto).split("\n"):
        m = RE_ARTICULO.match(linea)
        if m:
            nombre = m.group(1) + (f" {m.group(2).lower()}" if m.group(2) else "")
            arts.append((nombre, [m.group(3).strip()] if m.group(3).strip() else []))
        elif arts:
            arts[-1][1].append(linea)
        else:
            previo.append(linea)
    titulo_q = titulo.replace('"', "'")
    partes = ["---", f'titulo: "{titulo_q}"', f'id: "{id_norma}"', f"articulos: {len(arts)}", "---", ""]
    if "".join(previo).strip():
        partes += ["\n".join(previo).strip(), ""]
    for nombre, cuerpo in arts:
        partes += [f"## Artículo {nombre}", "", "\n".join(cuerpo).strip(), ""]
    return "\n".join(partes).rstrip() + "\n"


def convertir_norma(pdf: Path, destino: Path, id_norma: str, prefijo: str = "ley") -> dict:
    texto = fallo_md.texto_completo(pdf)
    md = a_markdown_norma(texto, pdf.stem, id_norma)
    destino.mkdir(parents=True, exist_ok=True)
    ruta = destino / f"{prefijo}-{id_norma}.md"
    ruta.write_text(md, encoding="utf-8")
    n = sum(1 for l in md.split("\n") if l.startswith("## Artículo "))
    return {"ruta": ruta, "articulos": n, "chars": len(md), "sin_articulos": n == 0}
