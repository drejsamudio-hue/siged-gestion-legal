import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import fitz

import kb_publicar as K

TEXTO = "Artículo 1.- Objeto de la ley. " * 10


def pdf(carpeta, nombre, texto=TEXTO):
    carpeta.mkdir(parents=True, exist_ok=True)
    p = carpeta / nombre
    doc = fitz.open()
    doc.new_page().insert_textbox(fitz.Rect(36, 36, 560, 800), texto, fontsize=9)
    doc.save(str(p))
    return p


def test_publica_fallo(tmp_path):
    f = pdf(tmp_path / "o", "Perez c Gomez.pdf", "VISTOS Y CONSIDERANDO: " + "se resuelve el caso. " * 10)
    r = K.publicar(f, "jurisprudencia", "", tmp_path / "c")
    assert r == tmp_path / "c" / "fallos" / "Perez c Gomez.md"
    assert "Perez c Gomez" in r.read_text(encoding="utf-8")


def test_publica_norma_misiones(tmp_path):
    f = pdf(tmp_path / "o", "Ley I - N 89.pdf")
    r = K.publicar(f, "rama", "legislacion_misiones", tmp_path / "c")
    assert r == tmp_path / "c" / "legislacion" / "misiones" / "ley-i-n89.md"
    assert r.exists()


def test_norma_sin_id_no_publica(tmp_path):
    f = pdf(tmp_path / "o", "apuntes.pdf")
    assert K.publicar(f, "rama", "legislacion_nacion", tmp_path / "c") is None
    assert not (tmp_path / "c").exists()


def test_no_pisa_existente(tmp_path):
    f = pdf(tmp_path / "o", "Ley I - N 89.pdf")
    destino = tmp_path / "c" / "legislacion" / "misiones" / "ley-i-n89.md"
    destino.parent.mkdir(parents=True)
    destino.write_text("previo", encoding="utf-8")
    assert K.publicar(f, "rama", "legislacion_misiones", tmp_path / "c") is None
    assert destino.read_text(encoding="utf-8") == "previo"


def test_motivo_expediente_no_publica(tmp_path):
    f = pdf(tmp_path / "o", "Ley I - N 89.pdf")
    assert K.publicar(f, "cartera", "id", tmp_path / "c") is None


def test_ordenanza_por_nombre_va_a_municipal(tmp_path):
    f = pdf(tmp_path / "o", "Ordenanza XII - N 115.pdf")
    r = K.publicar(f, "rama", "legislacion_misiones", tmp_path / "c")
    assert r == tmp_path / "c" / "legislacion" / "municipal" / "ordenanza-xii-n115.md"
    assert r.exists()


def test_ordenanza_por_texto_va_a_municipal(tmp_path):
    f = pdf(tmp_path / "o", "Ley X - N 18.pdf", "ORDENANZA Nº 18\n" + TEXTO)
    r = K.publicar(f, "rama", "legislacion_misiones", tmp_path / "c")
    assert r == tmp_path / "c" / "legislacion" / "municipal" / "ordenanza-x-n18.md"
