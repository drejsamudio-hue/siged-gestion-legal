from cartera_fuentes import desde_propios_txt


def test_desde_propios_txt_separa_invalidas():
    txt = "# comentario\n\n123456-2024\n990011-15\n7654321-2024\n"
    causas, invalidas = desde_propios_txt(txt)
    assert [c.expte.clave for c in causas] == ["123456/2024", "7654321/2024"]
    assert invalidas == ["990011-15"]
