import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import fallo_md
import norma_md
from kb_index import leer_ficha

TEXTO = (
    "LEY XII - N 27\n"
    "ARTICULO 1.- Objeto. La presente ley regula el registro\n"
    "provincial de proveedores.\n"
    "Art. 2º Definiciones. A los fines de esta ley se entiende por proveedor\n"
    "toda persona inscripta.\n"
    "ARTICULO 2 bis.- Excepciones.\n"
)


def test_divide_por_articulo():
    md = norma_md.a_markdown_norma(TEXTO, "Ley XII-N27", "xii-n27")
    assert "articulos: 3" in md
    for h in ("## Artículo 1\n", "## Artículo 2\n", "## Artículo 2 bis\n"):
        assert h in md
    assert md.index("## Artículo 2\n") < md.index("## Artículo 2 bis\n")


def test_texto_corrido_se_conserva():
    md = norma_md.a_markdown_norma(TEXTO, "Ley XII-N27", "xii-n27")
    assert "provincial de proveedores." in md
    assert "toda persona inscripta." in md
    assert "Objeto." in md


def test_front_matter_legible_por_kb_index(tmp_path):
    p = tmp_path / "ley-xii-n27.md"
    p.write_text(norma_md.a_markdown_norma(TEXTO, "Ley XII-N27", "xii-n27"), encoding="utf-8")
    ficha = leer_ficha(p)
    assert ficha["titulo"] == "Ley XII-N27"
    assert str(ficha["articulos"]) == "3"


def test_sin_articulos_se_marca(tmp_path, monkeypatch):
    monkeypatch.setattr(fallo_md, "texto_completo", lambda p: "Texto sin estructura alguna de ley.")
    r = norma_md.convertir_norma(tmp_path / "x.pdf", tmp_path / "out", "24240")
    assert r["sin_articulos"] is True
    assert r["articulos"] == 0


def test_nombre_de_archivo(tmp_path, monkeypatch):
    monkeypatch.setattr(fallo_md, "texto_completo", lambda p: TEXTO)
    r = norma_md.convertir_norma(tmp_path / "Ley XII-N27.pdf", tmp_path / "out", "xii-n27")
    assert r["ruta"] == tmp_path / "out" / "ley-xii-n27.md"
    assert r["ruta"].exists()
    assert r["articulos"] == 3 and r["sin_articulos"] is False
    assert r["chars"] == len(r["ruta"].read_text(encoding="utf-8"))
