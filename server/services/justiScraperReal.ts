import puppeteer, { Browser, Page } from "puppeteer";

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

export const JUSTI_URL = "https://pwa.jusmisiones.gov.ar/build/Panel";
const TIMEOUT = 30000;

/**
 * Scraper de Justi (PWA del STI del Poder Judicial de Misiones).
 * JUSTI_USER_DATA_DIR reutiliza un perfil de Chrome ya logueado, evitando repetir login/CAPTCHA.
 */
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

  /** Devuelve true si quedó logueado (o ya lo estaba por la sesión guardada). */
  private async login(page: Page, username: string, password: string): Promise<boolean> {
    await page.goto(JUSTI_URL, { waitUntil: "networkidle2", timeout: TIMEOUT });

    const passwordInput = await page.$('input[type="password"]');
    if (!passwordInput) return true;

    const userInput = await page.$('input[type="email"], input[type="text"], input:not([type])');
    if (!userInput) return false;

    await userInput.type(username);
    await passwordInput.type(password);

    const submit =
      (await page.$('button[type="submit"], input[type="submit"]')) ??
      (await page.$("button ::-p-text(Ingresar)")) ??
      (await page.$("button ::-p-text(Iniciar)")) ??
      (await page.$("button ::-p-text(Entrar)"));
    if (submit) {
      await submit.click();
    } else {
      await passwordInput.press("Enter");
    }

    try {
      await page.waitForFunction(() => !document.querySelector('input[type="password"]'), {
        timeout: TIMEOUT,
      });
      return true;
    } catch {
      return false;
    }
  }

  private capturarApi(page: Page, destino: RespuestaApiJusti[]): void {
    page.on("response", async response => {
      const type = response.request().resourceType();
      if (type !== "xhr" && type !== "fetch") return;
      if (!(response.headers()["content-type"] || "").includes("json")) return;
      try {
        destino.push({
          method: response.request().method(),
          url: response.url(),
          status: response.status(),
          body: await response.json(),
        });
      } catch {
        // cuerpo vacío o respuesta ya descartada
      }
    });
  }

  private async extraerNovedadesDom(page: Page): Promise<NovedadExpedienteJusti[]> {
    return page.evaluate(() => {
      const filas = Array.from(document.querySelectorAll("tbody tr, [role='row']"));
      return filas
        .map(fila => {
          const celdas = Array.from(fila.querySelectorAll("td, [role='gridcell'], [role='cell']")).map(
            c => c.textContent?.trim() || ""
          );
          if (celdas.length < 3) return null;
          const bg = window.getComputedStyle(fila as Element).backgroundColor;
          const estado = bg.includes("255, 255, 0") ? "amarillo" : bg.includes("255, 255, 255") ? "blanco" : "normal";
          return {
            numero: celdas[0],
            caratula: celdas[1],
            dependencia: celdas[2],
            ultimoMovimiento: celdas[3] || "",
            fechaMovimiento: celdas[4] || "",
            estado,
          };
        })
        .filter(Boolean) as any;
    });
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
    this.capturarApi(page, api);

    try {
      if (!(await this.login(page, username, password))) {
        throw new Error("Login fallido en Justi (credenciales, CAPTCHA o formulario no reconocido)");
      }

      await page.goto(JUSTI_URL, { waitUntil: "networkidle2", timeout: TIMEOUT });
      const novedades = await this.extraerNovedadesDom(page);

      // Las cédulas se mapearán desde `api` cuando se identifique el endpoint real.
      const cedulas: CedulaNotificacionJusti[] = [];

      return { novedades, cedulas, api, timestamp: new Date() };
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
