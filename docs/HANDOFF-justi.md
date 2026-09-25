# Traspaso: integración Justi → SIGED Gestión Legal

Rama: `claude/app-justi-connection-bkkbay`

## Objetivo

Traer automáticamente **novedades de expedientes** (y cédulas/notificaciones) desde **Justi**, la PWA del STI del Poder Judicial de Misiones (`https://pwa.jusmisiones.gov.ar/build/Panel`), hacia esta app, igual que ya se hace con SIGED.

## Qué se descartó

- **App Android en la red local**: el celular (192.168.1.10, Motorola) no expone puertos (nmap: todo cerrado). No hay API local.
- **Acceso desde la sesión en la nube**: el proxy bloquea `pwa.jusmisiones.gov.ar`. **Hay que seguir en local.**

## Estado actual

Listo y verificado (`pnpm check` sin errores, `pnpm test` 50/50):
- `server/services/justiScraperReal.ts`: un solo login, selectores válidos, reutiliza la sesión (`JUSTI_USER_DATA_DIR`) y captura todas las respuestas JSON de la API de Justi.
- `server/services/justiSchedulerReal.ts`: martes y viernes a las 8:00; se saltea la feria (enero, más los rangos de `JUSTI_FERIAS`); fechas dd/mm/aaaa; avisa al dueño cuando hay novedades.
- Routers tRPC `justiCredentials`, `justiScanReal` (`scan`, `getNovedades`, `getNotificaciones`, `marcarComoLeida`) y `justiScheduler`.
- Tablas `justi_credentials`, `justi_notificaciones` y `justi_novedades`. Las novedades no se duplican si el último movimiento no cambió.
- `scripts/justi-discover.ts` (`pnpm justi:discover`).

Pendiente, y requiere tu PC:
1. `pnpm install`, luego `pnpm justi:discover`. Se abre Chrome: te logueás y recorrés Novedades, Expedientes y Notificaciones, después cerrás. Queda `justi-api.json`, que está en `.gitignore` porque tiene datos personales.
2. Con ese archivo se mapean los endpoints reales a novedades y cédulas en `justiScraperReal.ts` (hoy las novedades salen del DOM y las cédulas vuelven vacías).
3. `pnpm db:push` contra la base local, para crear las tablas nuevas.

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
