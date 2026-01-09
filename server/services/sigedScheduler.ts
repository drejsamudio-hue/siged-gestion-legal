import { sigedScraperService } from "./sigedScraper";
import { reportGeneratorService } from "./reportGenerator";
import { notifyOwner } from "../_core/notification";
import { getDb } from "../db";
import { users } from "../../drizzle/schema";
import { eq } from "drizzle-orm";

/**
 * Servicio de scheduler para escaneos automáticos del SIGED
 * Se ejecuta los martes y viernes a las 8:00 AM
 */
export class SigedSchedulerService {
  /**
   * Verifica si hoy es un día de escaneo (martes o viernes)
   * y si es la hora correcta (8:00 AM)
   */
  static esHorarioDeEscaneo(): boolean {
    const ahora = new Date();
    const dia = ahora.getDay(); // 0 = domingo, 1 = lunes, 2 = martes, 3 = miércoles, 4 = jueves, 5 = viernes, 6 = sábado
    const hora = ahora.getHours();
    const minutos = ahora.getMinutes();

    // Martes (2) o viernes (5) a las 8:00 AM
    const esMartesoViernes = dia === 2 || dia === 5;
    const esLasOcho = hora === 8 && minutos >= 0 && minutos < 5; // Ventana de 5 minutos

    return esMartesoViernes && esLasOcho;
  }

  /**
   * Verifica si estamos fuera del período de feria
   * La feria termina el último día de febrero
   */
  static estaFueraDelPeriodoFeria(): boolean {
    const ahora = new Date();
    const mes = ahora.getMonth(); // 0 = enero, 1 = febrero, etc.
    const dia = ahora.getDate();

    // Enero (mes 0) = feria
    // Febrero hasta el 28/29 = feria
    // Marzo en adelante = fuera de feria
    if (mes === 0) return false; // Enero = feria
    if (mes === 1) return dia > 28; // Febrero después del 28
    return true; // Otros meses = fuera de feria
  }

  /**
   * Ejecuta el escaneo automático para todos los usuarios
   */
  static async ejecutarEscaneoAutomatico(): Promise<void> {
    try {
      const db = await getDb();
      if (!db) {
        console.error("[SigedScheduler] Database not available");
        return;
      }

      // Obtener todos los usuarios
      const todosLosUsuarios = await db.select().from(users);

      if (todosLosUsuarios.length === 0) {
        console.log("[SigedScheduler] No users found to scan");
        return;
      }

      console.log(
        `[SigedScheduler] Iniciando escaneo automático para ${todosLosUsuarios.length} usuarios`
      );

      // Ejecutar escaneo para cada usuario
      for (const usuario of todosLosUsuarios) {
        try {
          await this.escanearUsuario(usuario.id);
        } catch (error) {
          console.error(`[SigedScheduler] Error escaneando usuario ${usuario.id}:`, error);
        }
      }

      console.log("[SigedScheduler] Escaneo automático completado");
    } catch (error) {
      console.error("[SigedScheduler] Error en escaneo automático:", error);
    }
  }

  /**
   * Escanea expedientes de un usuario específico
   */
  private static async escanearUsuario(userId: number): Promise<void> {
    try {
      console.log(`[SigedScheduler] Escaneando usuario ${userId}`);

      // Obtener novedades del SIGED
      const novedades = await sigedScraperService.escanearExpedientes(userId);

      // Registrar escaneo en base de datos
      const scanId = await sigedScraperService.registrarScan(
        userId,
        novedades,
        "exitoso",
        `Escaneo automático completado: ${novedades.length} novedades encontradas`
      );

      console.log(`[SigedScheduler] Scan ${scanId} registrado para usuario ${userId}`);

      // Si hay novedades, generar informe y enviar email
      if (novedades.length > 0) {
        await this.generarYEnviarInforme(userId, scanId);
      } else {
        console.log(`[SigedScheduler] No novedades encontradas para usuario ${userId}`);
      }
    } catch (error) {
      console.error(`[SigedScheduler] Error escaneando usuario ${userId}:`, error);

      // Registrar error en base de datos
      try {
        await sigedScraperService.registrarScan(
          userId,
          [],
          "error",
          `Error durante escaneo: ${error instanceof Error ? error.message : "Unknown error"}`
        );
      } catch (dbError) {
        console.error(`[SigedScheduler] Error registrando fallo:`, dbError);
      }
    }
  }

  /**
   * Genera informe y lo envía por email
   */
  private static async generarYEnviarInforme(userId: number, scanId: number): Promise<void> {
    try {
      // Generar informe
      const informe = await reportGeneratorService.generarInforme(scanId);

      // Obtener datos del usuario
      const db = await getDb();
      if (!db) {
        throw new Error("Database not available");
      }

      const usuarioResult = await db.select().from(users).where(eq(users.id, userId));
      const usuario = usuarioResult[0];

      if (!usuario || !usuario.email) {
        console.warn(`[SigedScheduler] Usuario ${userId} no tiene email registrado`);
        return;
      }

      // Formatear informe como HTML
      const htmlInforme = reportGeneratorService.formatearInformeHTML(informe);

      // Enviar notificación al propietario
      const resultado = await notifyOwner({
        title: `Informe de Escaneo SIGED - ${new Date().toLocaleDateString("es-AR")}`,
        content: htmlInforme,
      });

      if (resultado) {
        console.log(`[SigedScheduler] Informe enviado a ${usuario.email}`);
      } else {
        console.warn(`[SigedScheduler] Error enviando informe a ${usuario.email}`);
      }
    } catch (error) {
      console.error(`[SigedScheduler] Error generando/enviando informe:`, error);
    }
  }
}

/**
 * Inicializa el scheduler automático
 * Se ejecuta al iniciar el servidor
 */
export function inicializarScheduler(): void {
  console.log("[SigedScheduler] Inicializando scheduler automático");

  // Verificar cada minuto si es hora de ejecutar el escaneo
  setInterval(async () => {
    if (
      SigedSchedulerService.esHorarioDeEscaneo() &&
      SigedSchedulerService.estaFueraDelPeriodoFeria()
    ) {
      console.log("[SigedScheduler] Ejecutando escaneo automático");
      await SigedSchedulerService.ejecutarEscaneoAutomatico();
    }
  }, 60000); // Verificar cada minuto

  console.log("[SigedScheduler] Scheduler inicializado");
  console.log("[SigedScheduler] Escaneos programados para: Martes y viernes a las 8:00 AM");
  console.log("[SigedScheduler] Período de feria: Enero - 28/29 de febrero");
}
