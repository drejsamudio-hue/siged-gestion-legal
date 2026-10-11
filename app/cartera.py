"""Registro de causas propias: numero normalizado, carpeta canonica y alias."""
from __future__ import annotations

import json
import os
import re
import tempfile
from dataclasses import asdict, dataclass, field, replace
from datetime import datetime
from pathlib import Path

RE_NUMERO = re.compile(
    r"^\s*(?P<numero>\d{1,7})\s*[/-]\s*(?P<anio>\d{4})"
    r"(?:\s*bis\s*(?P<bis>\d+)\s*[/-]\s*(?P<bis_anio>\d{2,4}))?"
    r"(?:\s*\(\s*EX\s*(?P<ex>[^)]+?)\s*\))?\s*$",
    re.I,
)


@dataclass(frozen=True)
class Expte:
    numero: int
    anio: int
    bis: int | None = None
    bis_anio: int | None = None
    ex: str | None = None

    @property
    def clave(self) -> str:
        return f"{self.numero}/{self.anio}"

    @property
    def clave_completa(self) -> str:
        if self.bis is None:
            return self.clave
        return f"{self.clave} bis{self.bis}/{self.bis_anio:02d}"

    @property
    def texto(self) -> str:
        return self.clave_completa + (f" (EX {self.ex})" if self.ex else "")

    @property
    def sospechoso(self) -> bool:
        return len(str(self.numero)) > 6


def normalizar_expte(texto: str) -> Expte | None:
    m = RE_NUMERO.match(texto or "")
    if not m:
        return None
    g = m.groupdict()
    anio = int(g["anio"])
    if not 1980 <= anio <= 2035:
        return None
    return Expte(
        numero=int(g["numero"]),
        anio=anio,
        bis=int(g["bis"]) if g["bis"] else None,
        bis_anio=int(g["bis_anio"]) % 100 if g["bis_anio"] else None,
        ex=g["ex"].strip() if g["ex"] else None,
    )


@dataclass
class Causa:
    expte: Expte
    id_expediente: str | None = None
    caratula: str | None = None
    dependencia: str | None = None
    carpeta: str | None = None
    carpeta_prevista: str | None = None
    fuentes: list[str] = field(default_factory=list)


def fusionar(causas: list[Causa]) -> list[Causa]:
    """Une por numero completo. El primero que trae un dato gana; las fuentes se suman."""
    por_clave: dict[str, Causa] = {}
    for c in causas:
        previa = por_clave.get(c.expte.clave_completa)
        if previa is None:
            por_clave[c.expte.clave_completa] = replace(c, fuentes=list(c.fuentes))
            continue
        for campo in ("id_expediente", "caratula", "dependencia", "carpeta", "carpeta_prevista"):
            if not getattr(previa, campo) and getattr(c, campo):
                setattr(previa, campo, getattr(c, campo))
        previa.fuentes += [f for f in c.fuentes if f not in previa.fuentes]
        if c.expte.ex and not previa.expte.ex:
            previa.expte = replace(previa.expte, ex=c.expte.ex)
    return list(por_clave.values())


def posibles_erratas(causas: list[Causa]) -> list[tuple[str, str]]:
    """Pares del mismo anio cuyos numeros difieren en un solo digito (123450 vs 123460)."""
    pares = []
    for i, a in enumerate(causas):
        for b in causas[i + 1:]:
            if a.expte.anio != b.expte.anio or a.expte.bis != b.expte.bis:
                continue
            x, y = str(a.expte.numero), str(b.expte.numero)
            if len(x) == len(y) and sum(p != q for p, q in zip(x, y)) == 1:
                pares.append((a.expte.clave_completa, b.expte.clave_completa))
    return pares


def guardar(causas: list[Causa], ruta: Path) -> None:
    filas = []
    for c in causas:
        d = asdict(c)
        d["expte"] = c.expte.texto
        filas.append(d)
    texto = json.dumps({"generado": datetime.now().isoformat(timespec="seconds"), "causas": filas},
                       ensure_ascii=False, indent=2)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=ruta.parent, prefix=ruta.name + ".", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(texto)
        os.replace(tmp, ruta)
    finally:
        Path(tmp).unlink(missing_ok=True)


def cargar(ruta: Path) -> list[Causa]:
    if not ruta.exists():
        return []
    causas = []
    for d in json.loads(ruta.read_text(encoding="utf-8")).get("causas", []):
        e = normalizar_expte(d.pop("expte"))
        if e is not None:
            causas.append(Causa(expte=e, **d))
    return causas
