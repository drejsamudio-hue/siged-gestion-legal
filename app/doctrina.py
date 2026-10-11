"""Criterios para decidir si un documento es doctrina, de que tipo y en que rama/especialidad.

Doctrina entra a 03_Doctrina solo con evidencia positiva: vocabulario juridico y que no sea
un documento de causa. Lo que no cumple queda sin clasificar en lugar de ensuciar la carpeta.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path

from doctrina_taxonomia import RAMA_SIN_DEFINIR, RAMAS

RE_NOMBRE_SIGED = re.compile(r"(?i)__user\d+|(?<![a-z])id[-_]?\d{5,8}(?!\d)|_var_www_|^anexo[-_ ]?\d+(?![a-z])")
RE_CABECERA_CAUSA = re.compile(
    r"(?i)\bautos\s*:|\bexpte\.?\s*n?[º°o]?\s*\d|\bjuzgado\b[^.\n]{0,80}\bsecretar[ií]a\b"
    r"|\bc[eé]dula de notificaci[oó]n\b|\bprovidencia\b"
)
_VOCABULARIO = ("derecho", "ley", "articulo", "codigo", "jurisprudencia", "doctrina", "tribunal", "sentencia",
                "obligacion", "contrato", "proceso", "juez", "responsabilidad", "constitucion", "normativa", "fallo")

_INFORME = re.compile(r"\binforme (final|anual|de gestion|de resultados|estadistico)\b|\bmemoria anual\b")
_NOTA_A_FALLO = re.compile(r"nota a(l)? fallo|nota a la sentencia|nota a sentencia|comentario "
                           r"(jurisprudencial|al fallo|a la sentencia|a fallo)|a proposito del fallo")
_COMPENDIO = re.compile(r"\b(compendio|digesto|repertorio|recopilacion|antologia|anuario)\b"
                        r"|jurisprudencia sistematizada|coleccion de fallos")
_LIBRO = re.compile(r"\bisbn\b|\bindice general\b|\btabla de contenidos\b|\bcapitulo (i|1|uno)\b|\bprologo\b")
_ARTICULO = re.compile(r"\b(resumen|abstract|palabras clave|keywords?|issn|doi)\b|\brevista\b")

VENTANA_TEXTO = 40000
PAGINAS_LIBRO = 120
PAGINAS_LIBRO_CON_APARATO = 60
PAGINAS_MAX_ARTICULO = 80
PAGINAS_MAX_NOTA = 25
PAGINAS_MIN_COMPENDIO = 20
PUNTAJE_ALTO, MARGEN_ALTO, PUNTAJE_MINIMO = 8, 4, 4
PALABRAS_JURIDICAS_MINIMAS = 4
PESO_NOMBRE = 4


@dataclass(frozen=True)
class DoctrinaDestino:
    rama: str
    especialidad: str
    tipo: str
    confianza: str
    motivo: str


def _normalizar(t: str) -> str:
    return unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode().lower()


def _vocabulario_juridico(t: str) -> int:
    return sum(1 for w in _VOCABULARIO if re.search(rf"\b{w}s?\b", t))


def _paginas(paginas: int, largo_texto: int) -> int:
    if paginas > 0:
        return paginas
    return 40 if largo_texto >= 39000 else max(1, largo_texto // 2500)


def _tipo(t: str, nombre: str, paginas: int) -> tuple[str, str]:
    if _INFORME.search(t) or _INFORME.search(nombre):
        return "informe", "informe institucional"
    if _NOTA_A_FALLO.search(t):
        return "nota", "nota o comentario a fallo"
    if paginas >= PAGINAS_MIN_COMPENDIO and (_COMPENDIO.search(t) or _COMPENDIO.search(nombre)):
        return "compendio", "compendio, digesto o recopilacion"
    if paginas >= PAGINAS_LIBRO:
        return "libro", f"{paginas} paginas"
    if paginas >= PAGINAS_LIBRO_CON_APARATO and _LIBRO.search(t):
        return "libro", f"{paginas} paginas con indice/ISBN/capitulos"
    if paginas <= PAGINAS_MAX_ARTICULO and _ARTICULO.search(t):
        return "articulo", "resumen/palabras clave/revista"
    if paginas <= PAGINAS_MAX_NOTA:
        return "nota", f"pieza breve ({paginas} paginas) sin aparato de revista"
    return "articulo", f"{paginas} paginas sin aparato"


def _puntuar(t: str, nombre: str) -> list[tuple[int, str, str]]:
    tabla = []
    for rama, especialidades in RAMAS.items():
        for esp, claves in especialidades.items():
            s = sum(min(t.count(k), 5) for k in claves) + PESO_NOMBRE * sum(k in nombre for k in claves)
            tabla.append((s, rama, esp))
    return sorted(tabla, reverse=True)


def clasificar_doctrina(texto: str, nombre: str, paginas: int = 0) -> DoctrinaDestino | None:
    """None si no es doctrina (documento de causa o sin contenido juridico).

    En libros escaneados solo se lee la portada: por eso alcanza con vocabulario juridico
    o con que la portada y el nombre disparen palabras clave de una especialidad.
    """
    if RE_NOMBRE_SIGED.search(nombre) or RE_CABECERA_CAUSA.search(texto[:1500]):
        return None
    t, n = _normalizar(texto[:VENTANA_TEXTO]), re.sub(r"[-_.]+", " ", _normalizar(Path(nombre).stem))
    (s1, rama, esp), (s2, _, _) = (_puntuar(t, n) + [(0, "", "")])[:2]
    if _vocabulario_juridico(t + " " + n) < PALABRAS_JURIDICAS_MINIMAS and s1 < PUNTAJE_MINIMO:
        return None

    tipo, motivo_tipo = _tipo(t, n, _paginas(paginas, len(texto)))
    if s1 >= PUNTAJE_ALTO and s1 - s2 >= MARGEN_ALTO:
        confianza = "alta"
    elif s1 >= PUNTAJE_MINIMO:
        confianza = "media"
    else:
        (rama, esp), confianza = RAMA_SIN_DEFINIR, "baja"
    return DoctrinaDestino(rama, esp, tipo, confianza, f"{motivo_tipo}; puntaje {s1}/{s2}")


def tema_de(texto: str, nombre: str) -> tuple[str, str]:
    """(rama, especialidad) por puntaje de palabras clave; sin senal suficiente, general/sin-especialidad."""
    t, n = _normalizar(texto[:VENTANA_TEXTO]), re.sub(r"[-_.]+", " ", _normalizar(Path(nombre).stem))
    s, rama, esp = _puntuar(t, n)[0]
    return (rama, esp) if s >= PUNTAJE_MINIMO else RAMA_SIN_DEFINIR


def ruta_doctrina(d: DoctrinaDestino, base: Path) -> Path:
    return base / "03_Doctrina" / d.rama / d.especialidad
