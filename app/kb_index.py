"""Indice del corpus juridico local (LOCAL_INDEX.json): que fallos, normas y doctrina hay y por area."""
from __future__ import annotations

import argparse
import json
import os
import re
import unicodedata
from datetime import datetime
from pathlib import Path

from config import CORPUS

AREA_NORMAS: dict[str, list[str]] = {
    "consumo": ["24240"],
    "honorarios": ["xii-n4"],
    "ejecucion": ["xii-n27"],
    "laboral": ["20744"],
    "administrativo": ["i-n89", "i-n95"],
}

_SEP = r"[\s_\-–—]*"
_RX_ROMANA = re.compile(rf"(?<![A-Za-z0-9])([IVX]+){_SEP}N\s*[°º.o]*\s*(\d+)(?!\d)", re.I)
_RX_NACIONAL = re.compile(rf"(?<![A-Za-z0-9])ley{_SEP}(?:n(?:ro|o)?\.?[°º]?\s*)?(\d{{1,3}}(?:\.\d{{3}})+|\d+)(?![\d.]*\d|/\d)", re.I)
_RX_YAML = re.compile(r'^([\w\-]+):\s*(.*?)\s*$')
_RX_BULLET = re.compile(r"^-\s+\*\*([\w\-]+):\*\*\s*(.*?)\s*$")
_RX_ARTICULO = re.compile(r"^\W*art[ií]culo\s+\d|^\W*art\.\s*\d", re.I | re.M)


def _ids(texto: str) -> list[str]:
    hallados: list[tuple[int, str]] = []
    for m in _RX_ROMANA.finditer(texto):
        hallados.append((m.start(), f"{m.group(1).lower()}-n{int(m.group(2))}"))
    for m in _RX_NACIONAL.finditer(texto):
        hallados.append((m.start(), m.group(1).replace(".", "")))
    vistos: list[str] = []
    for _, i in sorted(hallados):
        if i not in vistos:
            vistos.append(i)
    return vistos


def empieza_ordenanza(texto: str) -> bool:
    sin = "".join(c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn")
    return sin.lstrip().lower().startswith("ordenanza")


def norma_id(texto: str) -> str | None:
    ids = _ids(texto)
    return ids[0] if ids else None


def leer_ficha(path: Path) -> dict[str, str]:
    lineas = path.read_text(encoding="utf-8", errors="replace").splitlines()
    ficha: dict[str, str] = {}
    if lineas and lineas[0].strip() == "---":
        for linea in lineas[1:]:
            if linea.strip() == "---":
                break
            m = _RX_YAML.match(linea)
            if m:
                ficha[m.group(1)] = m.group(2).strip().strip('"').strip("'")
        return ficha
    for linea in lineas:
        m = _RX_BULLET.match(linea)
        if m:
            ficha[m.group(1)] = m.group(2)
        elif ficha and linea.strip() and not linea.startswith("- "):
            break
    return ficha


def _rel(p: Path, corpus: Path) -> str:
    return p.relative_to(corpus).as_posix()


def _md(directorio: Path) -> list[Path]:
    return sorted(directorio.rglob("*.md")) if directorio.is_dir() else []


def _areas_de_doctrina(path: Path, validas: set[str]) -> list[str]:
    texto = path.read_text(encoding="utf-8", errors="replace")
    return [a for a in re.findall(r"^##\s+(.+?)\s*$", texto, re.M) if a.strip().lower() in validas]


def construir(corpus: Path) -> dict:
    corpus = Path(corpus)
    avisos: list[str] = []
    fallos: dict[str, dict] = {}
    for p in _md(corpus / "fallos"):
        ficha = leer_ficha(p)
        if not ficha:
            avisos.append(f"fallo sin ficha, omitido: {_rel(p, corpus)}")
            continue
        slug = p.stem
        if slug in fallos:
            avisos.append(f"slug duplicado, omitido: {_rel(p, corpus)}")
            continue
        fallos[slug] = {
            "ruta": _rel(p, corpus),
            "area": (ficha.get("area") or ficha.get("rama") or "general").strip().lower(),
            "tema": ficha.get("tema", ""),
            "tribunal": ficha.get("tribunal", ""),
            "fecha": ficha.get("fecha", ""),
            "normas": _ids(ficha.get("normas", "")),
        }

    normas: dict[str, dict] = {}
    for p in _md(corpus / "legislacion"):
        if p.stem.lower().startswith("ordenanza-"):
            continue
        nid = norma_id(p.stem)
        if not nid:
            avisos.append(f"norma con nombre no reconocido, omitida: {_rel(p, corpus)}")
            continue
        if nid in normas:
            avisos.append(f"norma duplicada {nid}, omitida: {_rel(p, corpus)}")
            continue
        ficha = leer_ficha(p)
        try:
            arts = int(ficha["articulos"])
        except (KeyError, ValueError):
            arts = len(_RX_ARTICULO.findall(p.read_text(encoding="utf-8", errors="replace")))
        normas[nid] = {"ruta": _rel(p, corpus), "titulo": ficha.get("titulo", ""), "articulos": arts}

    nombres = set(AREA_NORMAS) | {f["area"] for f in fallos.values()}
    areas = {a: {"fallos": [], "normas": [], "doctrina": []} for a in sorted(nombres)}
    for f in fallos.values():
        areas[f["area"]]["fallos"].append(f["ruta"])
    for area, ids in AREA_NORMAS.items():
        areas[area]["normas"] = [i for i in ids if i in normas]
    for p in _md(corpus / "doctrina"):
        for a in _areas_de_doctrina(p, nombres):
            areas[a.strip().lower()]["doctrina"].append(_rel(p, corpus))

    sin_cobertura = [
        a for a, d in areas.items()
        if not d["fallos"] or any(i not in normas for i in AREA_NORMAS.get(a, []))
    ]
    return {
        "version": 1,
        "raiz": str(corpus),
        "actualizado": datetime.now().isoformat(timespec="seconds"),
        "areas": areas,
        "normas": normas,
        "fallos": fallos,
        "cobertura": {
            "total_fallos": len(fallos),
            "normas_disponibles": sorted(normas),
            "areas_sin_cobertura": sin_cobertura,
        },
        "avisos": avisos,
    }


def rebuild(corpus: Path = CORPUS) -> Path:
    corpus = Path(corpus)
    destino = corpus / "LOCAL_INDEX.json"
    tmp = destino.with_name(destino.name + ".tmp")
    tmp.write_text(json.dumps(construir(corpus), ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, destino)
    return destino


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Reconstruye LOCAL_INDEX.json del corpus")
    ap.add_argument("--corpus", type=Path, default=CORPUS)
    ruta = rebuild(ap.parse_args().corpus)
    print(ruta)
