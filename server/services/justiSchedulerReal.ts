import cron from "node-cron";
import { getJustiScraper } from "./justiScraperReal";
import { db } from "../db";
import { sigedScans, novedadesExpedientes, cedulasNotificacion } from "../_core/schema";
import { eq } from "drizzle-orm";
import { sendNotificationEmail } from "../_core/notification";

interface SchedulerConfig {
  enabled: boolean;
  cronExpression: string; // Ej: "0 8 * * 2,5" (martes y viernes a las 8 AM)
  userId?: string;
}

/**
 * Servicio de scheduling automático para Justi
 * Similar al de SIGED pero para la PWA de Justi
 */
export class JustiSchedulerReal {
  private task: cron.ScheduledTask | null = null;
  private config: SchedulerConfig = {
    enabled: false,
    cronExpression: "0 8 * * 2,5", // Martes y viernes a las 8 AM por defecto
  };

  /**
   * Inicia el scheduler con una expresión cron
   */
  startScheduler(cronExpression: string = "0 8 * * 2,5", userId?: string): void {
    if (this.task) {
      this.stopScheduler();
    }

    this.config = {
      enabled: true,
      cronExpression,
      userId,
    };

    this.task = cron.schedule(cronExpression, async () => {
      console.log(`[Justi Scheduler] Ejecutando escaneo automático - ${new Date().toISOString()}`);
      await this.executeScheduledScan();
    });

    console.log(`[Justi Scheduler] Iniciado con expresión: ${cronExpression}`);
  }

  /**
   * Detiene el scheduler
   */
  stopScheduler(): void {
    if (this.task) {
      this.task.stop();
      this.task = null;
      this.config.enabled = false;
      console.log("[Justi Scheduler] Detenido");
    }
  }

  /**
   * Verifica si estamos en período de feria judicial (Misiones)
   */
  private isEnFeria(): boolean {
    const hoy = new Date();
    const mes = hoy.getMonth() + 1;
    const dia = hoy.getDate();

    // Feria judicial en Misiones: del 1 al 31 de enero, 1 al 28 de julio
    if ((mes === 1) || (mes === 7)) {
      return true;
    }

    // Feriados nacionales (aproximado)
    const feriados = [
      "02-25", // Carnaval
      "03-24", // Conmemoración de la Batalla de la Vuelta de Obligado
      "04-02", // Día del Veterano
      "05-01", // Día del Trabajo
      "05-25", // Día de la Independencia
      "06-17", // Guemes
      "06-20", // Bandera
      "07-09", // Independencia
      "08-17", // Muerto
      "10-12", // Resistencia
      "11-18", // Nacionalidad
      "12-08", // Inmaculada
      "12-25", // Navidad
    ];

    const fechaFormato = `${String(mes).padStart(2, "0")}-${String(dia).padStart(2, "0")}`;
    if (feriados.includes(fechaFormato)) {
      return true;
    }

    return false;
  }

  /**
   * Ejecuta el escaneo automático
   */
  private async executeScheduledScan(): Promise<void> {
    try {
      // Verificar si estamos en feria
      if (this.isEnFeria()) {
        console.log("[Justi Scheduler] Período de feria judicial detectado - escaneo cancelado");
        return;
      }

      // Obtener todos los usuarios con credenciales de Justi almacenadas
      // Por ahora, asumimos que hay un usuario por defecto o se configura posteriormente
      const users = await db.query.users.findMany();

      if (users.length === 0) {
        console.log("[Justi Scheduler] No hay usuarios configurados");
        return;
      }

      for (const user of users) {
        try {
          console.log(`[Justi Scheduler] Escaneando para usuario: ${user.id}`);
          await this.scanUserJusti(user.id);
        } catch (error) {
          console.error(`[Justi Scheduler] Error escaneando usuario ${user.id}:`, error);
          // Continuar con el siguiente usuario
        }
      }

      console.log("[Justi Scheduler] Escaneo completado exitosamente");
    } catch (error) {
      console.error("[Justi Scheduler] Error durante escaneo:", error);
    }
  }

  /**
   * Escanea Justi para un usuario específico
   */
  private async scanUserJusti(userId: string): Promise<void> {
    // Obtener credenciales de Justi del usuario (asumiendo que están almacenadas)
    // Esto dependerá de tu esquema de base de datos
    // Por ahora, lanzaremos un error indicando que se necesitan credenciales

    throw new Error(
      `Credenciales de Justi no configuradas para usuario ${userId}. ` +
      `Implementar almacenamiento de credenciales de Justi en la base de datos.`
    );

    // Una vez que se implementen las credenciales:
    /*
    const scraper = getJustiScraper();
    const result = await scraper.escaneoCompleto(username, passwordEncrypted);

    // Guardar resultado del escaneo
    const scanRecord = await db.insert(sigedScans).values({
      userId,
      novedadesCount: result.novedades.length,
      cedulasCount: result.cedulas.length,
      status: "completado",
      timestamp: result.timestamp,
    });

    // Procesar novedades
    for (const novedad of result.novedades) {
      await db.insert(novedadesExpedientes).values({
        numero: novedad.numero,
        caratula: novedad.caratula,
        dependencia: novedad.dependencia,
        ultimoMovimiento: novedad.ultimoMovimiento,
        fechaMovimiento: novedad.fechaMovimiento,
        estado: novedad.estado,
        fuente: "justi",
        userId,
        scanId: scanRecord[0].insertId,
      });
    }

    // Procesar cédulas
    for (const cedula of result.cedulas) {
      await db.insert(cedulasNotificacion).values({
        tipo: cedula.tipo,
        titulo: cedula.titulo,
        contenido: cedula.contenido,
        fecha: cedula.fecha,
        expediente: cedula.expediente,
        fuente: "justi",
        userId,
        scanId: scanRecord[0].insertId,
      });
    }
    */
  }

  /**
   * Obtiene la configuración actual del scheduler
   */
  getConfig(): SchedulerConfig {
    return this.config;
  }

  /**
   * Obtiene el estado del scheduler
   */
  isRunning(): boolean {
    return this.config.enabled && this.task !== null;
  }
}

// Crear instancia singleton
let schedulerInstance: JustiSchedulerReal | null = null;

export function getJustiScheduler(): JustiSchedulerReal {
  if (!schedulerInstance) {
    schedulerInstance = new JustiSchedulerReal();
  }
  return schedulerInstance;
}
