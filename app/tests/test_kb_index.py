import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import kb_index
from kb_index import construir, leer_ficha, norma_id, rebuild


def _fallo(corpus: Path, nombre: str, area: str, extra: str = "") -> None:
    d = corpus / "fallos"
    d.mkdir(parents=True, exist_ok=True)
    (d / nombre).write_text(
        f'---\ntribunal: "STJ"\nfecha: "02/09/2011"\nautos: "X c/ Y"\narea: "{area}"\ntema: "t"\n{extra}---\n\n# X\n',
        encoding="utf-8",
    )


def test_norma_id_formas():
    assert norma_id("Ley 24.240") == "24240"
    assert norma_id("LEY XII - N° 27") == "xii-n27"
    assert norma_id("LEY IV – Nº 50.pdf") == "iv-n50"
    assert norma_id("DOC-20241206-WA0198_.pdf") is None
    assert norma_id("hola") is None


def test_leer_ficha_yaml_y_bullets(tmp_path):
    a = tmp_path / "a.md"
    a.write_text('---\ntribunal: "STJ"\narea: "consumo"\n---\n\n# t\n', encoding="utf-8")
    assert leer_ficha(a) == {"tribunal": "STJ", "area": "consumo"}
    b = tmp_path / "b.md"
    b.write_text("# b\n\n- **tribunal:** CSJN\n- **normas:** Ley 24.240\n\ntexto\n", encoding="utf-8")
    assert leer_ficha(b) == {"tribunal": "CSJN", "normas": "Ley 24.240"}
    c = tmp_path / "c.md"
    c.write_text("nada\n", encoding="utf-8")
    assert leer_ficha(c) == {}


def test_construir_agrupa_fallos_por_area(tmp_path):
    _fallo(tmp_path, "a.md", "consumo")
    _fallo(tmp_path, "b.md", "consumo")
    _fallo(tmp_path, "c.md", "honorarios")
    idx = construir(tmp_path)
    assert sorted(idx["areas"]["consumo"]["fallos"]) == ["fallos/a.md", "fallos/b.md"]
    assert idx["cobertura"]["total_fallos"] == 3
    assert idx["raiz"] == str(tmp_path)
    assert idx["fallos"]["a"]["area"] == "consumo"


def test_norma_publicada_entra_en_area(tmp_path):
    d = tmp_path / "legislacion" / "nacion"
    d.mkdir(parents=True)
    (d / "ley-24240.md").write_text(
        '---\ntitulo: "Defensa del Consumidor"\narticulos: 3\n---\n\nArt. 1\n', encoding="utf-8")
    _fallo(tmp_path, "a.md", "consumo", 'normas: "Ley 24.240 art 4"\n')
    idx = construir(tmp_path)
    assert idx["normas"]["24240"]["articulos"] == 3
    assert idx["normas"]["24240"]["ruta"] == "legislacion/nacion/ley-24240.md"
    assert "24240" in idx["areas"]["consumo"]["normas"]
    assert idx["fallos"]["a"]["normas"] == ["24240"]
    assert "consumo" not in idx["cobertura"]["areas_sin_cobertura"]
    assert "honorarios" in idx["cobertura"]["areas_sin_cobertura"]


def test_fallo_sin_ficha_se_omite_con_aviso(tmp_path):
    (tmp_path / "fallos").mkdir()
    (tmp_path / "fallos" / "roto.md").write_text("sin ficha\n", encoding="utf-8")
    idx = construir(tmp_path)
    assert idx["cobertura"]["total_fallos"] == 0
    assert any("roto.md" in a for a in idx["avisos"])


def test_doctrina_por_area(tmp_path):
    d = tmp_path / "doctrina"
    d.mkdir()
    (d / "x.md").write_text("# X\n\n## consumo\n\ntexto\n", encoding="utf-8")
    (d / "y.md").write_text("# Y\n", encoding="utf-8")
    idx = construir(tmp_path)
    assert idx["areas"]["consumo"]["doctrina"] == ["doctrina/x.md"]
    assert idx["areas"]["laboral"]["doctrina"] == []


def test_rebuild_atomico(tmp_path):
    _fallo(tmp_path, "a.md", "consumo")
    ruta = rebuild(tmp_path)
    assert ruta == tmp_path / "LOCAL_INDEX.json"
    assert json.loads(ruta.read_text(encoding="utf-8"))["version"] == 1
    assert not list(tmp_path.glob("*.tmp"))


def test_norma_id_con_numero_y_sin_fechas():
    assert norma_id("Ley N° 24.240") == "24240"
    assert norma_id("Ley Nº 20.744") == "20744"
    assert norma_id("ley n. 24240") == "24240"
    assert norma_id("Ley Nro. 24.240") == "24240"
    assert norma_id("Ley XII N° 27") == "xii-n27"
    assert norma_id("12/2020") is None
    assert norma_id("20241206") is None


def test_fallo_duplicado_y_norma_duplicada_avisan(tmp_path):
    _fallo(tmp_path, "a.md", "consumo")
    (tmp_path / "fallos" / "sub").mkdir()
    _fallo(tmp_path / "fallos", "a.md", "honorarios")
    for d in ("nacion", "otra"):
        (tmp_path / "legislacion" / d).mkdir(parents=True)
        (tmp_path / "legislacion" / d / "ley-24240.md").write_text(f'---\ntitulo: "{d}"\n---\n', encoding="utf-8")
    idx = construir(tmp_path)
    assert idx["cobertura"]["total_fallos"] == 1
    assert any("slug duplicado" in a for a in idx["avisos"])
    assert idx["normas"]["24240"]["titulo"] == "nacion"
    assert any("norma duplicada 24240" in a for a in idx["avisos"])


def test_ordenanza_no_entra_en_normas(tmp_path):
    d = tmp_path / "legislacion" / "municipal"
    d.mkdir(parents=True)
    (d / "ordenanza-xii-n115.md").write_text('---\ntitulo: "Ordenanza"\narticulos: 1\n---\n', encoding="utf-8")
    idx = construir(tmp_path)
    assert "xii-n115" not in idx["normas"]
    assert idx["avisos"] == []
