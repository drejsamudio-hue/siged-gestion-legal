# Traspaso: integración Justi → SIGED Gestión Legal

Rama: `claude/app-justi-connection-bkkbay`

## Objetivo

Traer automáticamente **novedades de expedientes** (y cédulas/notificaciones) desde **Justi**, la PWA del STI del Poder Judicial de Misiones (`https://pwa.jusmisiones.gov.ar/build/Panel`), hacia esta app, igual que ya se hace con SIGED.

## Qué se descartó

- **App Android en la red local**: el celular (192.168.1.10, Motorola) no expone puertos (nmap: todo cerrado). No hay API local.
- **Acceso desde la sesión en la nube**: el proxy bloquea `pwa.jusmisiones.gov.ar`. **Hay que seguir en local.**

## Qué quedó hecho (borrador, SIN probar)

| Archivo | Estado |
|---|---|
| `server/services/justiScraperReal.ts` | Scraper Puppeteer. Selectores **inventados**: nunca se vio el sitio real. |
| `server/services/justiSchedulerReal.ts` | **Roto**: importa módulos que no existen (`../_core/schema`, `db` y `sendNotificationEmail`). Hay que reescribirlo copiando `sigedSchedulerReal.ts`. |
| `server/routers.ts` | Routers `justiCredentials`, `justiScanReal` y `justiScheduler`. |
| `server/db.ts` | Funciones CRUD de Justi (credenciales, notificaciones, novedades). |
| `drizzle/schema.ts` | Tablas `justi_credentials`, `justi_notificaciones` y `justi_novedades` (MySQL). |

### Problemas conocidos a corregir
1. `button:contains(...)` no es un selector CSS válido: Puppeteer tira error. Hay que usar `::-p-text(...)` o XPath.
2. `escaneoCompleto` hace **dos logins en paralelo** (novedades + cédulas). Conviene un solo login y una sola página.
3. El scheduler tiene mal el calendario de feria/feriados: ahí dice julio completo, y la feria de invierno dura unas 2 semanas. Conviene usar la lógica que ya tiene `sigedSchedulerReal.ts` o el skill `plazos-procesales`.
4. `userId` figura como `string` en el scheduler, pero en la base es `number`.
5. Los routers usan `require()` en un proyecto ESM (`"type": "module"`). Pasa lo mismo con SIGED: hay que revisarlo y cambiarlo por `await import()`.

## Enfoque recomendado (antes de tocar selectores)

Justi es una SPA: seguramente consume una API JSON propia. **Interceptar esa API es mucho más robusto que parsear el HTML.**

1. Correr Puppeteer con `headless: false` y loguearse a mano (así se evita el CAPTCHA o el 2FA si los hay).
2. Registrar las respuestas XHR/fetch:
   ```ts
   page.on("response", async r => {
     const ct = r.headers()["content-type"] || "";
     if (ct.includes("json")) console.log(r.request().method(), r.url(), (await r.text()).slice(0, 500));
   });
   ```
3. Identificar los endpoints de novedades y notificaciones y el mecanismo de auth (token en `localStorage`, cookie o `Authorization: Bearer`).
4. Reemplazar el scraping de DOM por llamadas directas a esa API, usando el token obtenido con el login. Si el login no es automatizable, usar `userDataDir` para reutilizar la sesión.

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
