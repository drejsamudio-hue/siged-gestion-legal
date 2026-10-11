# Organizador de expedientes

Ordena en carpetas por causa los PDFs y documentos de tu estudio. Corre en tu computadora: **no envía nada a internet** y no usa ningún servicio externo.

## Qué hace

- Lleva una **cartera** con tus causas (número de expediente y carátula).
- Mira una carpeta desordenada (descargas, escritorio, un pendrive) y **propone** a qué causa va cada archivo, según el número de expediente, la carátula o el nombre.
- Vos revisás la propuesta, corregís lo que haga falta y **recién ahí** se mueven los archivos.
- Cada movimiento queda en un historial y **se puede deshacer**. Nunca borra ni pisa archivos.

## Instalación

**Con el programa (`Organizador.exe`)** — no hace falta instalar nada:

1. Copiá la carpeta del programa a tu computadora (por ejemplo, al escritorio).
2. Hacé doble clic en `Organizador.exe`. Se abre una ventana negra y, a los pocos segundos, el navegador.
3. **No cierres la ventana negra** mientras lo usás: cerrarla apaga el organizador.

Si Windows muestra "Windows protegió su PC", elegí "Más información" y "Ejecutar de todos modos": el programa no está firmado digitalmente.

**Lectura de PDFs escaneados (OCR):** no viene incluida. La primera vez que la necesites, abrí "Configuración" (abajo a la izquierda) y tocá "Instalar OCR en español". El programa baja el idioma español (2,3 MB) del repositorio oficial de Tesseract, <https://github.com/tesseract-ocr/tessdata_fast>, y lo guarda en `%APPDATA%\Organizador\tessdata`. Solo se conecta a internet cuando tocás ese botón. Sin OCR, todo lo demás funciona; solo los PDFs que son imágenes quedan como "sin texto".

**Desde el código** (si preferís no usar el `.exe`): hace falta [Python 3.10 o superior](https://www.python.org/downloads/) con "Add python.exe to PATH" tildado. Después `pip install -r requirements.txt` y doble clic en `iniciar.bat`. Para generar el `.exe` propio: `construir_exe.bat`.

## Primera configuración

El organizador se abre en <http://localhost:5050>. La primera vez aparece un formulario:

| Campo | Para qué sirve |
|---|---|
| Nombre del estudio | Se muestra en el título y el pie. |
| Ciudad o jurisdicción | Solo informativo. |
| Tus apellidos | Evita confundir tu firma con el nombre de una causa. Separados por coma. |
| Carpeta base | Donde se ordenan los expedientes. Si no existe, se crea con `01_Expedientes`, `_INBOX` y `_SISTEMA`. |

Al guardar, el programa se reinicia solo. La configuración queda en `%APPDATA%\Organizador\config.json` y se puede cambiar después desde "Configuración", abajo a la izquierda. Si abrís el programa dos veces, la segunda solo te lleva a la ventana ya abierta.

## Primeros pasos

1. **Cartera → Agregar causas.** Cargá tus causas de una de estas formas:
   - *Una causa*: número `NNNN/AAAA` y, si querés, la carátula.
   - *Pegar una lista*: una causa por línea, con o sin carátula.
   - *Buscar en una carpeta*: indicá dónde tenés tus archivos y el programa detecta los números de expediente en los nombres de carpetas y archivos (o dentro del texto). Si tu estudio nombra los archivos de otra manera, en "Opciones" podés escribir un patrón propio.
2. **Tandas → Nueva simulación.** Elegí la carpeta a ordenar. Revisá la propuesta agrupada por destino, destildá lo que no quieras mover y corregí destinos.
3. **Aplicar.** Se mueve exactamente lo aprobado.
4. **Historial.** Si algo no es lo que esperabas, deshacé la tanda.

También podés arrastrar archivos a "Soltar archivos" en Tandas.

## Qué se guarda y dónde

Todo vive dentro de tu carpeta base:

- `01_Expedientes\` — una carpeta por causa.
- `_INBOX\` — lo que todavía no se pudo clasificar.
- `_SISTEMA\` — cartera, historial de movimientos y simulaciones.

## Límites que conviene conocer

- Detecta el número de expediente con el formato `NNNN/AAAA` (también `NNNN-AAAA` o `NNNN_AAAA`, años 1980 a 2035). Si tu jurisdicción numera distinto, usá el patrón propio.
- La clasificación de jurisprudencia y doctrina está pensada para fallos argentinos.
- Es una ayuda para ordenar: **antes de mover documentos importantes, hacé una copia de seguridad**.

## Variables de entorno (opcional)

| Variable | Efecto |
|---|---|
| `ORGANIZADOR_BASE` | Carpeta base, pisa a la configuración. |
| `ORGANIZADOR_APELLIDOS` | Apellidos propios, separados por coma. |
| `ORGANIZADOR_CONFIG` | Ruta alternativa del `config.json`. |

Para otro puerto: `Organizador.exe --port 5060`.
