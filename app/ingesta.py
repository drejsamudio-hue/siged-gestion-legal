"""Ingesta continua: rutea lo que haya en _INBOX hacia la estructura.

Uso:
    python ingesta.py            # rutea todo lo que encuentre en _INBOX
    python ingesta.py --dry-run  # muestra a donde iria cada archivo, sin mover
    python ingesta.py --src DIR  # rutea desde otra carpeta (ej: una carpeta de descargas)
    python ingesta.py --csv RUTA # ademas guarda las propuestas (destino, motivo, confianza)
    python ingesta.py --omitir expediente_nuevo   # esos motivos no se mueven (solo motivos conocidos, ver MOTIVOS)
    python ingesta.py --src DIR --incluir-no-clasificados  # tambien saca lo no reconocido a _INBOX
    python ingesta.py --aplicar-csv RUTA  # mueve lo aprobado en un CSV de simulacion (accion=mover), sin reclasificar

Soporta PDF, .txt, .md, .docx, .doc. Cada movimiento queda registrado en
_SISTEMA/INGESTA_RUTEO.csv (origen, destino) para poder deshacerlo.
Orden de decision: cartera propia (id de SIGED o numero) -> expediente -> alias ->
jurisprudencia/legislacion -> nombre de partes -> doctrina (rama, especialidad, tipo).

Confianza: "alta" solo cuando hay una senal fuerte. Un texto con forma de sentencia que termina como
doctrina, o que cita un tribunal pero no tiene marcas de sentencia, sale como maximo "media". La cartera
solo rutea a carpetas que existen en disco; un cartera.json o aliases_cartera.json ilegible se ignora
con un aviso en stderr.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import shutil
import sys
import unicodedata
from collections import Counter
from datetime import datetime
from pathlib import Path, PureWindowsPath
from typing import NamedTuple

sys.path.insert(0, str(Path(__file__).parent))
from cartera import cargar as cargar_cartera  # noqa: E402
from doctrina import clasificar_doctrina, ruta_doctrina, tema_de  # noqa: E402
from extractor import extraer_universal, paginas_pdf  # noqa: E402
from fase2_expedientes import (  # noqa: E402
    JURIS_RE, MATRICULA_RE, OWNER_RE, buscar_caratula, buscar_expte, destino_unico,
)
from fase3_juris import FALLO, clasificar  # noqa: E402
from fase6b_renombres import RENOMBRES  # noqa: E402

from config import APELLIDOS_PROPIOS, BASE  # noqa: E402
import kb_index  # noqa: E402
import kb_publicar  # noqa: E402
INBOX = BASE / "_INBOX"
CASOS = BASE / "01_Expedientes"
SISTEMA = BASE / "_SISTEMA"
RUTEO_CSV = SISTEMA / "INGESTA_RUTEO.csv"
TANDAS_CSV = SISTEMA / "TANDAS.csv"
CARTERA_JSON = SISTEMA / "cartera.json"
ALIAS_CARTERA = SISTEMA / "aliases_cartera.json"
ALIAS_FILE = SISTEMA / "aliases.json"

IGNORAR = {"_sin_texto", "sin_texto", "sin_clasificar", "formato_desconocido",
           "desde_Organizado", "expediente_dudoso", "no_pdf"}

FORMATOS_CON_TEXTO = {".pdf", ".txt", ".md", ".docx", ".doc", ".csv", ".log"}
FORMATOS_SIN_TEXTO = {
    ".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp",
    ".ogg", ".mp3", ".mp4", ".wav",
    ".rar", ".zip", ".7z",
    ".xlsx", ".xls", ".pptx",
    ".lnk", ".prn",
}

TEXTO_LARGO = {".md", ".txt", ".docx", ".doc"}
NO_CLASIFICADOS = {"sin_texto", "sin_clasificar", "formato_desconocido"}
MOTIVOS = ("cartera", "doctrina", "expediente", "expediente_nuevo", "alias", "jurisprudencia",
           "match_carpeta", "escrito_propio", "rama", "sin_clasificar", "sin_texto", "formato_desconocido")


class Destino(NamedTuple):
    carpeta: Path
    motivo: str
    detalle: str = ""
    confianza: str = "media"


# ── Aliases ──────────────────────────────────────────────────────────

def _mtime(p: Path) -> float:
    return p.stat().st_mtime if p.exists() else 0.0


_alias_cache: tuple[tuple[float, float], list[tuple[re.Pattern, str]]] = ((0.0, 0.0), [])
_alias_por_archivo: dict[Path, list[tuple[re.Pattern, str]]] = {}


def _leer_aliases(archivo: Path) -> list[tuple[re.Pattern, str]]:
    """Un archivo ilegible conserva su ultima version buena y no arrastra al otro."""
    if not archivo.exists():
        return []
    compilados = []
    try:
        for a in json.loads(archivo.read_text(encoding="utf-8")).get("aliases", []):
            try:
                compilados.append((re.compile(a["pattern"], re.IGNORECASE), a["caso"]))
            except re.error:
                print(f"[alias invalido, ignorado] {a['pattern']}", file=sys.stderr)
    except (json.JSONDecodeError, OSError, KeyError, TypeError, AttributeError) as exc:
        print(f"[aliases ilegibles, se usa la version anterior] {archivo.name}: {exc}", file=sys.stderr)
        return _alias_por_archivo.get(archivo, [])
    _alias_por_archivo[archivo] = compilados
    return compilados


def cargar_aliases() -> list[tuple[re.Pattern, str]]:
    """Primero los manuales (aliases.json), despues los generados desde la cartera."""
    global _alias_cache
    firma = (_mtime(ALIAS_FILE), _mtime(ALIAS_CARTERA))
    if firma != _alias_cache[0]:
        _alias_cache = (firma, _leer_aliases(ALIAS_FILE) + _leer_aliases(ALIAS_CARTERA))
    return _alias_cache[1]


def _caso_valido(caso: object) -> bool:
    if not isinstance(caso, str) or not caso:
        return False
    d, raiz = (CASOS / caso).resolve(), CASOS.resolve()
    return d != raiz and d.is_relative_to(raiz) and d.is_dir()


def validar_alias(pattern: str, caso: str) -> str | None:
    try:
        rx = re.compile(pattern, re.IGNORECASE)
    except re.error as exc:
        return f"regex invalido: {exc}"
    if rx.search(""):
        return "el patron coincide con cualquier nombre"
    if not caso or not (CASOS / caso).is_dir():
        return f"no existe la carpeta {caso!r}"
    if not _caso_valido(caso):
        return f"la carpeta {caso!r} queda fuera de {CASOS.name}"
    return None


def _match_alias(nombre: str) -> str | None:
    nombre = _sin_tildes(nombre)
    for patron, caso in cargar_aliases():
        if patron.search(nombre) and _caso_valido(caso):
            return caso
    return None


# ── Match contra carpetas existentes ─────────────────────────────────

_PALABRAS_GENERICAS = {
    "banco", "estado", "nacion", "poder", "judicial", "provincia",
    "misiones", "posadas", "municipalidad", "ministerio", "defensa",
    "salud", "trabajo", "seguridad", "social", "tribunal", "juzgado",
    "primera", "instancia", "civil", "comercial", "laboral", "penal",
    "contencioso", "administrativo", "nacional", "federal", "anses",
    "establecimiento", "servicios", "argentina", "argentino", "fiduciarios",
    "demanda", "apelacion", "recurso", "consumo", "desalojo", "debate",
    "imprimir", "ahorro", "instituto", "norma", "expte", "amparo",
    "ejecucion", "sucesion", "divorcio", "despido", "danos", "perjuicios",
    "cobro", "pesos", "sumas", "dinero", "accion", "medida", "cautelar",
    "sociedad", "anonima", "limitada", "responsabilidad", "empresa", "compania",
    "seguros", "asociacion", "cooperativa", "consumidores", "usuarios", "colegio",
    "publico", "abogados", "medios", "buenos", "aires", "direccion", "general",
    "secretaria", "empleo", "internacional",
}
_PALABRAS_GENERICAS |= set(APELLIDOS_PROPIOS)  # el titular firma todo: no identifica causa


def asegurar_estructura() -> None:
    for d in (INBOX, CASOS, SISTEMA):
        d.mkdir(parents=True, exist_ok=True)


def _sin_tildes(t: str) -> str:
    return unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode().lower()


VENTANA = 12


def _utiles(partes: list[str]) -> list[str]:
    return [p for p in partes if len(p) >= 5 and not p.isdigit() and p not in _PALABRAS_GENERICAS]


def _match_carpetas_existentes(texto: str) -> str | None:
    """Busca el apellido del actor a <= VENTANA palabras de una palabra del demandado,
    como en una caratula. Las carpetas son AAAA-actor(3 palabras)-demandado.
    Ante empate no decide."""
    if not texto or len(texto) < 50:
        return None
    pos: dict[str, list[int]] = {}
    for i, w in enumerate(re.findall(r"[a-z0-9]+", _sin_tildes(texto))):
        pos.setdefault(w, []).append(i)
    candidatos: list[tuple[int, str]] = []
    for d in CASOS.iterdir():
        if not d.is_dir() or d.name.startswith("sinanio-") or "-expte-" in d.name:
            continue
        partes = d.name.split("-")[1:]
        actor, dem = _utiles(partes[:3]), _utiles(partes[3:])
        if not actor or not dem or actor[0] not in pos:
            continue
        cerca = {t for t in dem
                 if any(abs(i - j) <= VENTANA for i in pos[actor[0]] for j in pos.get(t, ()))}
        if cerca:
            candidatos.append((len(actor[0]) + sum(len(t) for t in cerca), d.name))
    if not candidatos:
        return None
    candidatos.sort(reverse=True)
    if len(candidatos) > 1 and candidatos[0][0] == candidatos[1][0]:
        return None
    return candidatos[0][1]


_exptes_cache: dict[str, str] | None = None


def _mapa_exptes() -> dict[str, str]:
    """expte -> carpeta, aprendido de los ruteos previos. Solo exptes que fueron a una unica carpeta."""
    global _exptes_cache
    if _exptes_cache is None:
        m: dict[str, Counter] = {}
        for nombre in ("FASE2_RUTEO.csv", "FASE4_RUTEO.csv", RUTEO_CSV.name):
            ruta = BASE / "_SISTEMA" / nombre
            if not ruta.exists():
                continue
            with ruta.open(encoding="utf-8", newline="") as fh:
                for r in csv.DictReader(fh):
                    expte = r.get("expediente") or (
                        r.get("detalle") if r.get("motivo") in ("expediente", "expediente_nuevo") else None)
                    partes = PureWindowsPath(r.get("destino", "")).parts
                    if expte and "01_Expedientes" in partes[:-1]:
                        caso = partes[partes.index("01_Expedientes") + 1]
                        m.setdefault(expte, Counter())[RENOMBRES.get(caso, caso)] += 1
        _exptes_cache = {e: next(iter(c)) for e, c in m.items()
                         if len(c) == 1 and (CASOS / next(iter(c))).is_dir()}
    return _exptes_cache


def _misma_caratula(caratula: str, carpeta: str) -> bool:
    sufijo = carpeta.split("-", 1)[1] if "-" in carpeta else carpeta
    if caratula.startswith(sufijo) or sufijo.startswith(caratula):
        return True
    a, b = caratula.split("-"), sufijo.split("-")
    propios = set(_utiles(b[3:])) or set(_utiles(b[1:]))
    return a[0] == b[0] and len(a[0]) >= 4 and bool(propios & set(_utiles(a[1:])))


def carpeta_de_caso(expte: str, caratula: str | None) -> tuple[Path, bool]:
    caso = _mapa_exptes().get(expte)
    if caso:
        return CASOS / caso, True
    num, anio = expte.split("/")
    for d in sorted(CASOS.iterdir()):
        if not d.is_dir():
            continue
        if f"expte-{num}-{anio}" in d.name:
            return d, True
        if caratula and d.name.startswith(anio) and _misma_caratula(caratula, d.name):
            return d, True
    return CASOS / f"{anio}-{caratula or f'expte-{num}-{anio}'}", False


# ── Cartera propia ───────────────────────────────────────────────────

RE_ID = re.compile(r"(?<![a-z])id[-_]?(\d{5,8})(?!\d)", re.I)
RE_NUM_FECHA = re.compile(r"(?<!\d)\d{1,6}[-_]\d{4}-\d{2}-\d{2}(?!\d)")
RE_NUM_ANIO = re.compile(r"(?<!\d)(\d{1,7})[-_/ ]?((?:19|20)\d{2})(?!\d)")
RE_BIS = re.compile(r"bis[-_ ]?(\d+)", re.I)


_SIGLAS_SIN_VALOR = {"otro", "otra", "pshm"}


def _tokens_de_parte(texto: str) -> list[str]:
    return [w for w in re.findall(r"[a-z]+", _sin_tildes(texto))
            if len(w) >= 4 and w not in _PALABRAS_GENERICAS and w not in _SIGLAS_SIN_VALOR]


def _partes_de(caratula: str) -> tuple[list[str], list[str]]:
    m = re.match(r"^(.+?)\s+c\s*/\s*(.+?)(?:\s+s\s*/.*)?$", caratula, re.I)
    if m:
        return _tokens_de_parte(m[1])[:3], _tokens_de_parte(m[2])[:3]
    return _tokens_de_parte(re.split(r"\s+s\s*/", caratula, flags=re.I)[0])[:3], []


class IndiceCartera:
    def __init__(self, causas):
        self.por_id: dict[str, str] = {}
        self.por_clave: dict[str, str] = {}
        self.por_bis: dict[str, str] = {}
        self.previstas: set[str] = set()
        self.partes: list[tuple[str, list[str], list[str]]] = []
        for c in causas:
            carpeta = c.carpeta or c.carpeta_prevista
            if not carpeta:
                continue
            if not c.carpeta:
                self.previstas.add(carpeta)
            if c.id_expediente:
                self.por_id[c.id_expediente] = carpeta
            if c.expte.bis is None:
                self.por_clave[c.expte.clave] = carpeta
            else:
                self.por_bis[f"{c.expte.clave} bis{c.expte.bis}"] = carpeta
            if c.caratula:
                actor, dem = _partes_de(c.caratula)
                if actor:
                    self.partes.append((carpeta.split("/")[0], actor, dem))

    def por_partes(self, nombre: str) -> str | None:
        """Carpeta si el nombre del archivo nombra a las partes de una unica causa."""
        palabras = set(re.findall(r"[a-z]+", _sin_tildes(nombre)))
        hits = set()
        for carpeta, actor, dem in self.partes:
            if dem:
                ok = actor[0] in palabras and any(t in palabras for t in dem)
            else:
                ok = len(actor) >= 2 and actor[0] in palabras and actor[1] in palabras
            if ok:
                hits.add(carpeta)
        return next(iter(hits)) if len(hits) == 1 else None

    def por_numero(self, numero: int, anio: int, bis: int | None = None) -> str | None:
        clave = f"{numero}/{anio}"
        if bis is not None and f"{clave} bis{bis}" in self.por_bis:
            return self.por_bis[f"{clave} bis{bis}"]
        return self.por_clave.get(clave)


_indice_cache: tuple[float, IndiceCartera] = (-1.0, IndiceCartera([]))


def _indice() -> IndiceCartera:
    global _indice_cache
    m = _mtime(CARTERA_JSON)
    if m != _indice_cache[0]:
        try:
            indice = IndiceCartera(cargar_cartera(CARTERA_JSON))
        except (json.JSONDecodeError, OSError, KeyError, TypeError, AttributeError) as exc:
            print(f"[cartera ilegible, se ignora] {CARTERA_JSON.name}: {exc}", file=sys.stderr)
            indice = IndiceCartera([])
        _indice_cache = (m, indice)
    return _indice_cache[1]


def _caso_cartera(nombre: str, texto: str | None) -> tuple[str, str] | None:
    """(carpeta, via). Por id de SIGED, numero o nombre de las partes en el nombre; por numero en el texto si se pasa."""
    idx = _indice()

    def existe(carpeta: str | None) -> str | None:
        return carpeta if carpeta and ((CASOS / carpeta).is_dir() or carpeta in idx.previstas) else None

    m = RE_ID.search(nombre)
    if m and existe(idx.por_id.get(m.group(1))):
        return idx.por_id[m.group(1)], "id"
    sin_fecha = RE_NUM_FECHA.sub(" ", nombre)
    bis = RE_BIS.search(sin_fecha)
    for mm in RE_NUM_ANIO.finditer(sin_fecha):
        carpeta = existe(idx.por_numero(int(mm.group(1)), int(mm.group(2)), int(bis.group(1)) if bis else None))
        if carpeta:
            return carpeta, "numero_nombre"
    carpeta = existe(idx.por_partes(nombre))
    if carpeta:
        return carpeta, "partes"
    if texto:
        e = buscar_expte(texto)
        if e:
            n, a = e.split("/")
            carpeta = existe(idx.por_numero(int(n), int(a)))
            if carpeta:
                return carpeta, "numero_texto"
    return None


# ── Clasificacion ────────────────────────────────────────────────────

EDITABLES = {".docx", ".doc", ".odt", ".rtf", ".md", ".txt"}
RE_EXPORTACION_SIGED = re.compile(r"__user|(?<![a-z])id[-_]?\d{5}|^expediente[-_ ]\d|limpio", re.I)


def _borrador(nombre: str, ext: str, via: str) -> bool:
    """Trabajo propio sin matricula: SIGED baja PDF; los editables son propios salvo las exportaciones del expediente.
    El texto no sirve para decidir: las providencias de SIGED tambien nombran al letrado."""
    return via != "id" and ext in EDITABLES and not RE_EXPORTACION_SIGED.search(nombre)


def _por_rama(p: Path, ext: str, texto: str) -> Destino:
    largo = len(texto.strip())
    if not ((ext == ".pdf" and largo > 120) or (ext in TEXTO_LARGO and largo > 400)):
        return Destino(INBOX / "sin_clasificar", "sin_clasificar", "", "baja")
    carpeta, rama = clasificar(texto)
    es_fallo = rama.startswith("fallo_sin_tribunal")
    if not (es_fallo or rama.startswith("doctrina_")):
        if BASE / "02_Jurisprudencia" in carpeta.parents:
            carpeta = BASE / "02_Jurisprudencia" / Path(*tema_de(texto, p.name))
        return Destino(carpeta, "rama", rama)
    d = clasificar_doctrina(texto, p.name, paginas_pdf(p) if ext == ".pdf" else 0)
    if d is None or (es_fallo and d.confianza == "baja"):
        if es_fallo:
            return Destino(BASE / "02_Jurisprudencia" / Path(*tema_de(texto, p.name)), "rama", rama)
        return Destino(INBOX / "sin_clasificar", "sin_clasificar", "no es doctrina", "baja")
    confianza = "media" if es_fallo and d.confianza == "alta" else d.confianza
    return Destino(ruta_doctrina(d, BASE), "doctrina", f"{d.tipo} | {d.motivo}", confianza)


def destino_de(p: Path) -> Destino:
    ext = p.suffix.lower()
    nombre = p.stem

    if ext not in FORMATOS_CON_TEXTO and ext not in FORMATOS_SIN_TEXTO:
        return Destino(INBOX / "formato_desconocido", "formato_desconocido", ext, "baja")

    texto, err = (None, None) if ext in FORMATOS_SIN_TEXTO else extraer_universal(p)
    if err in ("doc_lectura_binaria", "ocr_ilegible"):
        texto = None  # basura binaria + metadatos: no sirve para decidir por contenido
    hay_texto = bool(texto and len(texto.strip()) >= 30)
    firmado = hay_texto and bool(MATRICULA_RE.search(texto))
    propio = firmado or (hay_texto and bool(OWNER_RE.search(texto)))
    es_juris = hay_texto and not propio and bool(JURIS_RE.search(texto[:4000]))

    hit = _caso_cartera(nombre, texto if hay_texto and not es_juris else None)
    if hit:
        carpeta, via = hit
        sub_c = "00_escritos_propios" if firmado or _borrador(nombre, ext, via) else "01_siged"
        return Destino(CASOS / carpeta / sub_c, "cartera", via, "alta" if via in ("id", "numero_nombre") else "media")

    if not hay_texto:
        caso = _match_alias(nombre)
        if caso:
            return Destino(CASOS / caso / "00_escritos_propios", "alias", caso)
        sub = "sin_texto" if ext in FORMATOS_SIN_TEXTO else "_sin_texto"
        return Destino(INBOX / sub, "sin_texto", err or "", "baja")

    expte = buscar_expte(texto)
    caratula = buscar_caratula(texto)
    sub = "00_escritos_propios" if propio else "01_siged"
    sub_e = "00_escritos_propios" if firmado else "01_siged"

    if expte and (propio or caratula):
        carpeta, existe = carpeta_de_caso(expte, caratula)
        if existe:
            return Destino(carpeta / sub_e, "expediente", expte, "alta")
        # Un numero que no es de la cartera no abre carpeta: casi siempre es una causa citada o ajena.

    caso = _match_alias(nombre)
    if caso:
        return Destino(CASOS / caso / sub, "alias", caso)

    if es_juris:
        carpeta, rama = clasificar(texto)
        if rama.startswith("legislacion"):
            return Destino(carpeta, "rama", rama)
        if not rama.startswith(("fallo_sin_tribunal", "doctrina_")):
            return Destino(BASE / "02_Jurisprudencia" / Path(*tema_de(texto, p.name)), "jurisprudencia", rama,
                           "alta" if FALLO.search(texto[:4000]) else "media")
        return _por_rama(p, ext, texto)  # menciona "doctrina"/"jurisprudencia" pero sin tribunal identificado

    caso = _match_carpetas_existentes(texto)
    if caso:
        return Destino(CASOS / caso / sub, "match_carpeta", caso)

    if propio:
        return Destino(BASE / "05_Modelos_y_Escritos", "escrito_propio")

    return _por_rama(p, ext, texto)


def destino_ajeno(p: Path, carpeta: str) -> Destino:
    """Archivo de una carpeta de causa que no es del Dr.: los fallos y la doctrina van a su tema; el resto,
    a 06_Expedientes_ajenos conservando el nombre de la carpeta."""
    texto, err = extraer_universal(p)
    texto = texto if err not in ("doc_lectura_binaria", "ocr_ilegible") else None
    if texto and len(texto.strip()) > 200:
        destino, rama = clasificar(texto)
        if rama.startswith("legislacion"):
            return Destino(destino, "rama", rama)
        if not rama.startswith("doctrina_") and (FALLO.search(texto[:4000]) or not rama.startswith("fallo_sin")):
            return Destino(BASE / "02_Jurisprudencia" / Path(*tema_de(texto, p.name)), "jurisprudencia", rama,
                           "alta" if FALLO.search(texto[:4000]) else "media")
        d = clasificar_doctrina(texto, p.name, paginas_pdf(p) if p.suffix.lower() == ".pdf" else 0)
        if d:
            return Destino(ruta_doctrina(d, BASE), "doctrina", f"{d.tipo} | {d.motivo}", d.confianza)
    return Destino(BASE / "06_Expedientes_ajenos" / carpeta, "ajena", carpeta)


def ignorado(p: Path, origen: Path) -> bool:
    try:
        return bool(set(p.relative_to(origen).parts[:-1]) & IGNORAR)
    except ValueError:
        return False


RE_REPO_DESCARGADO = re.compile(r"-(main|master)$")
MARCAS_DE_PROYECTO = {"package.json", ".git", "node_modules", "pyproject.toml", ".venv", "venv", "setup.py"}


def archivos_pendientes(origen: Path) -> list[Path]:
    """Recorre origen sin entrar en las carpetas ignoradas ni en proyectos de codigo."""
    out = []
    for raiz, dirs, archivos in os.walk(origen):
        if raiz != str(origen) and (MARCAS_DE_PROYECTO & (set(dirs) | set(archivos))
                                    or RE_REPO_DESCARGADO.search(Path(raiz).name) or "SKILL.md" in archivos):
            dirs.clear()
            continue
        dirs[:] = [d for d in dirs if d not in IGNORAR and d not in MARCAS_DE_PROYECTO]
        out += [Path(raiz) / a for a in archivos]
    return out


def mover(src: Path, carpeta: Path, motivo: str, detalle: str = "", nombre: str | None = None) -> Path:
    """nombre: nombre nuevo del archivo (sin cambiar la extension); por defecto conserva el original."""
    if src.parent.resolve() == carpeta.resolve() and not nombre:
        return src
    if not carpeta.resolve().is_relative_to(BASE.resolve()):
        raise ValueError(f"Destino fuera de la base: {carpeta}")
    carpeta.mkdir(parents=True, exist_ok=True)
    dst = destino_unico(carpeta / ((Path(nombre).stem + src.suffix) if nombre else src.name))
    shutil.move(str(src), str(dst))
    try:
        _anotar(src, dst, motivo, detalle)
    except OSError as exc:
        try:
            shutil.move(str(dst), str(src))
        except OSError as exc2:
            raise OSError(f"No se pudo registrar el movimiento ni devolver el archivo: "
                          f"quedo en {dst} ({exc}; {exc2})") from exc
        raise OSError(f"No se pudo registrar el movimiento; el archivo volvio a {src} ({exc})") from exc
    global _exptes_cache
    _exptes_cache = None
    return dst


def _anotar(origen: Path, destino: Path, motivo: str, detalle: str = "") -> None:
    RUTEO_CSV.parent.mkdir(parents=True, exist_ok=True)
    nuevo = not RUTEO_CSV.exists()
    with RUTEO_CSV.open("a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if nuevo:
            w.writerow(["fecha", "origen", "destino", "motivo", "detalle"])
        w.writerow([datetime.now().isoformat(timespec="seconds"), origen, destino, motivo, detalle])


def _leer_propuestas(ruta: Path) -> list[dict]:
    """El CSV de la simulacion, tal cual o re-guardado por Excel (punto y coma, cp1252)."""
    for encoding in ("utf-8-sig", "cp1252"):
        try:
            texto = ruta.read_text(encoding=encoding)
            break
        except UnicodeDecodeError:
            continue
    dialecto = csv.Sniffer().sniff(texto.splitlines()[0], delimiters=",;\t")
    return list(csv.DictReader(texto.splitlines(), dialect=dialecto))


def leer_ruteo() -> list[dict]:
    if not RUTEO_CSV.exists():
        return []
    with RUTEO_CSV.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def leer_tandas() -> list[dict]:
    if not TANDAS_CSV.exists():
        return []
    with TANDAS_CSV.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def _registrar_tanda(origen: str, primera: int, ultima: int) -> str:
    """Una tanda = un rango de filas de INGESTA_RUTEO.csv (indices desde 0, sin la cabecera)."""
    tandas = leer_tandas()
    tid = f"t{len(tandas) + 1:04d}"
    nuevo = not TANDAS_CSV.exists()
    with TANDAS_CSV.open("a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if nuevo:
            w.writerow(["id", "fecha", "origen", "movidos", "primera_fila", "ultima_fila"])
        w.writerow([tid, datetime.now().isoformat(timespec="seconds"), origen, ultima - primera + 1, primera, ultima])
    return tid


def tandas_historicas(filas: list[dict], explicitas: list[dict], pausa: int = 120) -> list[dict]:
    """Tandas registradas mas las derivadas del historial viejo: filas seguidas con menos de `pausa` segundos."""
    cubiertas = {i for t in explicitas for i in range(int(t["primera_fila"]), int(t["ultima_fila"]) + 1)}
    out = [dict(t, derivada=False) for t in explicitas]
    actual: list[int] = []

    def cerrar():
        if actual:
            a, b = actual[0], actual[-1]
            out.append({"id": f"h{a}-{b}", "fecha": filas[a]["fecha"], "origen": "historial",
                        "movidos": b - a + 1, "primera_fila": a, "ultima_fila": b, "derivada": True})
            actual.clear()

    anterior = None
    for i, f in enumerate(filas):
        if i in cubiertas:
            cerrar()
            anterior = None
            continue
        try:
            t = datetime.fromisoformat(f["fecha"])
        except (ValueError, KeyError):
            t = anterior
        if actual and (anterior is None or t is None or (t - anterior).total_seconds() > pausa):
            cerrar()
        actual.append(i)
        anterior = t
    cerrar()
    return sorted(out, key=lambda t: int(t["primera_fila"]))


def deshacer_filas(primera: int, ultima: int) -> dict:
    """Devuelve cada archivo del rango a su origen, del ultimo al primero. Nunca pisa ni borra."""
    return deshacer_indices(list(range(primera, ultima + 1)), f"filas {primera}-{ultima}")


def deshacer_indices(indices: list[int], etiqueta: str) -> dict:
    """Como deshacer_filas, pero con filas sueltas del registro (para revertir solo algunas de una tanda)."""
    filas = leer_ruteo()
    inicio, restaurados, avisos = len(filas), 0, []
    for f in (filas[i] for i in sorted(set(indices), reverse=True) if 0 <= i < len(filas)):
        if f.get("motivo") == "deshacer":
            continue
        dst, org = Path(f["destino"]), Path(f["origen"])
        if not dst.is_file():
            avisos.append(f"[ya no esta en el destino] {dst}")
            continue
        if org.exists():
            avisos.append(f"[el origen esta ocupado] {org}")
            continue
        try:
            org.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(dst), str(org))
        except OSError as exc:
            avisos.append(f"[ERROR] {dst}: {exc}")
            continue
        try:
            _anotar(dst, org, "deshacer", etiqueta)
        except OSError as exc:
            try:
                shutil.move(str(org), str(dst))
                avisos.append(f"[sin registro, se dejo en el destino] {dst}: {exc}")
            except OSError as exc2:
                avisos.append(f"[ERROR: restaurado en {org} pero sin registro] {exc}; {exc2}")
            continue
        restaurados += 1
    tanda = _registrar_tanda(f"deshacer:{etiqueta.removeprefix('filas ')}", inicio, inicio + restaurados - 1) \
        if restaurados else None
    return {"restaurados": restaurados, "avisos": avisos, "tanda": tanda}


def _publicar(dst: Path, motivo: str, detalle: str) -> bool:
    try:
        ruta = kb_publicar.publicar(dst, motivo, detalle)
        if ruta is None and (motivo == "jurisprudencia" or detalle.startswith("legislacion_")):
            print(f"  [AVISO] no publicado (ya publicado / mismo nombre / sin id): {dst}")
        return ruta is not None
    except Exception as exc:  # noqa: BLE001
        print(f"  [AVISO publicacion] {dst}: {exc}")
        return False


def _reindexar() -> None:
    try:
        print(f"Indice del corpus: {kb_index.rebuild()}")
    except Exception as exc:  # noqa: BLE001
        print(f"  [AVISO reindexacion] {exc}")


def aplicar_filas(filas: list[dict], origen: str) -> dict:
    """Mueve exactamente las filas con accion=mover, al destino escrito, sin volver a clasificar."""
    inicio = len(leer_ruteo())
    movidos, avisos, publicados = 0, [], 0
    for f in filas:
        if f.get("accion", "").strip().lower() != "mover":
            continue
        src, destino = Path(f["archivo"]), Path(f["destino"])
        if not src.is_file():
            avisos.append(f"[ya no esta] {src}")
            continue
        if BASE not in destino.parents and destino != BASE:
            avisos.append(f"[destino fuera de {BASE}] {src} -> {destino}")
            continue
        try:
            dst = mover(src, destino, f.get("motivo", ""), f.get("detalle", ""), f.get("nombre_nuevo") or None)
            movidos += 1
            publicados += _publicar(dst, f.get("motivo", ""), f.get("detalle", ""))
        except OSError as exc:
            avisos.append(f"[ERROR] {src}: {exc}")
    tanda = _registrar_tanda(origen, inicio, inicio + movidos - 1) if movidos else None
    if publicados:
        _reindexar()
    return {"movidos": movidos, "avisos": avisos, "tanda": tanda, "publicados": publicados}


def aplicar_csv(ruta: Path) -> dict:
    r = aplicar_filas(_leer_propuestas(ruta), ruta.name)
    for a in r["avisos"]:
        print(f"  {a}")
    print(f"\nMovidos: {r['movidos']} | avisos: {len(r['avisos'])} | tanda: {r['tanda']}\nRegistro: {RUTEO_CSV}")
    return r


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--src", type=Path, default=None,
                    help="Carpeta origen (default: _INBOX)")
    ap.add_argument("--csv", type=Path, default=None, help="Guarda las propuestas en un CSV")
    ap.add_argument("--omitir", nargs="+", default=[], choices=MOTIVOS, metavar="MOTIVO",
                    help="Motivos que no se mueven: " + ", ".join(MOTIVOS))
    ap.add_argument("--incluir-no-clasificados", action="store_true",
                    help="Fuera del INBOX, tambien mueve lo que no se reconoce (a _INBOX/sin_clasificar, etc.)")
    ap.add_argument("--aplicar-csv", type=Path, default=None, metavar="CSV",
                    help="Mueve las filas con accion=mover de un CSV de simulacion revisado, sin reclasificar")
    args = ap.parse_args()
    asegurar_estructura()

    if args.aplicar_csv:
        aplicar_csv(args.aplicar_csv)
        return

    origen = args.src or INBOX
    if not origen.exists():
        print(f"No existe: {origen}")
        return

    pendientes = archivos_pendientes(origen)
    if not pendientes:
        print(f"{origen}: sin novedades.")
        return

    print(f"{len(pendientes)} archivos para rutear"
          f"{' (simulacion)' if args.dry_run else ''}\n")
    conteo: Counter = Counter()
    filas = []
    publicados = 0
    for p in pendientes:
        d = destino_de(p)
        conteo[d.motivo] += 1
        se_queda = d.motivo in args.omitir or (
            origen != INBOX and d.motivo in NO_CLASIFICADOS and not args.incluir_no_clasificados)
        filas.append([p, d.carpeta, d.motivo, d.detalle, d.confianza, "queda" if se_queda else "mover"])
        if se_queda:
            continue
        if args.dry_run:
            rel = p.relative_to(origen)
            try:
                dst_rel = d.carpeta.relative_to(BASE)
            except ValueError:
                dst_rel = d.carpeta
            print(f"  {str(rel)[:60]:60s} -> {dst_rel}  [{d.motivo} {d.detalle}]")
            continue
        try:
            dst = mover(p, d.carpeta, d.motivo, d.detalle)
        except Exception as exc:  # noqa: BLE001
            print(f"  [ERROR] {p}: {exc}")
            continue
        publicados += _publicar(dst, d.motivo, d.detalle)
    if args.csv:
        with args.csv.open("w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f)
            w.writerow(["archivo", "destino", "motivo", "detalle", "confianza", "accion"])
            w.writerows(filas)
        print(f"\nPropuestas: {args.csv}")
    print("\n--- Resumen ---")
    for k, v in conteo.most_common():
        print(f"  {k}: {v}")
    if not args.dry_run:
        if publicados:
            _reindexar()
        print(f"\nRegistro: {RUTEO_CSV}")


if __name__ == "__main__":
    main()
