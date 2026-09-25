import puppeteer, { Browser, Page } from "puppeteer";

/**
 * Integración con Justi (PWA del STI del Poder Judicial de Misiones).
 *
 * Mapa real de la app (relevado el 25/09/2026):
 * - Login: SSO Keycloak en idm.jusmisiones.gov.ar (realm "jusmisiones", cliente "sso-oid").
 * - Tras el login, la PWA guarda en sessionStorage: token, matricula, fullName y mail.
 * - GET /api/apitoken/login/:mail                   → [{ abogado, email, matricula }]
 * - GET /api/apitoken/notificaciones/:mail          → [{ cantidad }] (notificados últimos 7 días)
 * - GET /api/apitoken/notificaciones-detalles/:mail → numero_expediente, caratula,
 *       fecha_envio_notificacion, dependencia, remitente, documento_adjunto
 * - GET /api/apitoken/despachos/:mail               → agrupado por fecha: { fecha, items: [
 *       { id_despacho, nro_expediente, dependencia_nombre, secretaria_nombre,
 *         descripcion_tipo_despacho, designacion (carátula), sale_con } ] }
 *
 * El scraper no maneja el token: abre las pantallas de la propia PWA con un perfil de Chrome
 * logueado y lee las respuestas JSON que la app recibe.
 */

export interface NovedadExpedienteJusti {
  numero: string;
  caratula: string;
  dependencia: string;
  ultimoMovimiento: string;
  fechaMovimiento: string;
  estado: "amarillo" | "blanco" | "normal";
}

export interface CedulaNotificacionJusti {
  tipo: "cédula" | "despacho" | "otro";
  titulo: string;
  contenido: string;
  fecha: string;
  expediente?: string;
}

export interface RespuestaApiJusti {
  method: string;
  url: string;
  status: number;
  body: unknown;
}

export const JUSTI_BASE = "https://pwa.jusmisiones.gov.ar/build";
export const JUSTI_URL = `${JUSTI_BASE}/Panel`;
const TIMEOUT = 30000;

type Obj = Record<string, unknown>;
const str = (v: unknown): string => (v === null || v === undefined ? "" : String(v).trim());

/** La API a veces envuelve la lista en { data }; se acepta array plano u objeto con data. */
function comoLista(body: unknown): Obj[] {
  if (Array.isArray(body)) return body as Obj[];
  if (body && typeof body === "object") {
    const data = (body as Obj).data;
    if (Array.isArray(data)) return data as Obj[];
    if (data && typeof data === "object") return Object.values(data) as Obj[];
  }
  return [];
}

/** Despachos → novedades de expediente (un registro por despacho). */
export function mapearDespachos(body: unknown): NovedadExpedienteJusti[] {
  const salida: NovedadExpedienteJusti[] = [];
  for (const grupo of comoLista(body)) {
    const items = Array.isArray(grupo.items) ? (grupo.items as Obj[]) : [grupo];
    for (const d of items) {
      const numero = str(d.nro_expediente);
      if (!numero) continue;
      const fecha = str(d.fecha ?? grupo.fecha);
      const tipo = str(d.descripcion_tipo_despacho);
      const saleCon = str(d.sale_con);
      const id = str(d.id_despacho);
      salida.push({
        numero,
        caratula: str(d.designacion),
        dependencia: [str(d.dependencia_nombre), str(d.secretaria_nombre)].filter(Boolean).join(" - "),
        // Incluye fecha e id para que cada despacho nuevo cuente como movimiento distinto.
        ultimoMovimiento: [fecha, tipo && `Despacho ${tipo}`, saleCon && `sale con ${saleCon}`, id && `#${id}`]
          .filter(Boolean)
          .join(" · "),
        fechaMovimiento: fecha,
        estado: "normal",
      });
    }
  }
  return salida;
}

/** Notificaciones SIGED detalladas → cédulas. */
export function mapearNotificaciones(body: unknown): CedulaNotificacionJusti[] {
  return comoLista(body)
    .filter(n => str(n.numero_expediente) || str(n.caratula))
    .map(n => {
      const expediente = str(n.numero_expediente);
      return {
        tipo: "cédula" as const,
        titulo: [expediente && `Expte. ${expediente}`, str(n.caratula)].filter(Boolean).join(" - "),
        contenido: [
          str(n.dependencia) && `Dependencia: ${str(n.dependencia)}`,
          str(n.remitente) && `Remitente: ${str(n.remitente)}`,
          str(n.documento_adjunto) && `Documento: ${str(n.documento_adjunto)}`,
        ]
          .filter(Boolean)
          .join("\n"),
        fecha: str(n.fecha_envio_notificacion),
        expediente: expediente || undefined,
      };
    });
}

export class JustiScraperReal {
  private browser: Browser | null = null;

  async initBrowser(): Promise<void> {
    if (!this.browser) {
      this.browser = await puppeteer.launch({
        headless: process.env.JUSTI_HEADLESS !== "false",
        userDataDir: process.env.JUSTI_USER_DATA_DIR || undefined,
        args: ["--no-sandbox", "--disable-setuid-sandbox"],
      });
    }
  }

  async closeBrowser(): Promise<void> {
    if (this.browser) {
      await this.browser.close();
      this.browser = null;
    }
  }

  /** Espera a que la PWA tenga sesión (mail en sessionStorage); si aparece el login de Keycloak, lo completa. */
  private async asegurarSesion(page: Page, username: string, password: string): Promise<string> {
    await page.goto(JUSTI_URL, { waitUntil: "networkidle2", timeout: TIMEOUT });

    const mailSesion = () => page.evaluate(() => sessionStorage.getItem("mail"));
    let mail = await mailSesion().catch(() => null);
    if (mail) return mail;

    // Keycloak: #username / #password / #kc-login
    const user = await page.$("#username, input[name='username'], input[type='email']");
    const pass = await page.$("#password, input[type='password']");
    if (!user || !pass) {
      throw new Error(
        "Justi no muestra sesión ni formulario de login. Corré `pnpm justi:discover`, logueate a mano y usá JUSTI_USER_DATA_DIR."
      );
    }
    await user.type(username);
    await pass.type(password);
    const submit = await page.$("#kc-login, button[type='submit'], input[type='submit']");
    await Promise.all([
      page.waitForNavigation({ waitUntil: "networkidle2", timeout: TIMEOUT }).catch(() => undefined),
      submit ? submit.click() : pass.press("Enter"),
    ]);

    try {
      await page.waitForFunction(() => !!sessionStorage.getItem("mail"), { timeout: TIMEOUT });
    } catch {
      throw new Error("Login fallido en Justi (credenciales, doble factor o CAPTCHA)");
    }
    mail = await mailSesion();
    if (!mail) throw new Error("Login en Justi sin mail de sesión");
    return mail;
  }

  /** Abre una pantalla de la PWA y devuelve el JSON del endpoint de la API que esa pantalla consulta. */
  private async leerPantalla(page: Page, ruta: string, endpoint: string, api: RespuestaApiJusti[]): Promise<unknown> {
    const respuesta = page
      .waitForResponse(r => r.url().includes(`/api/apitoken/${endpoint}/`) && r.request().method() === "GET", {
        timeout: TIMEOUT,
      })
      .catch(() => null);
    await page.goto(`${JUSTI_BASE}/${ruta}`, { waitUntil: "networkidle2", timeout: TIMEOUT });
    const r = await respuesta;
    if (!r) return null;
    let body: unknown = null;
    try {
      body = await r.json();
    } catch {
      return null;
    }
    api.push({ method: "GET", url: r.url(), status: r.status(), body });
    if (r.status() >= 400 || (body && typeof body === "object" && "error" in (body as Obj))) {
      throw new Error(`Justi ${endpoint}: ${str((body as Obj)?.error) || `HTTP ${r.status()}`}`);
    }
    return body;
  }

  async escaneoCompleto(
    username: string,
    password: string
  ): Promise<{
    novedades: NovedadExpedienteJusti[];
    cedulas: CedulaNotificacionJusti[];
    api: RespuestaApiJusti[];
    timestamp: Date;
  }> {
    await this.initBrowser();
    const page = await this.browser!.newPage();
    const api: RespuestaApiJusti[] = [];

    try {
      const mail = await this.asegurarSesion(page, username, password);

      const despachos = await this.leerPantalla(page, `Despachos/${mail}`, "despachos", api);
      const notificaciones = await this.leerPantalla(
        page,
        `NotificacionesSiged/${mail}`,
        "notificaciones-detalles",
        api
      );

      return {
        novedades: mapearDespachos(despachos),
        cedulas: mapearNotificaciones(notificaciones),
        api,
        timestamp: new Date(),
      };
    } finally {
      await page.close();
      await this.closeBrowser();
    }
  }
}

let scraperInstance: JustiScraperReal | null = null;

export function getJustiScraper(): JustiScraperReal {
  if (!scraperInstance) {
    scraperInstance = new JustiScraperReal();
  }
  return scraperInstance;
}
