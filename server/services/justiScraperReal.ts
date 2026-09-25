import puppeteer, { Browser, Page } from "puppeteer";
import { decryptText } from "./encryptionService";

interface NovedadExpedienteJusti {
  numero: string;
  caratula: string;
  dependencia: string;
  ultimoMovimiento: string;
  fechaMovimiento: string;
  estado: "amarillo" | "blanco" | "normal";
  fuente: "justi";
}

interface CedulaNotificacionJusti {
  tipo: "cédula" | "despacho" | "otro";
  titulo: string;
  contenido: string;
  fecha: string;
  expediente?: string;
  fuente: "justi";
}

/**
 * Servicio de scraping real de Justi usando Puppeteer
 * Justi es la PWA del STI del Poder Judicial de Misiones
 */
export class JustiScraperReal {
  private browser: Browser | null = null;
  private readonly JUSTI_URL = "https://pwa.jusmisiones.gov.ar/build/Panel";
  private readonly TIMEOUT = 30000; // 30 segundos

  /**
   * Inicia el navegador
   */
  async initBrowser(): Promise<void> {
    if (!this.browser) {
      this.browser = await puppeteer.launch({
        headless: true,
        args: ["--no-sandbox", "--disable-setuid-sandbox"],
      });
    }
  }

  /**
   * Cierra el navegador
   */
  async closeBrowser(): Promise<void> {
    if (this.browser) {
      await this.browser.close();
      this.browser = null;
    }
  }

  /**
   * Realiza login en Justi
   */
  private async login(
    page: Page,
    username: string,
    password: string
  ): Promise<boolean> {
    try {
      await page.goto(this.JUSTI_URL, {
        waitUntil: "networkidle2",
        timeout: this.TIMEOUT,
      });

      // Esperar a que aparezca el formulario de login
      // Justi es una PWA, así que puede tener diferentes selectores
      const loginSelectors = [
        'input[type="email"]',
        'input[type="text"]',
        'input[name="usuario"]',
        'input[placeholder*="usuario"]',
        'input[placeholder*="correo"]',
      ];

      let loginFound = false;
      for (const selector of loginSelectors) {
        if (await page.$(selector)) {
          await page.type(selector, username);
          loginFound = true;
          break;
        }
      }

      if (!loginFound) {
        console.log("Selector de login no encontrado en Justi");
        // Intentar con evaluación de página directa
        await page.evaluate((user: string) => {
          const inputs = document.querySelectorAll("input[type='text'], input[type='email']");
          if (inputs.length > 0) {
            (inputs[0] as HTMLInputElement).value = user;
            inputs[0].dispatchEvent(new Event("input", { bubbles: true }));
          }
        }, username);
      }

      // Buscar y rellenar campo de contraseña
      const passwordSelectors = [
        'input[type="password"]',
        'input[name="clave"]',
        'input[name="password"]',
        'input[placeholder*="contraseña"]',
        'input[placeholder*="clave"]',
      ];

      let passwordFound = false;
      for (const selector of passwordSelectors) {
        if (await page.$(selector)) {
          await page.type(selector, password);
          passwordFound = true;
          break;
        }
      }

      if (!passwordFound) {
        console.log("Selector de contraseña no encontrado en Justi");
        await page.evaluate((pass: string) => {
          const inputs = document.querySelectorAll("input[type='password']");
          if (inputs.length > 0) {
            (inputs[0] as HTMLInputElement).value = pass;
            inputs[0].dispatchEvent(new Event("input", { bubbles: true }));
          }
        }, password);
      }

      // Buscar y hacer click en el botón de login
      const submitSelectors = [
        'button[type="submit"]',
        'button:contains("Ingresar")',
        'button:contains("Entrar")',
        'button:contains("Login")',
        'button[class*="login"]',
        'button[class*="submit"]',
      ];

      let submitFound = false;
      for (const selector of submitSelectors) {
        if (await page.$(selector)) {
          await page.click(selector);
          submitFound = true;
          break;
        }
      }

      if (!submitFound) {
        console.log("Botón de envío no encontrado, intentando con evaluación");
        await page.evaluate(() => {
          const buttons = Array.from(document.querySelectorAll("button"));
          const submitButton = buttons.find(
            (btn) =>
              btn.textContent?.toLowerCase().includes("ingresar") ||
              btn.textContent?.toLowerCase().includes("entrar") ||
              btn.textContent?.toLowerCase().includes("login")
          );
          if (submitButton) {
            submitButton.click();
          }
        });
      }

      // Esperar a que cargue el panel
      await page.waitForNavigation({
        waitUntil: "networkidle2",
        timeout: this.TIMEOUT,
      }).catch(() => {
        console.log("Navegación completada (sin espera adicional)");
      });

      return true;
    } catch (error) {
      console.error("Error durante login en Justi:", error);
      return false;
    }
  }

  /**
   * Extrae las novedades de expedientes del panel de Justi
   */
  async extraerNovedades(
    username: string,
    passwordEncrypted: string
  ): Promise<NovedadExpedienteJusti[]> {
    await this.initBrowser();
    const page = await this.browser!.newPage();

    try {
      // Desencriptar contraseña
      const password = decryptText(passwordEncrypted);

      // Realizar login
      const loginExitoso = await this.login(page, username, password);
      if (!loginExitoso) {
        throw new Error("Login fallido en Justi");
      }

      // Esperar a que cargue el contenido del panel
      await page.waitForSelector("table, [role='table'], [class*='expediente'], [class*='novedad']", {
        timeout: 10000,
      }).catch(() => {
        console.log("Contenido de expedientes cargado");
      });

      // Extraer datos de expedientes
      const novedades = await page.evaluate(() => {
        const expedientes: NovedadExpedienteJusti[] = [];

        // Buscar filas de expedientes en diferentes posibles estructuras
        const rows = document.querySelectorAll(
          "tr[data-expediente], tbody tr, [class*='expediente'] [class*='row'], [data-test*='expediente']"
        );

        rows.forEach((row) => {
          const cells = row.querySelectorAll("td, [role='gridcell'], [class*='cell']");
          if (cells.length >= 3) {
            const bgColor = window.getComputedStyle(row).backgroundColor;
            let estado: "amarillo" | "blanco" | "normal" = "normal";

            // Detectar color de fondo
            if (bgColor.includes("255, 255, 0") || bgColor.includes("ffff00")) {
              estado = "amarillo";
            } else if (bgColor.includes("255, 255, 255") || bgColor.includes("ffffff")) {
              estado = "blanco";
            }

            expedientes.push({
              numero: cells[0]?.textContent?.trim() || "",
              caratula: cells[1]?.textContent?.trim() || "",
              dependencia: cells[2]?.textContent?.trim() || "",
              ultimoMovimiento: cells[3]?.textContent?.trim() || "",
              fechaMovimiento: cells[4]?.textContent?.trim() || "",
              estado,
              fuente: "justi",
            });
          }
        });

        return expedientes;
      });

      return novedades;
    } catch (error) {
      console.error("Error extrayendo novedades de Justi:", error);
      throw error;
    } finally {
      await page.close();
    }
  }

  /**
   * Extrae las cédulas y notificaciones del panel de Justi
   */
  async extraerCedulas(
    username: string,
    passwordEncrypted: string
  ): Promise<CedulaNotificacionJusti[]> {
    await this.initBrowser();
    const page = await this.browser!.newPage();

    try {
      // Desencriptar contraseña
      const password = decryptText(passwordEncrypted);

      // Realizar login
      const loginExitoso = await this.login(page, username, password);
      if (!loginExitoso) {
        throw new Error("Login fallido en Justi");
      }

      // Buscar la sección de cédulas/notificaciones
      const cedularSelectors = [
        "[class*='cedula']",
        "[class*='notificacion']",
        "[class*='notification']",
        "a[href*='cedula']",
        "button:contains('Cédulas')",
      ];

      for (const selector of cedularSelectors) {
        if (await page.$(selector)) {
          try {
            await page.click(selector);
            await page.waitForNavigation({ waitUntil: "networkidle2", timeout: 5000 }).catch(() => {});
            break;
          } catch (e) {
            console.log(`Selector ${selector} no funcionó`);
          }
        }
      }

      // Esperar a que cargue el contenido de cédulas
      await page.waitForSelector("table, [role='table'], [class*='cedula'], [class*='notificacion']", {
        timeout: 10000,
      }).catch(() => {
        console.log("Contenido de cédulas cargado");
      });

      // Extraer cédulas y despachos
      const cedulas = await page.evaluate(() => {
        const notificaciones: CedulaNotificacionJusti[] = [];

        // Buscar filas de cédulas
        const rows = document.querySelectorAll(
          "tr[data-cedula], tbody tr, [class*='cedula'] [class*='row'], [data-test*='cedula']"
        );

        rows.forEach((row) => {
          const cells = row.querySelectorAll("td, [role='gridcell'], [class*='cell']");
          if (cells.length >= 2) {
            const tipo = cells[0]?.textContent?.toLowerCase().includes("cédula")
              ? "cédula"
              : "despacho";

            notificaciones.push({
              tipo,
              titulo: cells[1]?.textContent?.trim() || "",
              contenido: cells[2]?.textContent?.trim() || "",
              fecha: cells[3]?.textContent?.trim() || new Date().toISOString(),
              expediente: cells[4]?.textContent?.trim() || undefined,
              fuente: "justi",
            });
          }
        });

        return notificaciones;
      });

      return cedulas;
    } catch (error) {
      console.error("Error extrayendo cédulas de Justi:", error);
      throw error;
    } finally {
      await page.close();
    }
  }

  /**
   * Realiza un escaneo completo de Justi
   */
  async escaneoCompleto(
    username: string,
    passwordEncrypted: string
  ): Promise<{
    novedades: NovedadExpedienteJusti[];
    cedulas: CedulaNotificacionJusti[];
    timestamp: Date;
  }> {
    try {
      const [novedades, cedulas] = await Promise.all([
        this.extraerNovedades(username, passwordEncrypted),
        this.extraerCedulas(username, passwordEncrypted),
      ]);

      return {
        novedades,
        cedulas,
        timestamp: new Date(),
      };
    } finally {
      await this.closeBrowser();
    }
  }
}

// Crear instancia singleton
let scraperInstance: JustiScraperReal | null = null;

export function getJustiScraper(): JustiScraperReal {
  if (!scraperInstance) {
    scraperInstance = new JustiScraperReal();
  }
  return scraperInstance;
}
