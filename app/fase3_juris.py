"""Fase 3 - Jurisprudencia, doctrina y legislacion.

Toma la cola 02_Jurisprudencia/_pendientes_de_fichar y la reparte por tribunal,
area doctrinaria o cuerpo normativo. Lo que no da senal clara queda en la cola:
es preferible una cola honesta a una carpeta mal poblada.
"""
from __future__ import annotations

import csv
import re
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from extractor import extraer  # noqa: E402
from fase2_expedientes import destino_unico, slug  # noqa: E402

from config import BASE  # noqa: E402
SISTEMA = BASE / "_SISTEMA"
COLA = BASE / "02_Jurisprudencia" / "_pendientes_de_fichar"

MISIONES = re.compile(r"(?i)\bmisiones\b|\bposadas\b|\bober[a\u00e1]\b|eldorado|puerto iguaz")
STJ = re.compile(r"(?i)superior tribunal de justicia")
CSJN = re.compile(r"(?i)corte suprema de justicia de la naci[o\u00f3]n|\bC\.?S\.?J\.?N\.?\b")
CAM_NAC = re.compile(r"(?i)c[a\u00e1]mara nacional|\bCNCom\b|\bCNCiv\b|\bCNTrab\b|\bCNFed\b")
CAM = re.compile(r"(?i)c[a\u00e1]mara de apelaciones|c[a\u00e1]mara civil|c[a\u00e1]mara laboral|c[a\u00e1]mara penal|tribunal de apelaciones")
LABORAL = re.compile(r"(?i)\blaboral\b|del trabajo|ley de contrato de trabajo|\b20\.?744\b|despido|\b23\.?551\b")
PENAL = re.compile(r"(?i)\bpenal\b|\bcriminal\b|correccional|c[o\u00f3]digo procesal penal")
CIVIL = re.compile(r"(?i)civil y comercial|\bcivil\b|\bcomercial\b|familia")
LEGIS = re.compile(r"(?i)^\s*(ley|decreto|resoluci[o\u00f3]n|disposici[o\u00f3]n|ordenanza|c[o\u00f3]digo)\s+(n[\u00ba\u00b0]?\s*)?[\divxlc]")
FORMULA_NORMA = re.compile(
    r"(?i)sancion(a|an) con fuerza de\s+ley|\bdecreta\s*:|\bdispone\s*:|\bordena\s*:"
    r"|d[eé]se a la direcci[oó]n nacional del registro oficial")
ARTICULO_1 = re.compile(r"(?i)\bart[ií]culo\s+1\s*[º°o]?\s*[.:\-–]")
PROVINCIA_MISIONES = re.compile(r"(?i)provincia de misiones|c[aá]mara de representantes|\bley\s+[ivxlc]+\s*[-–]\s*n")
FALLO = re.compile(r"(?i)\bsentencia\b|\bfallo\b|\bacuerdo\b|\bresuelve\b|\bvistos\b|considerando|\bsumario\b|voto del")

AREAS = [
    ("consumo", re.compile(r"(?i)\b24\.?240\b|derecho del consumidor|relaci[o\u00f3]n de consumo|da[n\u00f1]o punitivo|usuario")),
    ("honorarios", re.compile(r"(?i)honorarios|arancel|\bXII\s*-?\s*N[\u00ba\u00b0]?\s*4\b|regulaci[o\u00f3]n de honorarios|\b27\.?423\b")),
    ("laboral", LABORAL),
    ("administrativo", re.compile(r"(?i)contencioso[\s-]administrativo|empleo p[u\u00fa]blico|acto administrativo|agotamiento de la v[i\u00ed]a")),
    ("procesal", re.compile(r"(?i)caducidad de instancia|recurso de apelaci[o\u00f3]n|excepci[o\u00f3]n de|c[o\u00f3]digo procesal|carga de la prueba|medida cautelar")),
]


def area_doctrina(texto: str) -> str:
    for nombre, pat in AREAS:
        if pat.search(texto):
            return nombre
    return "general"


def clasificar(texto: str) -> tuple[Path, str]:
    cab = texto[:4000]
    mis = bool(MISIONES.search(cab))

    if (LEGIS.search(cab.lstrip()[:200]) and not FALLO.search(cab)) or (
            FORMULA_NORMA.search(cab) and ARTICULO_1.search(cab)):
        sub = "misiones" if PROVINCIA_MISIONES.search(cab) else "nacion"
        return BASE / "04_Legislacion" / sub, f"legislacion_{sub}"

    if CSJN.search(cab):
        return BASE / "02_Jurisprudencia" / "nacional" / "csjn", "csjn"
    if CAM_NAC.search(cab):
        return BASE / "02_Jurisprudencia" / "nacional" / "camaras", "camara_nacional"
    if STJ.search(cab) and mis:
        return BASE / "02_Jurisprudencia" / "misiones" / "stj", "stj_misiones"
    if CAM.search(cab) and mis:
        if LABORAL.search(cab):
            return BASE / "02_Jurisprudencia" / "misiones" / "camara-laboral", "camara_laboral"
        if PENAL.search(cab):
            return BASE / "02_Jurisprudencia" / "misiones" / "camara-penal", "camara_penal"
        if CIVIL.search(cab):
            return BASE / "02_Jurisprudencia" / "misiones" / "camara-civil", "camara_civil"
        return BASE / "02_Jurisprudencia" / "misiones" / "otros", "camara_misiones_sin_fuero"
    if STJ.search(cab) or CAM.search(cab):
        return BASE / "02_Jurisprudencia" / "nacional" / "otros", "tribunal_otra_jurisdiccion"
    if FALLO.search(cab):
        destino = "misiones" if mis else "nacional"
        return BASE / "02_Jurisprudencia" / destino / "otros", f"fallo_sin_tribunal_{destino}"

    area = area_doctrina(texto[:12000])
    return BASE / "03_Doctrina" / area, f"doctrina_{area}"


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    archivos = [p for p in COLA.rglob("*") if p.is_file()]
    print(f"Cola: {len(archivos)} archivos", flush=True)
    conteo: dict[str, int] = {}
    log = SISTEMA / "FASE3_RUTEO.csv"
    with log.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["origen", "destino", "motivo"])
        for i, p in enumerate(archivos, 1):
            if i % 200 == 0:
                print(f"  ... {i}/{len(archivos)}", flush=True)
            if p.suffix.lower() == ".pdf":
                texto, _ = extraer(p)
            else:
                try:
                    texto = p.read_text(encoding="utf-8", errors="ignore")
                except Exception:  # noqa: BLE001
                    texto = None
            if not texto or len(texto.strip()) < 120:
                continue  # se queda en la cola: sin texto no hay clasificacion honesta
            carpeta, motivo = clasificar(texto)
            carpeta.mkdir(parents=True, exist_ok=True)
            dest = destino_unico(carpeta / p.name)
            try:
                shutil.move(str(p), str(dest))
            except Exception as exc:  # noqa: BLE001
                print(f"  [ERROR] {p}: {exc}")
                continue
            conteo[motivo] = conteo.get(motivo, 0) + 1
            w.writerow([str(p), str(dest), motivo])

    quedan = len([p for p in COLA.rglob("*") if p.is_file()])
    print("\n--- Resultado Fase 3 ---")
    for k, v in sorted(conteo.items(), key=lambda x: -x[1]):
        print(f"  {k}: {v}")
    print(f"  Quedan en la cola (sin texto legible): {quedan}")
    print(f"Log -> {log}")


if __name__ == "__main__":
    main()
