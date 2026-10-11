"""Fase 2 - Consolidacion de expedientes.

Lee cada PDF de los tres pools, extrae numero de expediente y caratula,
detecta pertenencia (matricula o apellido) y mueve a:
  01_Expedientes/<AAAA-actor-demandado>/{00_escritos_propios|01_siged}
  02_Jurisprudencia/_pendientes_de_fichar   (referencia -> la trata la fase 3)
  _INBOX/_sin_texto                         (PDF escaneado, sin capa de texto)
  _INBOX/sin_expediente                     (propio pero sin numero)
Nada se borra.
"""
from __future__ import annotations

import csv
import re
import shutil
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from extractor import extraer as extract_text  # noqa: E402

from config import APELLIDOS_PROPIOS, BASE  # noqa: E402
SISTEMA = BASE / "_SISTEMA"
POOLS = [
    
]

EXPTE_PATRONES = [
    re.compile(r"(?i)\bEXPTE\.?\s*(?:N[\u00ba\u00b0ro\.]*\s*)?(\d{1,6})\s*/\s*(\d{4})"),
    re.compile(r"(?i)\bEXPEDIENTE\s*(?:N[\u00ba\u00b0ro\.]*\s*)?(\d{1,6})\s*/\s*(\d{4})"),
    re.compile(r"(?i)\bexpte[_\-\s]*(\d{4,6})[\-_](\d{4})"),
    re.compile(r"\b(\d{4,6})\s*/\s*(20\d{2})\b"),
]
CARATULA_RE = re.compile(
    r"(?i)([A-Z\u00c1\u00c9\u00cd\u00d3\u00da\u00d1][\w\u00c1\u00c9\u00cd\u00d3\u00da\u00d1\u00e1\u00e9\u00ed\u00f3\u00fa\u00f1\.\s,]{1,60}?)\s+c/\s*"
    r"([A-Z\u00c1\u00c9\u00cd\u00d3\u00da\u00d1][\w\u00c1\u00c9\u00cd\u00d3\u00da\u00d1\u00e1\u00e9\u00ed\u00f3\u00fa\u00f1\.\s,]{1,60}?)(?=\s+s/|\s*$|\n)"
)
OWNER_RE = (re.compile(r"(?i)\b(?:" + "|".join(map(re.escape, APELLIDOS_PROPIOS)) + r")\b")
            if APELLIDOS_PROPIOS else re.compile(r"(?!)"))
MATRICULA_RE = re.compile(r"(?i)\bt(?:omo)?\.?\s*\d{1,4}\s*[-,/]?\s*f(?:olio)?\.?\s*\d{1,4}\b")
JURIS_RE = re.compile(
    r"(?i)\b(superior tribunal|corte suprema|c\u00e1mara de apelaciones|camara de apelaciones|"
    r"sala\s+[ivx]+|sumario|doctrina|fallo plenario|jurisprudencia|microjuris|la ley online|"
    r"thomson reuters|el dial|elDial)\b"
)


STOP = {"de", "la", "el", "los", "las", "del", "y", "sa", "s.a", "srl", "s.r.l"}


def slug(texto: str, maxw: int = 4) -> str:
    t = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    t = re.sub(r"[^a-zA-Z0-9\s]", " ", t).lower()
    palabras = [p for p in t.split() if p and p not in STOP]
    return "-".join(palabras[:maxw]) or "sin-nombre"


def buscar_expte(texto: str) -> str | None:
    encontrados: Counter = Counter()
    for pat in EXPTE_PATRONES:
        for m in pat.finditer(texto[:20000]):
            num, anio = m.group(1), m.group(2)
            if 2000 <= int(anio) <= 2030:
                encontrados[f"{int(num)}/{anio}"] += 1
        if encontrados:
            break
    return encontrados.most_common(1)[0][0] if encontrados else None


def buscar_caratula(texto: str) -> str | None:
    m = CARATULA_RE.search(texto[:20000])
    if not m:
        return None
    actor, dem = (re.sub(r"\s+", " ", g).strip(" .,") for g in m.groups())
    if len(actor) < 3 or len(dem) < 3:
        return None
    return f"{slug(actor, 3)}-{slug(dem, 3)}"


def destino_unico(dest: Path) -> Path:
    if not dest.exists():
        return dest
    i = 1
    while True:
        cand = dest.with_name(f"{dest.stem}__{i}{dest.suffix}")
        if not cand.exists():
            return cand
        i += 1


def analizar():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    archivos = []
    for pool in POOLS:
        if pool.exists():
            archivos += [p for p in pool.rglob("*") if p.is_file()]
    print(f"Analizando {len(archivos)} archivos...")

    fichas = []
    for i, p in enumerate(archivos, 1):
        if i % 250 == 0:
            print(f"  ... {i}/{len(archivos)}", flush=True)
        f = {"ruta": p, "expte": None, "caratula": None, "propio": False,
             "matricula": False, "juris": False, "texto_ok": False}
        if p.suffix.lower() == ".pdf":
            texto, err = extract_text(p)
            if texto and len(texto.strip()) > 120:
                f["texto_ok"] = True
                f["expte"] = buscar_expte(texto)
                f["caratula"] = buscar_caratula(texto)
                f["matricula"] = bool(MATRICULA_RE.search(texto))
                f["propio"] = f["matricula"] or bool(OWNER_RE.search(texto))
                f["juris"] = bool(JURIS_RE.search(texto[:6000])) and not f["propio"]
        fichas.append(f)

    # Propagacion: si alguna actuacion de un expediente es propia, todas lo son.
    # Y si a una le falta el numero pero comparte caratula, hereda el numero.
    por_caratula: dict[str, Counter] = defaultdict(Counter)
    propios_expte: set[str] = set()
    for f in fichas:
        if f["expte"] and f["caratula"]:
            por_caratula[f["caratula"]][f["expte"]] += 1
        if f["propio"] and f["expte"]:
            propios_expte.add(f["expte"])
    for f in fichas:
        if not f["expte"] and f["caratula"] and por_caratula.get(f["caratula"]):
            f["expte"] = por_caratula[f["caratula"]].most_common(1)[0][0]
        if f["expte"] in propios_expte:
            f["propio"] = True

    # Nombre canonico de carpeta por expediente
    nombre_caso: dict[str, str] = {}
    caratulas: dict[str, Counter] = defaultdict(Counter)
    for f in fichas:
        if f["expte"] and f["caratula"]:
            caratulas[f["expte"]][f["caratula"]] += 1
    for expte in {f["expte"] for f in fichas if f["expte"]}:
        anio = expte.split("/")[1]
        c = caratulas.get(expte)
        base = c.most_common(1)[0][0] if c else f"expte-{expte.replace('/', '-')}"
        nombre_caso[expte] = f"{anio}-{base}"
    return fichas, nombre_caso


def decidir(f: dict, nombre_caso: dict) -> tuple[Path, str]:
    ruta = str(f["ruta"])
    prior_ref = "\\Referencia\\" in ruta
    prior_prop = "\\Propios\\" in ruta

    if f["ruta"].suffix.lower() != ".pdf":
        return BASE / "_INBOX" / "no_pdf", "no_es_pdf"
    if not f["texto_ok"]:
        return BASE / "_INBOX" / "_sin_texto", "pdf_sin_capa_de_texto"

    propio = f["propio"] or prior_prop
    if f["expte"] and (propio or not prior_ref):
        caso = nombre_caso.get(f["expte"], f"expte-{f['expte'].replace('/', '-')}")
        sub = "00_escritos_propios" if f["matricula"] else "01_siged"
        return BASE / "01_Expedientes" / caso / sub, "expediente"
    if f["juris"] or prior_ref:
        return BASE / "02_Jurisprudencia" / "_pendientes_de_fichar", "referencia"
    if propio:
        return BASE / "_INBOX" / "propios_sin_expediente", "propio_sin_numero"
    return BASE / "_INBOX" / "sin_clasificar", "sin_senal"


def main() -> None:
    fichas, nombre_caso = analizar()
    log = SISTEMA / "FASE2_RUTEO.csv"
    conteo: Counter = Counter()
    with log.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["origen", "destino", "motivo", "expediente", "caratula",
                    "propio", "matricula", "texto_ok"])
        for f in fichas:
            carpeta, motivo = decidir(f, nombre_caso)
            src = f["ruta"]
            if not src.exists():
                continue
            carpeta.mkdir(parents=True, exist_ok=True)
            dest = destino_unico(carpeta / src.name)
            try:
                shutil.move(str(src), str(dest))
            except Exception as exc:  # noqa: BLE001
                print(f"  [ERROR] {src}: {exc}")
                continue
            conteo[motivo] += 1
            w.writerow([str(src), str(dest), motivo, f["expte"] or "",
                        f["caratula"] or "", f["propio"], f["matricula"], f["texto_ok"]])

    print("\n--- Resultado Fase 2 ---")
    for k, v in conteo.most_common():
        print(f"  {k}: {v}")
    print(f"  Expedientes distintos: {len(nombre_caso)}")
    print(f"Log -> {log}")


if __name__ == "__main__":
    main()
