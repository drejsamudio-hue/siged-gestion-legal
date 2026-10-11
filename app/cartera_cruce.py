"""Cruce de la cartera con las carpetas de 01_Expedientes: que existe, que falta, que renombrar."""
from __future__ import annotations

import csv
import re
from dataclasses import dataclass, replace
from datetime import datetime
from pathlib import Path

from cartera import Causa
from fase2_expedientes import slug

SUBCARPETAS = ("00_escritos_propios", "01_siged")
RE_CARPETA_POR_NUMERO = re.compile(r"^\d{4}-expte-\d+-\d{4}$")


@dataclass
class Cruce:
    causa: Causa
    carpeta: str | None
    via: str
    accion: str
    destino: str | None = None
    nota: str = ""


def nombre_carpeta(c: Causa) -> str:
    """AAAA-actor-demandado a partir de la caratula; sin caratula, AAAA-expte-N-AAAA."""
    base = f"{c.expte.anio}-"
    if c.caratula:
        texto = re.split(r"\s+[—–]\s+", c.caratula.strip())[0]
        m = re.match(r"^(?P<a>.+?)\s+c\s*/\s*(?P<d>.+?)(?:\s+s\s*/.*)?$", texto, re.I)
        if m:
            return f"{base}{slug(m['a'], 3)}-{slug(m['d'], 3)}"
        m = re.match(r"^(?P<a>.+?)\s+s/\s*(?P<b>.+)$", texto, re.I)
        if m:
            return f"{base}{slug(m['a'], 3)}-{slug(m['b'], 2)}"
    return f"{base}expte-{c.expte.numero}-{c.expte.anio}"


def carpeta_existente(c: Causa, casos_dir: Path, mapa: dict[str, str]) -> tuple[str | None, str]:
    if c.carpeta and (casos_dir / c.carpeta).is_dir():
        return c.carpeta, "cartera"
    if c.carpeta_prevista and (casos_dir / c.carpeta_prevista).is_dir():
        return c.carpeta_prevista, "prevista"
    nombre = mapa.get(c.expte.clave)
    if nombre and (casos_dir / nombre).is_dir():
        return nombre, "mapa"
    clave = f"expte-{c.expte.numero}-{c.expte.anio}"
    for d in sorted(casos_dir.iterdir()):
        if d.is_dir() and clave in d.name:
            return d.name, "nombre"
    return None, "sin_carpeta"


def subcarpeta_bis(c: Causa) -> str:
    return f"bis{c.expte.bis}-{c.expte.bis_anio:02d}"


def cruzar(causas: list[Causa], casos_dir: Path, mapa: dict[str, str]) -> list[Cruce]:
    """Los principales primero; cada bis va en una subcarpeta bisN-AA dentro de la carpeta del principal."""
    out = []
    propuestas_asignadas: dict[str, str] = {}
    base_final: dict[str, str | None] = {}
    for c in (c for c in causas if c.expte.bis is None):
        carpeta, via = carpeta_existente(c, casos_dir, mapa)
        propuesta = nombre_carpeta(c)
        if c.expte.sospechoso:
            out.append(Cruce(c, carpeta, via, "revisar", nota="numero de 7 digitos: no parece de SIGED Misiones"))
            base_final[c.expte.clave] = None
        elif carpeta is None:
            if propuesta in propuestas_asignadas and propuestas_asignadas[propuesta] != c.expte.clave:
                out.append(Cruce(c, None, via, "revisar", nota="otro expediente propone el mismo nombre de carpeta"))
                base_final[c.expte.clave] = None
            elif (casos_dir / propuesta).exists():
                out.append(Cruce(c, None, via, "revisar", nota="ya existe una carpeta con ese nombre que no corresponde al numero"))
                base_final[c.expte.clave] = None
            else:
                propuestas_asignadas[propuesta] = c.expte.clave
                out.append(Cruce(c, None, via, "crear", propuesta))
                base_final[c.expte.clave] = propuesta
        elif RE_CARPETA_POR_NUMERO.match(carpeta) and carpeta != propuesta:
            out.append(Cruce(c, carpeta, via, "renombrar", propuesta))
            base_final[c.expte.clave] = propuesta
        else:
            out.append(Cruce(c, carpeta, via, "ok"))
            base_final[c.expte.clave] = carpeta

    for c in (c for c in causas if c.expte.bis is not None):
        if c.expte.clave in base_final:
            base, via = base_final[c.expte.clave], "principal"
        else:
            base, via = carpeta_existente(replace(c, carpeta=None, carpeta_prevista=None), casos_dir, mapa)
            if base is None:
                base, via = nombre_carpeta(c), "sin_carpeta"
        if base is None or c.expte.sospechoso:
            out.append(Cruce(c, None, via, "revisar", nota="el expediente principal requiere revision"))
            continue
        destino = f"{base}/{subcarpeta_bis(c)}"
        if (casos_dir / destino).is_dir():
            out.append(Cruce(c, destino, via, "ok"))
        else:
            out.append(Cruce(c, None, via, "crear", destino))
    return out


def carpetas_sin_causa(casos_dir: Path, cruces: list[Cruce]) -> list[str]:
    usadas = {n.split("/")[0] for x in cruces for n in (x.carpeta, x.destino) if n}
    return sorted(d.name for d in casos_dir.iterdir() if d.is_dir() and d.name not in usadas)


def aplicar(cruces: list[Cruce], casos_dir: Path, log_csv: Path) -> tuple[list[tuple], list[tuple]]:
    """Crea las carpetas que faltan y renombra las que llevan solo el numero. No fusiona nunca."""
    hechos: list[tuple] = []
    conflictos: list[tuple] = []
    creadas: dict[str, str] = {}
    log_csv.parent.mkdir(parents=True, exist_ok=True)
    nuevo = not log_csv.exists()

    for x in sorted(cruces, key=lambda x: x.causa.expte.bis is not None):
        if x.accion == "crear":
            if x.destino in creadas:
                if creadas[x.destino] == x.causa.expte.clave:
                    x.causa.carpeta = x.destino
                    continue
                else:
                    conflictos.append(("", x.destino, "otro expediente propone el mismo nombre"))
                    continue
            if (casos_dir / x.destino).exists():
                conflictos.append(("", x.destino, "ya existe una carpeta con ese nombre"))
                continue
            try:
                for base in {x.destino, x.destino.split("/")[0]}:
                    for sub in SUBCARPETAS:
                        (casos_dir / base / sub).mkdir(parents=True, exist_ok=True)
            except OSError as exc:
                conflictos.append(("", x.destino, str(exc)))
                continue
            creadas[x.destino] = x.causa.expte.clave
            x.causa.carpeta = x.destino
            x.causa.carpeta_prevista = None
            hechos.append(("crear", "", x.destino))
            with log_csv.open("a", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                if nuevo:
                    w.writerow(["fecha", "accion", "origen", "destino"])
                    nuevo = False
                ahora = datetime.now().isoformat(timespec="seconds")
                w.writerow([ahora, "crear", "", x.destino])
        elif x.accion == "renombrar":
            origen, destino = casos_dir / x.carpeta, casos_dir / x.destino
            if not origen.exists() and destino.exists():
                x.causa.carpeta = x.destino
                continue
            if destino.exists():
                conflictos.append((x.carpeta, x.destino, "el destino ya existe"))
                continue
            try:
                origen.rename(destino)
            except OSError as exc:
                conflictos.append((x.carpeta, x.destino, str(exc)))
                continue
            x.causa.carpeta = x.destino
            hechos.append(("renombrar", x.carpeta, x.destino))
            with log_csv.open("a", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                if nuevo:
                    w.writerow(["fecha", "accion", "origen", "destino"])
                    nuevo = False
                ahora = datetime.now().isoformat(timespec="seconds")
                w.writerow([ahora, "renombrar", x.carpeta, x.destino])
        elif x.accion == "ok" and x.carpeta:
            x.causa.carpeta = x.carpeta
    return hechos, conflictos


def reporte_md(cruces: list[Cruce], sin_causa: list[str], erratas: list[tuple[str, str]],
               invalidas: list[str]) -> str:
    def tabla(filas):
        return "\n".join(filas) if filas else "_ninguna_"

    por_accion = {a: [x for x in cruces if x.accion == a] for a in ("ok", "crear", "renombrar", "revisar")}
    lineas = [
        "# Cruce cartera propia vs. carpetas",
        "",
        f"- Causas en cartera: **{len(cruces)}**",
        f"- Con carpeta y sin cambios: **{len(por_accion['ok'])}**",
        f"- Sin carpeta (se crearian): **{len(por_accion['crear'])}**",
        f"- Carpeta con solo el numero (se renombrarian): **{len(por_accion['renombrar'])}**",
        f"- A revisar a mano: **{len(por_accion['revisar'])}**",
        f"- Carpetas de 01_Expedientes que no estan en la cartera: **{len(sin_causa)}**",
        "",
        "## Asignadas (recibiran archivos con confianza alta)",
        tabla([f"- {x.causa.expte.clave_completa} -> `{x.carpeta}` ({x.via})" for x in por_accion["ok"]]),
        "",
        "## Se crearian",
        tabla([f"- {x.causa.expte.clave_completa} -> `{x.destino}`" for x in por_accion["crear"]]),
        "",
        "## Se renombrarian",
        tabla([f"- `{x.carpeta}` -> `{x.destino}` ({x.causa.expte.clave_completa})" for x in por_accion["renombrar"]]),
        "",
        "## A revisar a mano",
        tabla([f"- {x.causa.expte.clave_completa}: {x.nota}" for x in por_accion["revisar"]]),
        "",
        "## Posibles erratas (numeros que difieren en un digito)",
        tabla([f"- {a} vs {b}" for a, b in erratas]),
        "",
        "## Lineas de la lista manual que no se pudieron leer",
        tabla([f"- `{s}`" for s in invalidas]),
    ]
    return "\n".join(lineas) + "\n"
