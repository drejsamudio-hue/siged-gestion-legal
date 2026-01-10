import * as cron from "node-cron";
import { getSigedScraper } from "./sigedScraperReal";
import { getSigedCredentials, updateSigedSyncStatus, saveSigedNotificacion } from "../db";
import { notifyOwner } from "../_core/notification";

/**
 * Servicio de scheduler real para escaneos automáticos del SIGED
 * Ejecuta los martes y viernes a las 8:00 AM
 */
export class SigedSchedulerReal {
  private scheduledTasks: Map<number, cron.ScheduledTask> = new Map();
  private readonly CRON_EXPRESSION = "0 8 * * 2,5"; // Martes (2) y viernes (5) a las 8:00 AM
  private readonly FERIA_END_DATE = new Date(2025, 1, 28); // 28 de febrero de 2025

  /**
   * Verifica si estamos en período de feria judicial
   */
  private isInFeriaJudicial(): boolean {
    const today = new Date();
    const feriaStart = new Date(2025, 0, 1); // 1 de enero
    const feriaEnd = this.FERIA_END_DATE;

    return today >= feriaStart && today <= feriaEnd;
  }

  /**
   * Ejecuta un escaneo del SIGED para un usuario específico
   */
  private async ejecutarEscaneoParaUsuario(userId: number): Promise<void> {
    try {
      console.log(`[SIGED Scheduler] Iniciando escaneo para usuario ${userId}`);

      // Obtener credenciales del usuario
      const creds = await getSigedCredentials(userId);
      if (!creds) {
        console.warn(`[SIGED Scheduler] No credentials found for user ${userId}`);
        return;
      }

      // Ejecutar escaneo
      const scraper = getSigedScraper();
      const resultado = await scraper.escaneoCompleto(creds.username, creds.password);

      // Guardar notificaciones en la base de datos
      for (const cedula of resultado.cedulas) {
        await saveSigedNotificacion({
          userId,
          tipo: cedula.tipo,
          titulo: cedula.titulo,
          contenido: cedula.contenido,
          fechaNotificacion: new Date(cedula.fecha),
        });
      }

      // Actualizar estado de sincronización
      await updateSigedSyncStatus(userId, true);

      console.log(
        `[SIGED Scheduler] Escaneo completado para usuario ${userId}. Novedades: ${resultado.novedades.length}, Cédulas: ${resultado.cedulas.length}`
      );

      // Enviar notificación al propietario
      if (resultado.cedulas.length > 0) {
        await notifyOwner({
          title: "SIGED - Nuevas notificaciones",
          content: `Se encontraron ${resultado.cedulas.length} nuevas cédulas/despachos en el SIGED para el usuario ${userId}.`,
        });
      }
    } catch (error: any) {
      console.error(`[SIGED Scheduler] Error en escaneo para usuario ${userId}:`, error);
      await updateSigedSyncStatus(userId, false, error.message);
    }
  }

  /**
   * Inicia el scheduler para un usuario
   */
  async iniciarScheduler(userId: number): Promise<void> {
    // Si ya existe una tarea para este usuario, no hacer nada
    if (this.scheduledTasks.has(userId)) {
      console.log(`[SIGED Scheduler] Scheduler ya está activo para usuario ${userId}`);
      return;
    }

    // Crear tarea cron
    const task = cron.schedule(this.CRON_EXPRESSION, async () => {
      // Solo ejecutar si no estamos en período de feria
      if (!this.isInFeriaJudicial()) {
        await this.ejecutarEscaneoParaUsuario(userId);
      } else {
        console.log(
          `[SIGED Scheduler] Escaneo omitido para usuario ${userId} - Período de feria judicial`
        );
      }
    });

    this.scheduledTasks.set(userId, task);
    console.log(`[SIGED Scheduler] Scheduler iniciado para usuario ${userId}`);
  }

  /**
   * Detiene el scheduler para un usuario
   */
  detenerScheduler(userId: number): void {
    const task = this.scheduledTasks.get(userId);
    if (task) {
      task.stop();
      this.scheduledTasks.delete(userId);
      console.log(`[SIGED Scheduler] Scheduler detenido para usuario ${userId}`);
    }
  }

  /**
   * Ejecuta un escaneo manual inmediato
   */
  async escaneoManual(userId: number): Promise<void> {
    console.log(`[SIGED Scheduler] Iniciando escaneo manual para usuario ${userId}`);
    await this.ejecutarEscaneoParaUsuario(userId);
  }

  /**
   * Obtiene el estado del scheduler para un usuario
   */
  obtenerEstado(userId: number): {
    activo: boolean;
    proximaEjecucion: string;
    enFeria: boolean;
  } {
    const activo = this.scheduledTasks.has(userId);
    const proximaEjecucion = activo ? "Martes y viernes a las 8:00 AM" : "No programado";
    const enFeria = this.isInFeriaJudicial();

    return {
      activo,
      proximaEjecucion,
      enFeria,
    };
  }

  /**
   * Detiene todos los schedulers
   */
  detenerTodos(): void {
    this.scheduledTasks.forEach((task, userId) => {
      task.stop();
      console.log(`[SIGED Scheduler] Scheduler detenido para usuario ${userId}`);
    });
    this.scheduledTasks.clear();
  }
}

// Crear instancia singleton
let schedulerInstance: SigedSchedulerReal | null = null;

export function getSigedScheduler(): SigedSchedulerReal {
  if (!schedulerInstance) {
    schedulerInstance = new SigedSchedulerReal();
  }
  return schedulerInstance;
}

/**
 * Inicializa los schedulers para todos los usuarios con credenciales SIGED
 * Llamar esto al iniciar el servidor
 */
export async function initializeAllSchedulers(): Promise<void> {
  try {
    console.log("[SIGED Scheduler] Inicializando schedulers para todos los usuarios");
    // Nota: En una implementación real, aquí se consultaría la base de datos
    // para obtener todos los usuarios con credenciales SIGED activas
    // Por ahora, esto se hace manualmente cuando el usuario inicia sesión
  } catch (error) {
    console.error("[SIGED Scheduler] Error inicializando schedulers:", error);
  }
}
