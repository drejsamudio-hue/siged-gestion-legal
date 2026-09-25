# Traspaso: integración Justi → SIGED Gestión Legal

Rama: `claude/app-justi-connection-bkkbay`

## Objetivo

Traer automáticamente **novedades de expedientes** (y cédulas/notificaciones) desde **Justi**, la PWA del STI del Poder Judicial de Misiones (`https://pwa.jusmisiones.gov.ar/build/Panel`), hacia esta app, igual que ya se hace con SIGED.

## Qué se descartó

- **App Android en la red local**: el celular (192.168.1.10, Motorola) no expone puertos (nmap: todo cerrado). No hay API local.
- **Acceso desde la sesión en la nube**: el proxy bloquea `pwa.jusmisiones.gov.ar`. **Hay que seguir en local.**

## Estado actual

Base hecha en la nube (vigente, ampliada abajo):
- `server/services/justiSchedulerReal.ts`: martes y viernes a las 8:00; se saltea la feria (enero, más los rangos de `JUSTI_FERIAS`); fechas dd/mm/aaaa y aaaa-mm-dd; avisa al dueño cuando hay novedades nuevas.
- Routers tRPC `justiCredentials`, `justiScanReal` (`scan`, `getNovedades`, `getNotificaciones`, `marcarComoLeida`) y `justiScheduler`.
- Tablas `justi_credentials`, `justi_notificaciones` y `justi_novedades`. Las novedades no se duplican si el último movimiento no cambió.
- `scripts/justi-discover.ts` (`pnpm justi:discover`).

### API real de Justi (relevada en local el 25/09/2026)

- Login: SSO Keycloak (`idm.jusmisiones.gov.ar`, realm `jusmisiones`, cliente `sso-oid`). La PWA deja `token`, `matricula`, `fullName` y `mail` en `sessionStorage`.
- `GET /api/apitoken/login/:mail` → `[{ abogado, email, matricula }]`
- `GET /api/apitoken/notificaciones/:mail` → `[{ cantidad }]` (solo contador, últimos 7 días)
- `GET /api/apitoken/notificaciones-detalles/:mail` → `numero_expediente, caratula, fecha_envio_notificacion, dependencia, remitente, documento_adjunto`
- `GET /api/apitoken/despachos/:mail` → agrupado por `fecha` con `items: [{ id_despacho, nro_expediente, dependencia_nombre, secretaria_nombre, descripcion_tipo_despacho, designacion, sale_con }]`
- El mail va sin codificar en la URL (codificado, el backend responde "El usuario y el Token no son correspondientes").
- Justi **no** expone movimientos de expediente en general: solo despachos del usuario vinculado y notificaciones SIGED de 7 días.

### Hecho en local (25/09/2026)

- `justiScraperReal.ts` usa la API: abre `Despachos/:mail` y `NotificacionesSiged/:mail` con el perfil logueado y lee el JSON que recibe la PWA (no manipula el token). Despachos → `justi_novedades`; notificaciones detalladas → `justi_notificaciones`.
- Login Keycloak (`#username`, `#password`, `#kc-login`) si el perfil no tiene sesión.
- `parseFecha` toma `aaaa-mm-dd` como fecha local (antes corría al día anterior).
- Cédulas deduplicadas por título + fecha; el aviso cuenta solo registros nuevos.
- `routers.ts`: se reemplazaron los `require()` de SIGED por imports estáticos (fallaban en ESM).
- `pnpm check` sin errores; `pnpm test` 57/57.

### Base de datos — usar Docker

No hay motor de base corriendo en tu PC hoy. La forma más fácil: **Docker Desktop** + `docker-compose.yml`.

1. **Instala Docker Desktop** desde https://www.docker.com/products/docker-desktop (15 min, reinicia).
2. En la carpeta del proyecto:
   ```powershell
   docker-compose up -d
   ```
   Eso levanta MySQL 8.4 sin contraseña, escuchando en localhost:3306.
3. `pnpm db:push` crea las tablas.
4. Para parar: `docker-compose down`.

Si no querés Docker, la alternativa es instalar MySQL 8 manualmente en Windows (sin Docker): el `.env` ya está listo, solo hay que levantar el servicio.

### Pendiente

1. **Prueba end-to-end del scraper** una vez que haya base: 
   - `pnpm justi:discover` una sola vez (abre Chrome, te logueás, cierra) → guarda sesión en `.justi-profile`.
   - Después `pnpm scan` desde la app.
2. `notificaciones-detalles` no se pudo ver con datos (0 notificaciones esta semana); el mapeo sale del código de la PWA. Validar cuando haya una.

Variables de entorno:
- `JUSTI_USER_DATA_DIR=.justi-profile`: reutiliza la sesión guardada por el script de descubrimiento.
- `JUSTI_HEADLESS=false`: muestra el navegador mientras corre.
- `JUSTI_FERIAS=2026-07-13:2026-07-24`: rangos de feria de invierno según la acordada del STJ. Verificar las fechas.

## PostgreSQL local: ¿conviene?

El proyecto hoy es **MySQL** (`drizzle-orm/mysql2` y `dialect: "mysql"`). Para usar Postgres:

| Opción | Ventaja | Desventaja |
|---|---|---|
| Levantar MySQL con Docker (`docker run -p 3306:3306 -e MYSQL_ROOT_PASSWORD=... mysql:8`) | Cero cambios de código | Otro motor más corriendo |
| Migrar a Postgres | Usás lo que ya tenés | Hay que convertir 14 tablas y 12 enums, además de unos 15 usos de `onUpdateNow`, `insertId` y `onDuplicateKeyUpdate` |

Si migrás, los cambios son:
- `drizzle.config.ts`: `dialect: "postgresql"`
- `drizzle/schema.ts`: `mysqlTable` → `pgTable`, `int().autoincrement()` → `serial()`, `mysqlEnum` → `pgEnum`, `onUpdateNow()` → `.$onUpdate(() => new Date())`
- `server/db.ts`: `drizzle-orm/mysql2` → `drizzle-orm/node-postgres` (`pnpm add pg @types/pg`, `pnpm remove mysql2`)
- `onDuplicateKeyUpdate` → `onConflictDoUpdate({ target, set })`; `insertId` → `.returning({ id })`
- Borrar las migraciones MySQL viejas de `drizzle/` y regenerarlas con `pnpm db:push`

**Recomendación:** primero hacer andar Justi con Docker/MySQL. La migración a Postgres conviene como tarea separada, en su propio commit.

## Prompt para seguir en Claude Code (local)

```
Estoy en la rama claude/app-justi-connection-bkkbay. Leé docs/HANDOFF-justi.md.
1) Instalá dependencias (pnpm install) y corré pnpm check y pnpm test.
2) Creá un script scripts/justi-discover.ts que abra Puppeteer headful en
   https://pwa.jusmisiones.gov.ar/build/Panel, me deje loguearme a mano y
   registre todas las respuestas JSON (método, URL y cuerpo truncado) en un archivo.
3) Con esos endpoints, reescribí justiScraperReal.ts para usar la API en vez del DOM,
   y arreglá justiSchedulerReal.ts siguiendo el patrón de sigedSchedulerReal.ts.
4) Después evaluamos migrar a PostgreSQL local según la sección del handoff.
```
