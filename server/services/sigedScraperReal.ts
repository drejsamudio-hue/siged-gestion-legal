import puppeteer, { Browser, Page } from "puppeteer";
import { decryptText } from "./encryptionService";

interface NovedadExpediente {
  numero: string;
  caratula: string;
  dependencia: string;
  ultimoMovimiento: string;
  fechaMovimiento: string;
  estado: "amarillo" | "blanco" | "normal";
}

interface CedulaNotificacion {
  tipo: "cédula" | "despacho" | "otro";
  titulo: string;
  contenido: string;
  fecha: string;
  expediente?: string;
}

/**
 * Servicio de scraping real del SIGED usando Puppeteer
 */
export class SigedScraperReal {
  private browser: Browser | null = null;
  private readonly SIGED_URL = "https://www.jusmisiones.gov.ar/siged/";
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
   * Realiza login en el SIGED
   */
  private async login(
    page: Page,
    username: string,
    password: string
  ): Promise<boolean> {
    try {
      await page.goto(this.SIGED_URL, { waitUntil: "networkidle2", timeout: this.TIMEOUT });

      // Esperar a que aparezca el formulario de login
      await page.waitForSelector('input[name="usuario"]', { timeout: 10000 });

      // Llenar credenciales
      await page.type('input[name="usuario"]', username);
      await page.type('input[name="clave"]', password);

      // Resolver CAPTCHA si existe (esto es manual en el caso real)
      // Por ahora, asumimos que el usuario ya está logueado o que el CAPTCHA se resuelve automáticamente
      const captchaInput = await page.$('input[name="captcha"]');
      if (captchaInput) {
        console.log("CAPTCHA detectado - requiere intervención manual");
        return false;
      }

      // Hacer click en el botón de login
      await page.click('button[type="submit"]');

      // Esperar a que se cargue el dashboard
      await page.waitForNavigation({ waitUntil: "networkidle2", timeout: this.TIMEOUT });

      return true;
    } catch (error) {
      console.error("Error durante login:", error);
      return false;
    }
  }

  /**
   * Extrae las novedades de expedientes del panel principal
   */
  async extraerNovedades(
    username: string,
    passwordEncrypted: string
  ): Promise<NovedadExpediente[]> {
    await this.initBrowser();
    const page = await this.browser!.newPage();

    try {
      // Desencriptar contraseña
      const password = decryptText(passwordEncrypted);

      // Realizar login
      const loginExitoso = await this.login(page, username, password);
      if (!loginExitoso) {
        throw new Error("Login fallido");
      }

      // Esperar a que cargue la tabla de expedientes
      await page.waitForSelector("table, [role='table']", { timeout: 10000 });

      // Extraer datos de expedientes
      const novedades = await page.evaluate(() => {
        const expedientes: NovedadExpediente[] = [];

        // Buscar filas de expedientes (ajustar selectores según estructura real del SIGED)
        const rows = document.querySelectorAll("tr[data-expediente], tbody tr");

        rows.forEach((row) => {
          const cells = row.querySelectorAll("td");
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
            });
          }
        });

        return expedientes;
      });

      return novedades;
    } catch (error) {
      console.error("Error extrayendo novedades:", error);
      throw error;
    } finally {
      await page.close();
    }
  }

  /**
   * Extrae las cédulas y notificaciones del casillero
   */
  async extraerCedulas(
    username: string,
    passwordEncrypted: string
  ): Promise<CedulaNotificacion[]> {
    await this.initBrowser();
    const page = await this.browser!.newPage();

    try {
      // Desencriptar contraseña
      const password = decryptText(passwordEncrypted);

      // Realizar login
      const loginExitoso = await this.login(page, username, password);
      if (!loginExitoso) {
        throw new Error("Login fallido");
      }

      // Navegar al casillero de notificaciones
      await page.goto(`${this.SIGED_URL}aplicacion.php?ai=casillero`, {
        waitUntil: "networkidle2",
        timeout: this.TIMEOUT,
      });

      // Esperar a que cargue el casillero
      await page.waitForSelector("table, [role='table']", { timeout: 10000 });

      // Extraer cédulas y despachos
      const cedulas = await page.evaluate(() => {
        const notificaciones: CedulaNotificacion[] = [];

        // Buscar filas de cédulas (ajustar selectores según estructura real)
        const rows = document.querySelectorAll("tr[data-cedula], tbody tr");

        rows.forEach((row) => {
          const cells = row.querySelectorAll("td");
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
            });
          }
        });

        return notificaciones;
      });

      return cedulas;
    } catch (error) {
      console.error("Error extrayendo cédulas:", error);
      throw error;
    } finally {
      await page.close();
    }
  }

  /**
   * Realiza un escaneo completo del SIGED
   */
  async escaneoCompleto(
    username: string,
    passwordEncrypted: string
  ): Promise<{
    novedades: NovedadExpediente[];
    cedulas: CedulaNotificacion[];
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
let scraperInstance: SigedScraperReal | null = null;

export function getSigedScraper(): SigedScraperReal {
  if (!scraperInstance) {
    scraperInstance = new SigedScraperReal();
  }
  return scraperInstance;
}
