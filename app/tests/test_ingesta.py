import csv
import json
import sys

import fitz
import pytest

import ingesta as I
from cartera import Causa, guardar, normalizar_expte

CUERPO = "Providencia del juzgado. Se tiene presente lo manifestado por la parte y se ordena el traslado. " * 2
FIRMA = " Tomo 12 Folio 34 del Colegio de Abogados."
NOTA_DOCTRINAL = (
    "Nota a fallo. El dano punitivo del art. 52 bis de la ley 24.240 y la multa civil en la relacion de "
    "consumo. Segun la doctrina y la jurisprudencia del tribunal, el derecho del consumidor exige "
    "responsabilidad del proveedor. " * 6
)


@pytest.fixture
def entorno(tmp_path, monkeypatch):
    base = tmp_path / "SIGED"
    for d in ("01_Expedientes/2022-perez-gomez", "01_Expedientes/2023-vidal-luna", "_INBOX", "_SISTEMA"):
        (base / d).mkdir(parents=True)
    for nombre, valor in {
        "BASE": base, "INBOX": base / "_INBOX", "CASOS": base / "01_Expedientes", "SISTEMA": base / "_SISTEMA",
        "RUTEO_CSV": base / "_SISTEMA" / "INGESTA_RUTEO.csv", "TANDAS_CSV": base / "_SISTEMA" / "TANDAS.csv", "CARTERA_JSON": base / "_SISTEMA" / "cartera.json",
        "ALIAS_CARTERA": base / "_SISTEMA" / "aliases_cartera.json", "ALIAS_FILE": tmp_path / "sin_aliases.json",
    }.items():
        monkeypatch.setattr(I, nombre, valor)
    monkeypatch.setattr(I, "_exptes_cache", None)
    monkeypatch.setattr(I, "_indice_cache", (-1.0, I.IndiceCartera([])))
    monkeypatch.setattr(I, "_alias_cache", ((-1.0, -1.0), []))
    return base


def cartera(base, *causas):
    guardar(list(causas), base / "_SISTEMA" / "cartera.json")


def causa(numero, carpeta, id_expediente=None):
    return Causa(normalizar_expte(numero), id_expediente=id_expediente, carpeta=carpeta)


def escribir(tmp_path, nombre, texto):
    p = tmp_path / nombre
    if p.suffix == ".pdf":
        doc = fitz.open()
        doc.new_page().insert_textbox(fitz.Rect(36, 36, 560, 800), texto, fontsize=9)
        doc.save(str(p))
    else:
        p.write_text(texto, encoding="utf-8")
    return p


def test_id_de_siged_en_el_nombre_manda_a_la_causa(entorno, tmp_path):
    cartera(entorno, causa("111111/2022", "2022-perez-gomez", "555555"))
    d = I.destino_de(escribir(tmp_path, "999999-2020__user0000-id555555.txt", CUERPO))
    assert d.carpeta == entorno / "01_Expedientes" / "2022-perez-gomez" / "01_siged"
    assert (d.motivo, d.detalle, d.confianza) == ("cartera", "id", "alta")


def test_numero_en_el_nombre_y_escrito_firmado(entorno, tmp_path):
    cartera(entorno, causa("111111/2022", "2022-perez-gomez"))
    d = I.destino_de(escribir(tmp_path, "escrito 111111-2022 final.txt", CUERPO + FIRMA))
    assert d.carpeta == entorno / "01_Expedientes" / "2022-perez-gomez" / "00_escritos_propios"
    assert (d.motivo, d.detalle, d.confianza) == ("cartera", "numero_nombre", "alta")


def test_numero_pegado_al_anio_como_en_los_recibos(entorno, tmp_path):
    cartera(entorno, causa("77123/2023", "2023-vidal-luna"))
    d = I.destino_de(escribir(tmp_path, "PLAZO_FIJO_EXPTE_771232023_BIS_12.txt", CUERPO))
    assert d.carpeta.parent.name == "2023-vidal-luna"


def test_fecha_de_guardado_no_es_numero_de_expediente(entorno, tmp_path):
    cartera(entorno, causa("111111/2022", "2022-perez-gomez"))
    d = I.destino_de(escribir(tmp_path, "111111-2022-05-08_10-00-00.txt", CUERPO))
    assert d.motivo != "cartera"


def test_bis_con_carpeta_propia_gana_al_principal(entorno, tmp_path):
    cartera(entorno, causa("111111/2022", "2022-perez-gomez"), causa("111111/2022 bis1/23", "2023-vidal-luna"))
    a = I.destino_de(escribir(tmp_path, "111111-2022__id1.txt", CUERPO))
    assert a.carpeta.parent.name == "2022-perez-gomez"
    b = I.destino_de(escribir(tmp_path, "111111-2022 bis1-23 cedula.txt", CUERPO))
    assert b.carpeta.parent.name == "2023-vidal-luna"


def test_numero_en_el_texto_de_la_cartera_tiene_confianza_media(entorno, tmp_path):
    cartera(entorno, causa("111111/2022", "2022-perez-gomez"))
    d = I.destino_de(escribir(tmp_path, "cedula.txt", "Expte. N 111111/2022. " + CUERPO))
    assert (d.motivo, d.detalle, d.confianza) == ("cartera", "numero_texto", "media")


def test_alias_ignora_tildes_del_nombre(entorno, tmp_path):
    (entorno / "_SISTEMA" / "aliases_cartera.json").write_text(
        json.dumps({"aliases": [{"pattern": r"(?<![a-z])vidal(?![a-z])", "caso": "2023-vidal-luna"}]}), encoding="utf-8")
    assert I._match_alias("Escrito de Vidál") == "2023-vidal-luna"


def test_nota_doctrinal_va_a_su_rama_y_no_a_jurisprudencia(entorno, tmp_path):
    d = I.destino_de(escribir(tmp_path, "nota-punitivo.md", NOTA_DOCTRINAL))
    assert d.carpeta.parent == entorno / "03_Doctrina" / "consumo"
    assert d.motivo == "doctrina" and d.detalle.startswith("nota |")
    assert d.confianza in {"alta", "media"}


def test_pdf_que_no_es_doctrina_no_ensucia_03_doctrina(entorno, tmp_path):
    pdf = tmp_path / "manual.pdf"
    doc = fitz.open()
    doc.new_page().insert_text((72, 72), "Manual de servicio de la moto. Cambio de aceite y bujias. " * 6)
    doc.save(str(pdf))
    d = I.destino_de(pdf)
    assert (d.motivo, d.confianza) == ("sin_clasificar", "baja")
    assert d.carpeta == entorno / "_INBOX" / "sin_clasificar"


def test_confianza_de_los_motivos_existentes(entorno, tmp_path):
    assert I.destino_de(tmp_path / "x.exe").confianza == "baja"
    assert I.destino_de(escribir(tmp_path, "vacio.txt", "corto")).confianza == "baja"


def correr(monkeypatch, *argumentos):
    monkeypatch.setattr(sys, "argv", ["ingesta.py", *argumentos])
    I.main()


def test_main_mueve_registra_y_respeta_omitir(entorno, tmp_path, monkeypatch):
    cartera(entorno, causa("111111/2022", "2022-perez-gomez"))
    origen = tmp_path / "origen"
    origen.mkdir()
    escribir(origen, "cedula 111111-2022.pdf", CUERPO)
    escribir(origen, "nota.md", NOTA_DOCTRINAL)
    (origen / "logo.svg").write_text("<svg/>")

    correr(monkeypatch, "--src", str(origen), "--dry-run", "--csv", str(tmp_path / "p.csv"))
    filas = list(csv.DictReader((tmp_path / "p.csv").open(encoding="utf-8-sig")))
    assert {f["motivo"]: f["accion"] for f in filas} == {"cartera": "mover", "doctrina": "mover", "formato_desconocido": "queda"}
    assert (origen / "nota.md").exists()

    correr(monkeypatch, "--src", str(origen), "--omitir", "doctrina")
    assert (entorno / "01_Expedientes" / "2022-perez-gomez" / "01_siged" / "cedula 111111-2022.pdf").exists()
    assert (origen / "nota.md").exists() and (origen / "logo.svg").exists()
    assert len(I.RUTEO_CSV.read_text(encoding="utf-8").splitlines()) == 2


SENTENCIA_PUNITIVO = (
    "VISTOS Y CONSIDERANDO: el dano punitivo del art. 52 bis de la ley 24.240 y la multa civil en la relacion "
    "de consumo. Segun la doctrina y la jurisprudencia del tribunal, el derecho del consumidor exige "
    "responsabilidad del proveedor. RESUELVE: hacer lugar al reclamo. " * 6
)
ARTICULO_CSJN = (
    "El dano punitivo del art. 52 bis de la ley 24.240 y la multa civil en la relacion de consumo. "
    "Segun la doctrina, la Corte Suprema de Justicia de la Nacion y el derecho del consumidor exigen "
    "responsabilidad del proveedor. " * 6
)


def test_texto_con_forma_de_sentencia_nunca_sale_como_seguro(entorno, tmp_path):
    d = I.destino_de(escribir(tmp_path, "resolucion-punitivo.md", SENTENCIA_PUNITIVO))
    assert d.motivo in {"doctrina", "rama"}
    assert d.confianza != "alta"


def test_cartera_ignora_carpeta_que_no_existe_en_disco(entorno, tmp_path):
    cartera(entorno, causa("111111/2022", "2022-fantasma-inexistente"))
    d = I.destino_de(escribir(tmp_path, "escrito 111111-2022 final.txt", CUERPO + FIRMA))
    assert d.motivo != "cartera"


def test_articulo_que_cita_a_la_corte_sin_marcas_de_sentencia_tiene_confianza_media(entorno, tmp_path):
    d = I.destino_de(escribir(tmp_path, "articulo-csjn.md", ARTICULO_CSJN))
    assert d.motivo == "jurisprudencia"
    assert d.confianza == "media"


def test_omitir_rechaza_motivos_desconocidos(entorno, tmp_path, monkeypatch):
    with pytest.raises(SystemExit):
        correr(monkeypatch, "--src", str(tmp_path), "--omitir", "expediente_nuevoo")


def test_omitir_acepta_todos_los_motivos_conocidos():
    assert {"cartera", "doctrina", "expediente_nuevo", "sin_clasificar"} <= set(I.MOTIVOS)


def test_cartera_json_corrupto_no_rompe_el_ruteo(entorno, tmp_path, capsys):
    (entorno / "_SISTEMA" / "cartera.json").write_text("{esto no es json", encoding="utf-8")
    d = I.destino_de(escribir(tmp_path, "escrito 111111-2022.txt", CUERPO))
    assert d.motivo != "cartera"
    assert "cartera" in capsys.readouterr().err.lower()


def test_aliases_corruptos_no_rompen_el_ruteo(entorno, tmp_path, capsys):
    (entorno / "_SISTEMA" / "aliases_cartera.json").write_text("[[[", encoding="utf-8")
    assert I._match_alias("Escrito de Vidal") is None
    assert "alias" in capsys.readouterr().err.lower()


def test_aliases_generados_corruptos_no_pierden_los_manuales(entorno, tmp_path, monkeypatch):
    manual = tmp_path / "aliases_manuales.json"
    manual.write_text(json.dumps({"aliases": [{"pattern": "vidal", "caso": "2023-vidal-luna"}]}), encoding="utf-8")
    monkeypatch.setattr(I, "ALIAS_FILE", manual)
    (entorno / "_SISTEMA" / "aliases_cartera.json").write_text("[[[", encoding="utf-8")
    assert I._match_alias("Escrito de Vidal") == "2023-vidal-luna"


def test_archivo_de_un_bis_va_a_su_subcarpeta(entorno, tmp_path):
    (entorno / "01_Expedientes" / "2022-perez-gomez" / "bis1-23").mkdir()
    cartera(entorno, causa("111111/2022", "2022-perez-gomez"), causa("111111/2022 bis1/23", "2022-perez-gomez/bis1-23"))
    d = I.destino_de(escribir(tmp_path, "111111-2022 bis1-23 cedula.pdf", CUERPO))
    assert d.carpeta == entorno / "01_Expedientes" / "2022-perez-gomez" / "bis1-23" / "01_siged"
    p = I.destino_de(escribir(tmp_path, "111111-2022 providencia.pdf", CUERPO))
    assert p.carpeta == entorno / "01_Expedientes" / "2022-perez-gomez" / "01_siged"


def test_carpeta_prevista_se_usa_aunque_no_exista_todavia(entorno, tmp_path):
    guardar([Causa(normalizar_expte("111111/2024"), carpeta_prevista="2024-vidal-luna")], entorno / "_SISTEMA" / "cartera.json")
    d = I.destino_de(escribir(tmp_path, "111111-2024 cedula.pdf", CUERPO))
    assert d.carpeta == entorno / "01_Expedientes" / "2024-vidal-luna" / "01_siged"
    assert (d.motivo, d.detalle, d.confianza) == ("cartera", "numero_nombre", "alta")


def con_caratula(numero, caratula, carpeta):
    return Causa(normalizar_expte(numero), caratula=caratula, carpeta=carpeta)


def test_partes_unicas_se_reconocen_en_el_nombre_del_archivo(entorno, tmp_path):
    (entorno / "01_Expedientes" / "2021-vidal-juan-moreno").mkdir()
    cartera(entorno, con_caratula("222222/2021", "VIDAL JUAN C/ MORENO SA S/ Danos", "2021-vidal-juan-moreno"))
    d = I.destino_de(escribir(tmp_path, "Vidal Juan contra Moreno - cedula.pdf", CUERPO))
    assert d.carpeta == entorno / "01_Expedientes" / "2021-vidal-juan-moreno" / "01_siged"
    assert (d.motivo, d.detalle, d.confianza) == ("cartera", "partes", "media")


def test_apellido_compartido_por_dos_causas_no_decide(entorno, tmp_path):
    (entorno / "01_Expedientes" / "2021-vidal-juan-moreno").mkdir()
    (entorno / "01_Expedientes" / "2022-vidal-juan-lopez").mkdir()
    cartera(entorno,
            con_caratula("222222/2021", "VIDAL JUAN C/ MORENO SA S/ Danos", "2021-vidal-juan-moreno"),
            con_caratula("333333/2022", "VIDAL JUAN C/ LOPEZ SA S/ Danos", "2022-vidal-juan-lopez"))
    assert I.destino_de(escribir(tmp_path, "vidal escrito.txt", CUERPO)).motivo != "cartera"
    d = I.destino_de(escribir(tmp_path, "vidal lopez escrito.txt", CUERPO))
    assert d.carpeta.parent.name == "2022-vidal-juan-lopez"


def test_borradores_de_la_causa_van_a_escritos_propios(entorno, tmp_path):
    import docx
    cartera(entorno, causa("111111/2022", "2022-perez-gomez", "555555"))
    propios = entorno / "01_Expedientes" / "2022-perez-gomez" / "00_escritos_propios"
    siged = entorno / "01_Expedientes" / "2022-perez-gomez" / "01_siged"
    d = docx.Document()
    d.add_paragraph("Expte. N 111111/2022. " + CUERPO)
    d.save(str(tmp_path / "contestacion perez.docx"))
    assert I.destino_de(tmp_path / "contestacion perez.docx").carpeta == propios
    assert I.destino_de(escribir(tmp_path, "Demanda_Perez 111111-2022 v2.md", CUERPO)).carpeta == propios
    assert I.destino_de(escribir(tmp_path, "notas_caso_v3.txt", "Expte. N 111111/2022. " + CUERPO)).carpeta == propios
    assert I.destino_de(escribir(tmp_path, "111111-2022__user0000-id555555.md", CUERPO)).carpeta == siged
    assert I.destino_de(escribir(tmp_path, "expediente_111111_2022_limpio.txt", CUERPO)).carpeta == siged

def test_proyectos_de_codigo_y_carpetas_ignoradas_no_se_recorren(tmp_path):
    for rel in ("web/package.json", "web/src/app.js", "web/leeme.txt", "bot/.git/HEAD", "bot/main.py",
                "sin_clasificar/viejo.txt", "skills-main/a/doc.md", "mi-skill/SKILL.md", "mi-skill/ref.md", "cedula.pdf", "sub/escrito.docx"):
        (tmp_path / rel).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / rel).write_text("x")
    assert sorted(p.relative_to(tmp_path).as_posix() for p in I.archivos_pendientes(tmp_path)) == [
        "cedula.pdf", "sub/escrito.docx"]


def test_aplicar_csv_mueve_solo_lo_aprobado_sin_reclasificar(entorno, tmp_path, monkeypatch, capsys):
    origen = tmp_path / "origen"
    origen.mkdir()
    a, b, c = (escribir(origen, n, CUERPO) for n in ("a.txt", "b.txt", "c.txt"))
    destino = entorno / "01_Expedientes" / "2023-vidal-luna" / "00_escritos_propios"
    filas = [["archivo", "destino", "motivo", "detalle", "confianza", "accion"],
             [a, destino, "cartera", "manual", "media", "mover"],
             [b, destino, "cartera", "", "media", "queda"],
             [origen / "ya-no-esta.txt", destino, "cartera", "", "media", "mover"],
             [c, tmp_path / "fuera-de-la-base", "cartera", "", "media", "mover"]]
    csv_ok = tmp_path / "aprobado.csv"
    with csv_ok.open("w", newline="", encoding="cp1252") as f:
        csv.writer(f, delimiter=";").writerows(filas)  # como lo guarda Excel en castellano

    correr(monkeypatch, "--aplicar-csv", str(csv_ok))

    assert (destino / "a.txt").exists() and not a.exists()
    assert b.exists() and c.exists()
    registro = list(csv.DictReader(I.RUTEO_CSV.open(encoding="utf-8")))
    assert [(r["motivo"], r["detalle"]) for r in registro] == [("cartera", "manual")]
    salida = capsys.readouterr().out
    assert "ya-no-esta.txt" in salida and "fuera-de-la-base" in salida


def test_causa_donde_el_actor_es_el_estudio_no_se_reconoce_por_nombre(entorno, tmp_path, monkeypatch):
    monkeypatch.setattr(I, "_PALABRAS_GENERICAS", I._PALABRAS_GENERICAS | {"robles", "marcos", "andres"})
    (entorno / "01_Expedientes" / "2020-robles-banco-macro").mkdir()
    cartera(entorno, con_caratula("444444/2020", "ROBLES MARCOS ANDRES C/ BANCO MACRO SA S/ Sumarisimos", "2020-robles-banco-macro"))
    assert I.destino_de(escribir(tmp_path, "macro banco resumen.txt", CUERPO)).motivo != "cartera"


def test_jurisprudencia_va_por_tema_y_el_tribunal_queda_en_el_detalle(entorno, tmp_path):
    d = I.destino_de(escribir(tmp_path, "articulo-csjn.md", ARTICULO_CSJN))
    assert d.carpeta.parent == entorno / "02_Jurisprudencia" / "consumo"
    assert d.detalle == "csjn"


def test_ninguna_ruta_de_jurisprudencia_queda_por_tribunal(entorno, tmp_path):
    textos = [ARTICULO_CSJN, SENTENCIA_PUNITIVO, "Superior Tribunal de Justicia de Misiones, Posadas. " + CUERPO * 3]
    for i, t in enumerate(textos):
        d = I.destino_de(escribir(tmp_path, f"f{i}.md", t))
        if (entorno / "02_Jurisprudencia") in d.carpeta.parents:
            assert d.carpeta.parent.parent == entorno / "02_Jurisprudencia"
            assert d.carpeta.parent.name not in {"misiones", "nacional"}


def test_aplicar_registra_la_tanda_y_deshacer_la_revierte(entorno, tmp_path):
    origen = tmp_path / "o"
    origen.mkdir()
    a, b = escribir(origen, "a.txt", CUERPO), escribir(origen, "b.txt", CUERPO)
    dst = entorno / "01_Expedientes" / "2023-vidal-luna" / "01_siged"
    r = I.aplicar_filas([{"archivo": str(a), "destino": str(dst), "accion": "mover"},
                         {"archivo": str(b), "destino": str(dst), "accion": "mover"}], "prueba.csv")
    assert (r["movidos"], r["tanda"]) == (2, "t0001")
    t = I.leer_tandas()[0]
    assert (t["origen"], t["primera_fila"], t["ultima_fila"]) == ("prueba.csv", "0", "1")

    escribir(origen, "b.txt", "otro")  # el origen de b quedo ocupado
    d = I.deshacer_filas(0, 1)
    assert d["restaurados"] == 1 and a.exists() and (dst / "b.txt").exists()
    assert any("ocupado" in x for x in d["avisos"])
    assert I.leer_ruteo()[-1]["motivo"] == "deshacer"
    assert I.leer_tandas()[-1]["origen"] == "deshacer:0-1"


def test_tandas_del_historial_viejo_se_derivan_por_pausas():
    filas = [{"fecha": f} for f in ("2026-09-26T10:00:00", "2026-09-26T10:00:30", "2026-09-26T11:00:00",
                                     "2026-09-26T11:00:10", "2026-09-26T12:00:00")]
    explicitas = [{"id": "t0001", "fecha": "x", "origen": "c.csv", "movidos": "1", "primera_fila": "4", "ultima_fila": "4"}]
    ids = [t["id"] for t in I.tandas_historicas(filas, explicitas)]
    assert ids == ["h0-1", "h2-3", "t0001"]


def test_pdf_escaneado_se_lee_por_ocr(tmp_path, monkeypatch):
    import extractor as X
    if not X.ocr_disponible():
        pytest.skip("Tesseract con espanol no instalado")
    monkeypatch.setattr(X, "OCR_CACHE", tmp_path / "cache")
    texto = fitz.open()
    texto.new_page().insert_textbox(fitz.Rect(40, 40, 570, 500), "PROVIDENCIA. Posadas, 3 de marzo. Agreguese la cedula acompanada y tengase presente. Notifiquese a las partes por el termino de ley.", fontsize=16)
    imagen = texto[0].get_pixmap(dpi=200)
    escaneado = fitz.open()
    escaneado.new_page().insert_image(escaneado[0].rect, pixmap=imagen)
    escaneado.save(str(tmp_path / "scan.pdf"))
    t, err = X.extraer_universal(tmp_path / "scan.pdf")
    assert err == "ocr" and "PROVIDENCIA" in t.upper()
    assert list((tmp_path / "cache").iterdir())


def test_ocr_ilegible_se_distingue_del_texto_real():
    import extractor as X
    assert X.calidad_texto("Posadas, 3 de marzo. Se tiene presente lo manifestado por la parte en autos.") > X.OCR_CALIDAD_MINIMA
    assert X.calidad_texto("AEAS Ae o NE eaos E a e o OeeassaoTEESEERAoa3% A AE e e o A O e et dead AU ula") < X.OCR_CALIDAD_MINIMA


def test_numero_ajeno_a_la_cartera_no_crea_carpeta(entorno, tmp_path):
    texto = "Expte. N 987654/2019. Autos: RUIZ JUAN c/ SOSA PEDRO s/ Danos. " + CUERPO + FIRMA
    d = I.destino_de(escribir(tmp_path, "escrito.md", texto))
    assert d.motivo != "expediente_nuevo"
    assert "987654" not in str(d.carpeta)


def test_aplicar_puede_renombrar_y_deshacer_restaura_el_nombre(entorno, tmp_path):
    origen = tmp_path / "o"
    origen.mkdir()
    a = escribir(origen, "fallo (12).pdf.txt", CUERPO)
    dst = entorno / "02_Jurisprudencia" / "consumo" / "dano-punitivo"
    r = I.aplicar_filas([{"archivo": str(a), "destino": str(dst), "accion": "mover",
                          "nombre_nuevo": "2023-03-12_STJ_perez-gomez"}], "x")
    assert r["movidos"] == 1 and (dst / "2023-03-12_STJ_perez-gomez.txt").exists()
    I.deshacer_filas(0, 0)
    assert a.exists()


def _dos_fallos(tmp_path):
    origen = tmp_path / "origen"
    origen.mkdir()
    escribir(origen, "articulo-csjn.md", ARTICULO_CSJN)
    escribir(origen, "articulo-csjn-2.md", ARTICULO_CSJN)
    return origen


def test_main_publica_y_reindexa_una_vez(entorno, tmp_path, monkeypatch):
    origen = _dos_fallos(tmp_path)
    llamadas, rebuilds = [], []
    monkeypatch.setattr(I.kb_publicar, "publicar", lambda p, m, d, *a: llamadas.append((p, m)) or p)
    monkeypatch.setattr(I.kb_index, "rebuild", lambda *a: rebuilds.append(a))
    correr(monkeypatch, "--src", str(origen), "--incluir-no-clasificados")
    assert len(llamadas) == 2 and all(p.exists() for p, _ in llamadas)
    assert len(rebuilds) == 1


def test_main_dry_run_no_publica(entorno, tmp_path, monkeypatch):
    origen = _dos_fallos(tmp_path)
    llamadas, rebuilds = [], []
    monkeypatch.setattr(I.kb_publicar, "publicar", lambda *a: llamadas.append(a))
    monkeypatch.setattr(I.kb_index, "rebuild", lambda *a: rebuilds.append(a))
    correr(monkeypatch, "--src", str(origen), "--dry-run")
    assert not llamadas and not rebuilds


def test_aplicar_filas_publica_y_reindexa_una_vez(entorno, tmp_path, monkeypatch):
    a = escribir(tmp_path, "uno.txt", CUERPO)
    b = escribir(tmp_path, "dos.txt", CUERPO)
    dst = entorno / "dest"
    rebuilds = []
    monkeypatch.setattr(I.kb_publicar, "publicar", lambda p, m, d, *x: p)
    monkeypatch.setattr(I.kb_index, "rebuild", lambda *x: rebuilds.append(x))
    filas = [{"archivo": str(f), "destino": str(dst), "accion": "mover", "motivo": "jurisprudencia"} for f in (a, b)]
    r = I.aplicar_filas(filas, "t")
    assert r["publicados"] == 2 and len(rebuilds) == 1


def test_error_de_publicar_o_rebuild_no_corta_la_ingesta(entorno, tmp_path, monkeypatch):
    origen = _dos_fallos(tmp_path)

    def falla(*a):
        raise RuntimeError("boom")

    monkeypatch.setattr(I.kb_publicar, "publicar", falla)
    monkeypatch.setattr(I.kb_index, "rebuild", falla)
    correr(monkeypatch, "--src", str(origen), "--incluir-no-clasificados")
    assert not list(origen.iterdir())
    monkeypatch.setattr(I.kb_publicar, "publicar", lambda p, *a: p)
    origen2 = _dos_fallos(tmp_path / "x") if (tmp_path / "x").mkdir() is None else None
    correr(monkeypatch, "--src", str(origen2), "--incluir-no-clasificados")
    assert not list(origen2.iterdir())


def test_asegurar_estructura_crea_las_carpetas_de_una_base_vacia(tmp_path, monkeypatch):
    b = tmp_path / "base"
    for nombre, valor in {"INBOX": b / "_INBOX", "CASOS": b / "01_Expedientes", "SISTEMA": b / "_SISTEMA"}.items():
        monkeypatch.setattr(I, nombre, valor)
    I.asegurar_estructura()
    assert all((b / d).is_dir() for d in ("_INBOX", "01_Expedientes", "_SISTEMA"))


def test_alias_que_apunta_fuera_de_la_base_se_rechaza(entorno, tmp_path):
    (tmp_path / "fuera").mkdir()
    assert (entorno / "01_Expedientes" / ".." / ".." / "fuera").resolve() == (tmp_path / "fuera").resolve()
    err = I.validar_alias("secreto", "../../fuera")
    assert err is not None and "fuera" in err
    assert I.validar_alias("perez", "2022-perez-gomez") is None


def test_mover_no_sale_de_la_base(entorno, tmp_path):
    origen = escribir(tmp_path, "doc.txt", CUERPO)
    fuera = tmp_path / "fuera"
    fuera.mkdir()
    with pytest.raises(ValueError, match="fuera de la base"):
        I.mover(origen, fuera, "prueba")
    assert origen.exists() and not list(fuera.iterdir())


def test_si_falla_el_registro_el_archivo_vuelve_al_origen(entorno, tmp_path, monkeypatch):
    origen = escribir(tmp_path, "doc.txt", CUERPO)
    destino = entorno / "01_Expedientes" / "2022-perez-gomez"

    def sin_disco(*a, **k):
        raise OSError("disco lleno")

    monkeypatch.setattr(I, "_anotar", sin_disco)
    with pytest.raises(OSError, match="volvio"):
        I.mover(origen, destino, "prueba")
    assert origen.exists() and not (destino / "doc.txt").exists()


def test_si_falla_el_registro_al_deshacer_el_archivo_no_queda_sin_historial(entorno, tmp_path, monkeypatch):
    origen = escribir(tmp_path, "doc.txt", CUERPO)
    destino = entorno / "01_Expedientes" / "2022-perez-gomez"
    movido = I.mover(origen, destino, "prueba")
    assert movido.exists() and not origen.exists()

    def sin_disco(*a, **k):
        raise OSError("sin permisos")

    monkeypatch.setattr(I, "_anotar", sin_disco)
    r = I.deshacer_filas(0, 0)
    assert r["restaurados"] == 0 and any("sin registro" in a for a in r["avisos"])
    assert movido.exists() and not origen.exists()


def test_un_enlace_simbolico_hacia_afuera_no_permite_salir_de_la_base(entorno, tmp_path):
    fuera = tmp_path / "fuera"
    fuera.mkdir()
    enlace = entorno / "01_Expedientes" / "2024-enlace"
    try:
        enlace.symlink_to(fuera, target_is_directory=True)
    except OSError:
        pytest.skip("este sistema no permite crear enlaces simbolicos sin permisos")
    err = I.validar_alias("secreto", "2024-enlace")
    assert err is not None and "fuera" in err
    origen = escribir(tmp_path, "doc.txt", CUERPO)
    with pytest.raises(ValueError, match="fuera de la base"):
        I.mover(origen, enlace, "prueba")
    assert origen.exists() and not list(fuera.iterdir())


@pytest.mark.parametrize("caso", ["../_SISTEMA", "..", ".", "absoluta"])
def test_alias_cargado_desde_archivo_no_sale_de_expedientes(entorno, caso):
    if caso == "absoluta":
        caso = str(entorno / "_SISTEMA")
    (entorno / "_SISTEMA" / "aliases_cartera.json").write_text(
        json.dumps({"aliases": [{"pattern": "vidal", "caso": caso}]}), encoding="utf-8")
    assert I._match_alias("escrito vidal") is None
