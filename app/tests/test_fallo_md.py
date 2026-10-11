from fallo_md import a_markdown, convertir, limpiar

CRUDO = """PODER JUDICIAL DE MISIONES
1
SUPERIOR TRIBUNAL DE JUSTICIA DE LA PROVINCIA DE MISIONES. Posadas, 3 de mayo de 2021.
VISTOS: los autos "PEREZ JUAN c/ GOMEZ SA s/ Danos".
PODER JUDICIAL DE MISIONES
2
CONSIDERANDO: que la regu-
lacion de honorarios debe
respetar la ley XII N 4.
PODER JUDICIAL DE MISIONES
Pagina 3 de 3
Por ello, el Superior Tribunal de Justicia RESUELVE: hacer lugar al recurso.
"""


def test_limpiar_quita_encabezados_repetidos_numeros_de_pagina_y_une_palabras():
    t = limpiar(CRUDO)
    assert "PODER JUDICIAL DE MISIONES" not in t and "Pagina 3" not in t
    assert "regulacion de honorarios debe respetar" in t


def test_markdown_con_ficha_y_secciones(tmp_path):
    md = a_markdown(tmp_path / "fallo.pdf", CRUDO)
    assert "- **tribunal:** stj_misiones" in md
    assert "## Vistos" in md and "## Considerando" in md and "## Resuelve" in md


def test_convertir_omite_duplicados(tmp_path):
    for n in ("a.txt", "b.txt"):
        (tmp_path / "in").mkdir(exist_ok=True)
        (tmp_path / "in" / n).write_text(CRUDO, encoding="utf-8")
    r = convertir([tmp_path / "in"], tmp_path / "out")
    assert (r["convertidos"], r["duplicados"]) == (1, 1)
    assert len(list((tmp_path / "out").iterdir())) == 1


def test_compacto_conserva_encabezado_y_final():
    from fallo_md import compactar
    md = "CABECERA " + "x" * 20000 + " RESUELVE: hacer lugar."
    c = compactar(md, 100, 200)
    assert c.startswith("CABECERA") and c.endswith("hacer lugar.") and len(c) < 500
