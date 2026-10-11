"""Datos de idioma para el OCR: se descargan del repositorio oficial de Tesseract, solo si el usuario lo pide."""
from __future__ import annotations

import hashlib
import os
import urllib.request
from pathlib import Path

# Fijada al ultimo commit que modifico el archivo (14/09/2017): el contenido de esta URL no puede cambiar.
URL_OFICIAL = "https://github.com/tesseract-ocr/tessdata_fast/raw/923915d4ced2a7235221788285785a29c4a42d4a/spa.traineddata"
PAGINA_OFICIAL = "https://github.com/tesseract-ocr/tessdata_fast"
ARCHIVO = "spa.traineddata"
MIN_BYTES = 500_000
MAX_BYTES = 60_000_000
# Medida el 10/10/2026 sobre la misma ruta en la rama main, sin cambios desde 2017.
SHA256_OFICIAL = "6f2e04d02774a18f01bed44b1111f2cd7f3ba7ac9dc4373cd3f898a40ea6b464"


def url_descarga() -> str:
    """Se puede apuntar a un espejo propio con ORGANIZADOR_TESSDATA_URL; sin eso, la fuente oficial."""
    return os.environ.get("ORGANIZADOR_TESSDATA_URL") or URL_OFICIAL


def instalado(carpeta: Path) -> bool:
    return (carpeta / ARCHIVO).is_file()


def instalar(carpeta: Path, url: str | None = None, timeout: int = 60, sha256: str | None = None) -> Path:
    """Baja el idioma a `carpeta`. Si algo falla no deja archivos a medias ni pisa uno que ya funciona.

    De la fuente oficial exige la huella conocida; con un espejo propio solo controla el tamano.
    """
    url = url or url_descarga()
    if sha256 is None and url == URL_OFICIAL:
        sha256 = SHA256_OFICIAL
    huella = hashlib.sha256()
    if not url.lower().startswith(("https://", "http://127.0.0.1", "http://localhost")):
        raise ValueError("La descarga solo se permite por https")
    carpeta.mkdir(parents=True, exist_ok=True)
    final = carpeta / ARCHIVO
    parcial = carpeta / (ARCHIVO + ".part")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Organizador"})
        with urllib.request.urlopen(req, timeout=timeout) as r, parcial.open("wb") as f:
            total = 0
            while True:
                bloque = r.read(65536)
                if not bloque:
                    break
                total += len(bloque)
                if total > MAX_BYTES:
                    raise ValueError("El archivo es mas grande de lo esperado")
                huella.update(bloque)
                f.write(bloque)
        if total < MIN_BYTES:
            raise ValueError(f"El archivo descargado es demasiado chico ({total} bytes)")
        if sha256 and huella.hexdigest() != sha256:
            raise ValueError("La huella del archivo no coincide con la esperada. Puede que el repositorio lo haya actualizado: buscá una version nueva del programa o apuntá ORGANIZADOR_TESSDATA_URL a un espejo")
        parcial.replace(final)
        return final
    finally:
        parcial.unlink(missing_ok=True)
