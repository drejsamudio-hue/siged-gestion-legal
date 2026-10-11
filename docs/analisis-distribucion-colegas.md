# Análisis de la app para distribuir a colegas

Fecha del análisis: 11/10/2026 · Rama: `arena/17d8fce6-siged-gestion-legal` · Commit base: `13b46ec`

## Resumen ejecutivo

El repositorio contiene **dos productos distintos**, y su madurez para distribuir a colegas es muy diferente:

| Producto | Qué es | ¿Listo para distribuir? |
|---|---|---|
| **Organizador de expedientes** (`app/`, Python/Flask → `Organizador.exe`) | Herramienta local que ordena PDFs por causa. No usa internet (salvo OCR opcional). | **Sí.** Distribuible bajo AGPL-3.0 con `construir_exe.bat` (tests + exe + SHA-256 + zip con fuente). Pendiente solo probar/firmar el `.exe` en Windows. |
| **SIGED Gestión Legal** (`client/` + `server/`, Node/React/MySQL) | Gestión de expedientes + escritos + chatbot + escaneo automático del SIGED/Justi. | **No, todavía.** Está atada a la plataforma donde se desarrolló (login, almacenamiento, notificaciones) y guarda credenciales de sistemas judiciales. Requiere trabajo previo. |

**Verificación de salud ejecutada hoy:**

- Organizador: `pytest app/tests` → **196 tests pasando, 1 salteado** (3,7 s).
- SIGED web: `tsc --noEmit` sin errores · `vitest` → **57/57 tests pasando** (6 archivos).
- Código estable; el problema no es la calidad funcional sino los **siguientes ítems de distribución**.

---

## 1. Organizador de expedientes — el candidato a distribuir

### Qué recibe el colega hoy

1. Copia la carpeta con `Organizador.exe` y hace doble clic.
2. Se abre en `http://localhost:5050`; el asistente de primera configuración crea la carpeta base (`01_Expedientes`, `_INBOX`, `_SISTEMA`).
3. Carga su cartera de causas, simula tandas de ordenamiento, aprueba, y puede deshacer cada movimiento.

Documentación (README.md) ya escrita en español rioplatense para abogados no técnicos: instalación, primeros pasos, límites del detector de expedientes (`NNNN/AAAA`), variables de entorno. Es el mejor "manual de distribución" que hay en el repo.

### Puntos fuertes (esto se puede decir al distribuirla)

- **Privacidad real**: la API se ata a `localhost` y bloquea hosts que no sean `localhost/127.0.0.1` y orígenes cruzados (`_solo_local` en `app/dashboard.py`) — hay defensa explícita contra DNS rebinding. Ningún dato del estudio sale de la máquina.
- **Nunca borra ni pisa archivos**; cada movimiento queda en historial y es deshacible.
- Configuración y datos en `%APPDATA%\Organizador\` y en la carpeta base que elige el usuario; multiusuario seguro en la misma PC.
- La única descarga de internet (idioma OCR `spa.traineddata`) es **opcional**, viene de la fuente oficial de Tesseract, con **SHA-256 fijado**, parcial `.part` + renombrado atómico y solo por HTTPS (`app/ocr_setup.py`). Hay espejo propio vía `ORGANIZADOR_TESSDATA_URL`.
- Cobertura de tests sólida (196) sobre cartera, ingesta, cruce, dashboard, doctrina y OCR/legislación.

### Brechas a resolver antes de repartirlo

| # | Brecha | Impacto | Qué hacer |
|---|---|---|---|
| 1 | **Licencia de PyMuPDF (`fitz`) es AGPL-3.0 / comercial (Artifex)** — `app/extractor.py` lo usa para leer PDFs y se empaqueta dentro del `.exe`. | **Alto.** Distribuir el `.exe` a terceros (colegas de otros estudios) activa la copyleft AGPL: hay que entregar el código completo bajo AGPL (o comprar licencia comercial de Artifex). El `package.json` declara "MIT", lo cual no cubre esto. | ✅ **Resuelto 11/10/2026:** ruta (a) elegida — Organizador publicado bajo AGPL-3.0 (`app/LICENSE`), fuente incluida en cada release. |
| 2 | **`Organizador.exe` sin firma digital** → Windows SmartScreen muestra "Windows protegió su PC". | Medio. El README lo explica, pero asusta a colegas poco técnicos y parece software dudoso. | 🟡 **Parcial:** se publica SHA-256 del `.exe` para verificar integridad (README explica `certutil`). La firma digital requiere comprar certificado. |
| 3 | **No hay archivo LICENSE en la raíz** (solo `"license": "MIT"` en `package.json`, que aplica al paquete npm). | Medio (legal). | ✅ **Resuelto:** `LICENSE` (MIT, app web) + `app/LICENSE` (AGPL-3.0, Organizador) + `THIRD_PARTY_NOTICES.md`. |
| 4 | **`build/` de PyInstaller quedó versionado** (1,6 MB de intermedios: `base_library.zip`, `.toc`, `.pyc`) aunque `.gitignore` lo lista. | Bajo (higiene del repo). | ✅ **Resuelto:** fuera del versionado y del árbol de trabajo. |
| 5 | **`pytest` está en `requirements.txt` de producción** (se instala en la PC del usuario con `iniciar.bat`/`construir_exe.bat`). | Bajo. | ✅ **Resuelto:** `requirements.txt` solo runtime; `requirements-dev.txt` con pytest y pyinstaller. |
| 6 | **Sin auto-update ni mecanismo de versionado de releases.** | Medio. | 🟡 **Parcial:** archivo `VERSION` + `construir_exe.bat` arma el zip de release con SHA-256. Sin GitHub Actions (decisión del usuario). |
| 7 | **OCR: verificar en PC limpia.** El motor lo aporta PyMuPDF (`get_textpage_ocr`) y solo se descarga el idioma. | Bajo. | 🟡 **Validado en suite:** test OCR de punta a punta en verde con `spa.traineddata` oficial (SHA-256 verificado). Falta repetir la prueba en Windows con el `.exe`. |

### Checklist mínimo de release del Organizador

> **Estado 11/10/2026:** se resolvió todo lo resoluble desde el repo. Decisión tomada: **Organizador bajo AGPL-3.0** conservando PyMuPDF (y el OCR sin instalar nada). Queda solo lo que exige una PC con Windows.

1. ~~Resolver el punto de licencia~~ → Hecho: `app/LICENSE` (AGPL-3.0 completa), `LICENSE` (MIT para la app web), `THIRD_PARTY_NOTICES.md`, sección "Licencia" en el README y fuente incluida en cada zip de release.
2. Construir en Windows con `construir_exe.bat` — el script ahora instala `requirements-dev.txt`, **corre los tests** (si fallan, no arma nada), genera el `.exe`, calcula el SHA-256 (`Organizador.exe.sha256`) y arma `dist\Organizador-<versión>.zip` con exe + README + licencias + `Organizador-<versión>-fuente.zip` (cumplimiento AGPL automático).
3. Probar el `.exe` en PC limpia (único pendiente): primer arranque, configuración, movimiento y deshacer, OCR opcional, reinicio al guardar config. La suite (197 tests, incluido el OCR de punta a punta con `spa.traineddata` oficial verificado por SHA-256) corre en verde.
4. Firmar el `.exe` si hay certificado (opcional): mientras tanto, el SHA-256 publicado permite verificar integridad.
5. ~~Armar zip con licencias~~ → Lo hace el script, ver punto 2.
6. Publicar el zip como release (tag + notas). Sin GitHub Actions por decisión del usuario: se comparte el zip manualmente.

---

## 2. SIGED Gestión Legal — qué impide distribuirla hoy

Es una app web completa (dashboard, expedientes, generador de escritos, chatbot legal de Misiones, notas, escaneo SIGED/Justi con scheduler), con tests y TypeScript en orden. Pero para darle de tomar a un colega aparecen estos bloqueantes:

### B1. Dependencia total de la plataforma de desarrollo (bloqueante)

- **Login**: OAuth de Manus (`server/_core/oauth.ts`, `sdk.ts`, `useAuth.ts` con `manus-runtime-user-info`). Sin `OAUTH_SERVER_URL`, `VITE_APP_ID` y `JWT_SECRET` **nadie puede entrar**.
- **Almacenamiento de archivos**: proxy propio (`BUILT_IN_FORGE_API_URL/KEY`, `server/storage.ts`).
- **Notificaciones**: `notifyOwner` → `SendNotification` de la plataforma (`server/_core/notification.ts`).
- **LLM / mapas / imágenes**: helpers de plataforma (`llm.ts`, `map.ts`, `imageGeneration.ts`).

*Qué hace falta:* reemplazar auth (usuarios locales con contraseña, o Auth.js/Keycloak propio), apuntar storage a S3/local, y sustituir notificaciones por email SMTP o webhooks.

### B2. Seguridad de la configuración (bloqueante)

- `server/services/encryptionService.ts`: si falta `ENCRYPTION_KEY`, usa `"default-unsafe-key-change-in-production"` — **clave pública conocida** con la que se encriptan las credenciales de SIGED/Justi en MySQL.
- `docker-compose.yml` levanta MySQL 8.4 con **`MYSQL_ROOT_PASSWORD` vacío** (atado a `127.0.0.1`, pero insuficiente si la PC se comparte o se expone en red de estudio).
- **No hay `.env.example`** documentado: `DATABASE_URL`, `ENCRYPTION_KEY`, `JWT_SECRET`, `OWNER_OPEN_ID` hay que adivinarlos del código.

*Qué hace falta:* `.env.example` + generación de secretos en el instalador, negar arranque si `ENCRYPTION_KEY` es el default, contraseña real en MySQL.

### B3. Credenciales de sistemas judiciales y scraping (alto — decisión previa)

El sistema guarda (encriptadas) las credenciales de SIGED (`jusmisiones.gov.ar/siged`) y de Justi (SSO Keycloak `idm.jusmisiones.gov.ar`) de cada usuario, y con Puppeteer se loguea y extrae novedades, cédulas y despachos (`sigedScraperReal.ts`, `justiScraperReal.ts`, perfil de sesión en `.justi-profile`).

Antes de que **cada colega** ponga su matrícula y contraseña ahí, conviene definir:

- **Términos de uso del Poder Judicial**: el acceso automatizado vía navegador headless puede violar los términos del SIGED/Justi. Usar las credenciales propias de cada uno reduce el riesgo (cada quien accede a lo suyo), pero no lo elimina. Recomendable consultar al área de informática del STJ o, cuanto menos, dejarlo documentado y con opt-in explícito.
- **Datos personales (Ley 25.326)**: la base acumula carátulas, partes, notificaciones y credenciales. Informar a los usuarios qué se almacena y dónde; si el uso es profesional, evaluar el encuadre de datos de clientes.
- La sesión guardada de Justi (`.justi-profile`) contiene tokens: ya está en `.gitignore`, pero debe excluirse también de cualquier paquete que se distribuya.

### B4. Funcionalidades declaradas que no están de punta a punta

- **"Alertas por email"**: el TODO las tilda como hechas en la sección 11, pero no hay transporte SMTP/nodemailer en el código. Solo se guarda un `notificationEmail` y se formatean reportes HTML/texto "para email" (`reportGenerator.ts`); el aviso real llega por notificación de plataforma. Hay que implementar el envío o corregir la documentación.
- **Exportación PDF/DOCX de escritos** y **búsqueda full-text**: pendientes según `todo.md`.

### B5. Operación para un colega no técnico

Requiere Node 20+, pnpm, Docker/MySQL, Chromium para Puppeteer y una consola. No hay Dockerfile de la app, ni instalador, ni manual de usuario (el README solo cubre el Organizador).

---

## 3. Plan recomendado

### Ruta A — Distribuir ya (1–2 días de trabajo)

Distribuir **solo el Organizador.exe** a los colegas, que es lo que hoy está diseñado para eso:

1. Definir licencia (recomendado si no se quiere abrir el código: licencia comercial de Artifex; si se abre: AGPL-3.0 completo).
2. Armar el release (checklist de la sección 1).
3. Acompañar con un mensaje tipo "guía de 1 página": qué hace, qué no hace (no consulta internet, no reemplaza la copia de seguridad), y cómo instalar OCR.

### Ruta B — SIGED para el estudio (1–2 semanas de trabajo)

Si la meta es que los colegas usen SIGED Gestión Legal:

1. **Auth propia** (usuarios locales o SSO del estudio) y secretos obligatorios (`ENCRYPTION_KEY`, `JWT_SECRET`) sin defaults.
2. MySQL con contraseña + `.env.example` + `docker-compose` endurecido; Dockerfile de la app.
3. Decisión documentada sobre scraping SIGED/Justi (opt-in por usuario, aviso de riesgos).
4. Email SMTP real para alertas (o dejar de prometerlo en docs).
5. Manual de usuario breve + guía de instalación asistida.
6. Ideal: publicarla como servicio interno del estudio (una instancia, acceso por HTTPS en LAN/VPN) en vez de instalarla en cada PC.

### Higiene del repo (cualquiera de las rutas)

- Quitar `build/` del versionado.
- Mover `pytest` a dependencias de desarrollo.
- Archivo `LICENSE` (y `THIRD_PARTY_NOTICES` con las licencias de dependencias empaquetadas).
- Alinear `todo.md` con la realidad (las "alertas por email" no están implementadas).

---

## Anexo: inventario rápido del repo

- `app/` — Organizador (Python 3.10+: `dashboard.py` Flask 5050, `ingesta.py` clasificación, `cartera*.py`, `extractor.py` PDF/DOCX, `ocr_setup.py`, tests en `app/tests/`).
- `client/` + `server/` — SIGED (React 19 + Vite + tRPC + Drizzle/MySQL 8; routers de expedientes/escritos/chatbot/credenciales SIGED y Just; schedulers con node-cron — martes y viernes 8:00, se saltea feria).
- `drizzle/` — 5 migraciones MySQL.
- `docs/HANDOFF-justi.md` — traspaso técnico de la integración Justi (API relevada, endpoints, pendientes).
- `Organizador.spec`, `construir_exe.bat`, `iniciar.bat` — empaquetado/ejecución del Organizador.
- Variables de entorno del Organizador: `ORGANIZADOR_BASE`, `ORGANIZADOR_APELLIDOS`, `ORGANIZADOR_CONFIG`, `ORGANIZADOR_TESSDATA_URL`, `TESSDATA_PREFIX`, `ORGANIZADOR_CORPUS`, `ORGANIZADOR_JUSTI_DIR`.
- Variables de entorno SIGED: `DATABASE_URL`, `ENCRYPTION_KEY`, `JWT_SECRET`, `VITE_APP_ID`, `OAUTH_SERVER_URL`, `OWNER_OPEN_ID`, `BUILT_IN_FORGE_API_URL/KEY`, `PORT`, `JUSTI_USER_DATA_DIR`, `JUSTI_HEADLESS`, `JUSTI_FERIAS`.
