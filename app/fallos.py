"""Ficha de un fallo por reglas (sin IA): tribunal, sala, fecha, caratula, tipo, normas, tema, fuerza como
precedente y si es un rechazo formal del recurso (extemporaneo, desierto, mal concedido...), que no sirve para citar
sobre el fondo."""
from __future__ import annotations

import re
import unicodedata
from dataclasses import asdict, dataclass

from doctrina import tema_de
from fase3_juris import clasificar

MESES = {m: i for i, m in enumerate(
    "enero febrero marzo abril mayo junio julio agosto septiembre octubre noviembre diciembre".split(), 1)}
MESES["setiembre"] = 9

RE_FECHA_LARGA = re.compile(r"(\d{1,2})\s+(?:dias?\s+)?de(?:l mes de)?\s+(" + "|".join(MESES) + r")\s+(?:de(?:l ano)?\s+)?((?:19|20)\d{2})")
RE_FECHA_CORTA = re.compile(r"(?<!\d)(\d{1,2})/(\d{1,2})/((?:19|20)\d{2})(?!\d)")
RE_SALA = re.compile(r"\bsala\s+(i{1,3}|iv|v|vi{0,3}|[1-9]|[a-l])\b")
RE_CARATULA = re.compile(r"(?:autos|caratulados?|en los autos)\s*[:\"“]?\s*[\"“]?([^\"”\n]{8,160}?\s+c/\s*[^\"”\n]{3,160}?)(?:[\"”]|\s+s/|\s+expte|$)")
RE_EXPTE = re.compile(r"expte\.?\s*(?:n[°ºo.]*\s*)?(\d{1,7}\s*/\s*(?:19|20)?\d{2})")
RE_LEY = re.compile(r"\bley\s+(?:n[°ºo.]*\s*)?((?:[ivxl]+\s*-?\s*n[°º]?\s*\d+)|\d{1,2}\.?\d{3})")
RE_ART = re.compile(r"\bart(?:iculo|s?\.)\s*(\d{1,4}(?:\s*bis)?)")

PLENARIO = re.compile(r"\bplenari[oa]|doctrina legal|fallo plenario|acuerdo plenario")
DISIDENCIA = re.compile(r"\bdisidencia\b|\bvoto en disidencia\b|\ben minoria\b")
INTERLOCUTORIA = re.compile(r"\binterlocutori[oa]\b|\bauto interlocutorio\b")

# Rechazo por cuestiones formales: el tribunal no entra al fondo.
RECHAZO_FORMAL = [
    ("extemporaneo", r"extemporane|fuera de (?:termino|plazo)|vencido el plazo|interpuesto tardiamente"),
    ("desierto", r"\bdesiert[oa]\b|deserci[oó]n"),
    ("mal concedido", r"mal concedid"),
    ("inadmisible", r"inadmisib|no (?:resulta|es) admisible|improcedencia formal|formalmente improcedente"),
    ("in limine", r"in limine"),
    ("art. 280 CPCCN", r"art(?:iculo|\.)\s*280"),
    ("sin sentencia definitiva", r"no (?:se dirige contra|reviste (?:el caracter de|calidad de)) sentencia definitiva|no es sentencia definitiva"),
    ("falta de fundamentacion", r"falta de fundamentaci[oó]n autonoma|carece de fundamentaci[oó]n|no (?:rebate|refuta|critica)"),
    ("sin deposito", r"falta de(?:l)? dep[oó]sito|no (?:efectu|acredit)[oó] el dep[oó]sito"),
    ("caducidad recursiva", r"caducidad de la (?:instancia|segunda instancia) recursiva|perenci[oó]n de la instancia"),
]
RECHAZO_RE = [(n, re.compile(p)) for n, p in RECHAZO_FORMAL]
RESUELVE = re.compile(r"\b(?:resuelve|resuelvo|se resuelve|por ello|por todo lo expuesto|fallo:|falla:|decide)\b")
RECHAZA = re.compile(r"\b(?:rechaz|desestim|declar|inadmit|no hacer lugar|no ha lugar)")
FONDO_RESUELTO = re.compile(r"\b(?:hacer lugar|hace lugar|haciendo lugar|revoc|modific|admitir parcialmente|condenar)")

FUERZA = {"stj_misiones": "1-STJ Misiones", "camara_civil": "2-Camara Misiones", "camara_laboral": "2-Camara Misiones",
          "camara_penal": "2-Camara Misiones", "camara_misiones_sin_fuero": "2-Camara Misiones", "csjn": "3-CSJN",
          "camara_nacional": "4-Nacional u otra provincia", "tribunal_otra_jurisdiccion": "4-Nacional u otra provincia"}


@dataclass
class Ficha:
    tribunal: str
    sala: str
    fecha: str
    caratula: str
    expte: str
    tipo: str
    fuerza: str
    rama: str
    especialidad: str
    normas: str
    rechazo_formal: str
    evidencia: str


def _norm(t: str) -> str:
    return unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode().lower()


def _fecha(t: str) -> str:
    fechas = []
    for d, m, a in RE_FECHA_LARGA.findall(t):
        fechas.append(f"{a}-{MESES[m]:02d}-{int(d):02d}")
    for d, m, a in RE_FECHA_CORTA.findall(t):
        if 1 <= int(m) <= 12 and 1 <= int(d) <= 31:
            fechas.append(f"{a}-{int(m):02d}-{int(d):02d}")
    return max(fechas) if fechas else ""


def _parte_resolutiva(t: str) -> str:
    m = None
    for m in RESUELVE.finditer(t):
        pass
    return (t[m.start():] if m else t[-3000:])[:1500]


def rechazo_formal(t: str) -> tuple[str, str]:
    """(motivo, evidencia) si la parte resolutiva rechaza por una cuestion formal y no trata el fondo."""
    parte = _parte_resolutiva(t)
    if not RECHAZA.search(parte) or FONDO_RESUELTO.search(re.sub(r"no hacer lugar|no ha lugar", "", parte)):
        return "", ""
    for nombre, rx in RECHAZO_RE:
        hit = rx.search(parte)
        if hit:
            a = max(0, hit.start() - 120)
            return nombre, " ".join(parte[a:hit.end() + 120].split())
    return "", ""


MISIONES_RE = re.compile(r"misiones|posadas|obera|eldorado")
TRIBUNAL_EMISOR = [
    ("stj_misiones", re.compile(r"superior tribunal de justicia|\bstj\b|tribunal superior de justicia")),
    ("camara_laboral", re.compile(r"camara de apelaciones (?:en lo )?laboral|camara laboral")),
    ("camara_penal", re.compile(r"camara de apelaciones (?:en lo )?(?:penal|criminal)|tribunal penal")),
    ("camara_civil", re.compile(r"camara de apelaciones (?:en lo )?civil|camara civil")),
    ("csjn", re.compile(r"corte suprema de justicia de la nacion")),
    ("camara_nacional", re.compile(r"camara nacional|camara federal")),
]
RESUELVE_EMISOR = re.compile(r"(superior tribunal de justicia|camara[^.]{0,60}|corte suprema[^.]{0,40})\s+(?:de [^.]{0,40})?r\s?e\s?s\s?u\s?e\s?l\s?v\s?e")


def tribunal_emisor(t: str) -> str:
    """Quien dicta el fallo: primero la formula resolutiva, despues el encabezado. Las citas del cuerpo no cuentan."""
    candidatos = []
    m = RESUELVE_EMISOR.search(t)
    if m:
        candidatos.append(m.group(1))
    candidatos.append(t[:1500])
    for zona in candidatos:
        for nombre, rx in TRIBUNAL_EMISOR:
            if rx.search(zona):
                if nombre.startswith(("stj", "camara_l", "camara_p", "camara_c")) and not MISIONES_RE.search(t[:4000]):
                    return "tribunal_otra_jurisdiccion"
                return nombre
    return ""


def fichar(texto: str, nombre: str) -> Ficha:
    t = _norm(texto[:60000])
    rama_trib = tribunal_emisor(t) or clasificar(texto)[1]
    rama, esp = tema_de(texto, nombre)
    car = RE_CARATULA.search(t)
    ex = RE_EXPTE.search(t)
    sala = RE_SALA.search(t[:5000])
    normas = sorted({f"ley {x.replace(' ', '')}" for x in RE_LEY.findall(t)})[:8]
    arts = [a for a in dict.fromkeys(RE_ART.findall(t))][:8]
    resolutiva = _parte_resolutiva(t)
    es_plenario = bool(re.search(r"plenari[oa]", t[:3000]) or re.search(r"(?:sentar|fijar|establecer) (?:como )?doctrina legal|acuerdo plenario", resolutiva))
    tipo = ("plenario/doctrina legal" if es_plenario else
            "interlocutoria" if INTERLOCUTORIA.search(t) else "sentencia")
    if DISIDENCIA.search(t):
        tipo += " (con disidencia)"
    motivo, evidencia = rechazo_formal(t)
    return Ficha(
        tribunal=rama_trib, sala=sala.group(1).upper() if sala else "", fecha=_fecha(t[:8000]) or _fecha(t),
        caratula=car.group(1).strip().upper()[:140] if car else "", expte=ex.group(1).replace(" ", "") if ex else "",
        tipo=tipo, fuerza="0-Plenario/doctrina legal" if es_plenario else FUERZA.get(rama_trib, "5-Sin tribunal identificado"),
        rama=rama, especialidad=esp, normas="; ".join(normas + [f"art. {a}" for a in arts]),
        rechazo_formal=motivo, evidencia=evidencia[:300],
    )


def ficha_dict(texto: str, nombre: str) -> dict:
    return asdict(fichar(texto, nombre))
