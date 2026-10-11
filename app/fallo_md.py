"""Convierte fallos (PDF, DOCX, TXT) a Markdown limpio para que un lector (IA o persona) gaste menos:
texto completo con OCR si hace falta, sin encabezados/pies repetidos ni numeros de pagina, palabras cortadas
unidas, secciones marcadas (Vistos / Considerando / Resuelve) y la ficha por reglas arriba.

    python fallo_md.py ARCHIVO_O_CARPETA [...] --out CARPETA [--compacto] [--con-duplicados]
"""
from __future__ import annotations

import argparse
import hashlib
import re
import sys
from collections import Counter
from pathlib import Path

import fitz

sys.path.insert(0, str(Path(__file__).parent))
from extractor import extraer_universal, ocr_pdf  # noqa: E402
from fallos import ficha_dict  # noqa: E402

SECCIONES = [
    ("Vistos", re.compile(r"^\s*(?:autos\s+y\s+)?vistos\b[:.\s]", re.I)),
    ("Considerando", re.compile(r"^\s*(?:y\s+)?considerando\b[:.\s]?|^\s*resulta\b[:.\s]", re.I)),
    ("Resuelve", re.compile(r"^\s*(?:por\s+(?:ello|todo\s+lo\s+expuesto)|se\s+resuelve|r\s?e\s?s\s?u\s?e\s?l\s?v\s?e|fall[ao]\s*:)", re.I)),
]
RE_PAGINA = re.compile(r"^\s*(?:p[aá]g(?:ina)?\.?\s*)?\d{1,4}\s*(?:de\s*\d{1,4})?\s*$", re.I)


def texto_completo(path: Path) -> str:
    """Todas las paginas (el extractor comun lee solo el principio y el final); OCR si el PDF es escaneado."""
    if path.suffix.lower() == ".pdf":
        try:
            with fitz.open(str(path)) as doc:
                texto = "\n".join(p.get_text() for p in doc)
        except Exception:  # noqa: BLE001
            texto = ""
        if len(texto.strip()) < 100:
            texto = ocr_pdf(path, paginas=50) or ""
        return texto
    texto, _ = extraer_universal(path, max_chars=2_000_000)
    return texto or ""


def limpiar(texto: str) -> str:
    lineas = [l.rstrip() for l in texto.replace("\r", "").split("\n")]
    repetidas = {l for l, n in Counter(l.strip() for l in lineas if 4 <= len(l.strip()) <= 120).items() if n >= 3}
    out = []
    for l in lineas:
        s = l.strip()
        if not s or RE_PAGINA.match(s) or s in repetidas:
            if out and out[-1] != "":
                out.append("")
            continue
        if out and out[-1].endswith("-") and s[:1].islower():
            out[-1] = out[-1][:-1] + s
        elif out and out[-1] and not re.search(r"[.:;)\]]$", out[-1]) and s[:1].islower():
            out[-1] += " " + s
        else:
            out.append(re.sub(r"[ \t]{2,}", " ", s))
    return "\n".join(out).strip()


def a_markdown(path: Path, texto: str | None = None) -> str:
    crudo = texto if texto is not None else texto_completo(path)
    limpio = limpiar(crudo)
    ficha = ficha_dict(crudo, path.name) if crudo.strip() else {}
    cab = [f"# {path.stem}", ""]
    for k in ("tribunal", "sala", "fecha", "caratula", "expte", "tipo", "fuerza", "rama", "especialidad", "normas",
              "rechazo_formal"):
        if ficha.get(k):
            cab.append(f"- **{k}:** {ficha[k]}")
    cuerpo = []
    for linea in limpio.split("\n"):
        for titulo, rx in SECCIONES:
            if rx.match(linea):
                cuerpo += ["", f"## {titulo}", ""]
                break
        cuerpo.append(linea)
    return "\n".join(cab + ["", *cuerpo]).strip() + "\n"


def compactar(md: str, encabezado: int = 2500, final: int = 8000) -> str:
    """Ficha + encabezado + el final del fallo (ultimos considerandos y parte resolutiva), donde esta el holding.
    Ahorra ~75% en fallos largos; si el lector necesita mas, lee el .md completo."""
    if len(md) <= encabezado + final:
        return md
    return md[:encabezado] + "\n\n[... cuerpo omitido: leer el .md completo si hace falta ...]\n\n" + md[-final:]


def huella(md: str) -> str:
    cuerpo = md.split("\n", 1)[-1]
    return hashlib.sha1(re.sub(r"\W+", "", cuerpo.lower()).encode()).hexdigest()


def convertir(entradas: list[Path], salida: Path, sin_duplicados: bool = True, compacto: bool = False) -> dict:
    salida.mkdir(parents=True, exist_ok=True)
    vistos: dict[str, str] = {}
    res = {"convertidos": 0, "duplicados": 0, "chars_antes": 0, "chars_despues": 0}
    archivos = [p for e in entradas for p in ([e] if e.is_file() else sorted(e.rglob("*"))) if p.is_file()]
    for p in archivos:
        crudo = texto_completo(p)
        md = a_markdown(p, crudo)
        h = huella(md)
        if sin_duplicados and h in vistos:
            res["duplicados"] += 1
            continue
        vistos[h] = p.name
        (salida / f"{p.stem}.md").write_text(md, encoding="utf-8")
        if compacto:
            md = compactar(md)
            (salida / f"{p.stem}.compacto.md").write_text(md, encoding="utf-8")
        res["convertidos"] += 1
        res["chars_antes"] += len(crudo)
        res["chars_despues"] += len(md)
    return res


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("entradas", nargs="+", type=Path)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--con-duplicados", action="store_true")
    ap.add_argument("--compacto", action="store_true", help="ademas, version corta: encabezado + final del fallo")
    a = ap.parse_args()
    r = convertir(a.entradas, a.out, not a.con_duplicados, a.compacto)
    ahorro = 1 - r["chars_despues"] / max(1, r["chars_antes"])
    print(f"Convertidos: {r['convertidos']} | duplicados omitidos: {r['duplicados']} | "
          f"caracteres: {r['chars_antes']:,} -> {r['chars_despues']:,} ({ahorro:.0%} menos)")


if __name__ == "__main__":
    main()
