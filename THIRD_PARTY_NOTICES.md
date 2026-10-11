# Avisos de licencias de terceros — Organizador de expedientes

El `Organizador.exe` empaqueta o utiliza los siguientes componentes de terceros.
Al redistribuir el programa, conservá este archivo.

| Componente | Licencia | Para qué se usa |
|---|---|---|
| [PyMuPDF](https://pymupdf.readthedocs.io/) (motor MuPDF) | **AGPL-3.0** / comercial de Artifex | Lectura de PDF, renderizado y OCR. **Es la razón por la que el Organizador se distribuye bajo AGPL-3.0.** |
| Motor [Tesseract OCR](https://github.com/tesseract-ocr/tesseract) (incluido por PyMuPDF) | Apache-2.0 | Reconocimiento de texto en PDFs escaneados |
| [spa.traineddata](https://github.com/tesseract-ocr/tessdata_fast) (tessdata_fast) | Apache-2.0 | Idioma español del OCR. Se descarga aparte, solo si el usuario lo pide, desde la fuente oficial con SHA-256 verificado (`app/ocr_setup.py`) |
| [Flask](https://flask.palletsprojects.com/) (con Werkzeug, Jinja2, itsdangerous, click, blinker) | BSD-3-Clause | Servidor web local de la interfaz |
| [python-docx](https://github.com/python-openxml/python-docx) | Apache-2.0 | Lectura de archivos .docx |
| [PyInstaller](https://pyinstaller.org/) (bootloader) | GPL-2.0 con excepción de bootloader | Armado del `.exe` (solo en la PC de quien construye; la excepción del bootloader hace que el `.exe` no arrastre esa GPL) |
| [pytest](https://pytest.org/) | MIT | Solo desarrollo y tests; no se incluye en el `.exe` |
| [Inter](https://rsms.me/inter/) | SIL Open Font License 1.1 | Tipografía de la interfaz (texto en `app/static/fonts/OFL-inter.txt`) |
| [IBM Plex Mono](https://www.ibm.com/plex/) | SIL Open Font License 1.1 | Tipografía de la interfaz (texto en `app/static/fonts/OFL-ibm-plex-mono.txt`) |
| [DM Serif Display](https://github.com/googlefonts/dmserif) | SIL Open Font License 1.1 | Tipografía de la interfaz (texto en `app/static/fonts/OFL-dm-serif-display.txt`) |

## Licencia del Organizador

El código del Organizador (`app/`) se distribuye bajo **GNU AGPL v3.0** (texto
completo en `app/LICENSE`), principalmente porque PyMuPDF/MuPDF es AGPL-3.0.

Esto significa, en resumen, que podés usarlo, compartirlo y modificarlo
libremente, pero si lo distribuís (por ejemplo, el `Organizador.exe` a
colegas) tenés que ofrecer también el código fuente bajo la misma licencia.
Cada paquete de release generado con `construir_exe.bat` incluye la fuente
(`Organizador-<versión>-fuente.zip`) para que sea automático cumplir con esto.

Si necesitás distribuir el programa sin esa obligación, la alternativa es
adquirir una licencia comercial de PyMuPDF (Artifex) o reemplazar esa librería;
ver `docs/analisis-distribucion-colegas.md`.
