import puppeteer from "puppeteer";
import { writeFileSync } from "node:fs";
import { JUSTI_URL } from "../server/services/justiScraperReal";

const SALIDA = "justi-api.json";
const PERFIL = process.env.JUSTI_USER_DATA_DIR || ".justi-profile";

type Registro = { method: string; url: string; status: number; authHeaders: string[]; body: unknown };
const registros: Registro[] = [];

const guardar = () => writeFileSync(SALIDA, JSON.stringify(registros, null, 2));

const browser = await puppeteer.launch({ headless: false, userDataDir: PERFIL, defaultViewport: null });
const [page] = await browser.pages();

page.on("response", async response => {
  const req = response.request();
  if (!["xhr", "fetch"].includes(req.resourceType())) return;
  if (!(response.headers()["content-type"] || "").includes("json")) return;
  let body: unknown;
  try {
    body = await response.json();
  } catch {
    return;
  }
  // Solo nombres de headers de auth, nunca sus valores.
  const authHeaders = Object.keys(req.headers()).filter(h => /auth|token|cookie/i.test(h));
  registros.push({ method: req.method(), url: response.url(), status: response.status(), authHeaders, body });
  console.log(`${req.method()} ${response.status()} ${response.url()}`);
  guardar();
});

await page.goto(JUSTI_URL, { waitUntil: "networkidle2" });
console.log(`
Logueate en la ventana si hace falta y recorré Panel, Novedades, Expedientes y Notificaciones.
Todo se guarda en ${SALIDA}. Cerrá la ventana del navegador para terminar.
La sesión queda en ${PERFIL}/ (usala con JUSTI_USER_DATA_DIR para el scraper).
`);

browser.on("disconnected", () => {
  guardar();
  console.log(`Listo: ${registros.length} respuestas en ${SALIDA}`);
  process.exit(0);
});
