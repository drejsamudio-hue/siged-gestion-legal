import * as cron from "node-cron";
import { getJustiScraper } from "./justiScraperReal";
import {
  getJustiCredentials,
  updateJustiSyncStatus,
  saveJustiNotificacion,
  saveJustiNovedad,
} from "../db";
import { notifyOwner } from "../_core/notification";

const CRON_EXPRESSION = "0 8 * * 2,5"; // Martes y viernes 8:00

/**
 * Enero completo es feria. La de invierno la fija cada año el STJ por acordada,
 * así que se configura con JUSTI_FERIAS="2026-07-13:2026-07-24,..." (inclusive).
 */
export function isEnFeriaJudicial(date: Date = new Date(), ferias = process.env.JUSTI_FERIAS ?? ""): boolean {
  if (date.getMonth() === 0) return true;
  const dia = date.toISOString().slice(0, 10);
  return ferias
    .split(",")
    .map(r => r.trim().split(":"))
    .some(([desde, hasta]) => desde && hasta && dia >= desde && dia <= hasta);
}

export class JustiSchedulerReal {
  private scheduledTasks: Map<number, cron.ScheduledTask> = new Map();

  private async ejecutarEscaneoParaUsuario(userId: number): Promise<void> {
    try {
      const creds = await getJustiCredentials(userId);
      if (!creds) {
        console.warn(`[Justi Scheduler] Sin credenciales para usuario ${userId}`);
        return;
      }

      const resultado = await getJustiScraper().escaneoCompleto(creds.username, creds.password);

      // Justi repite lo de los últimos 7 días en cada consulta: se cuentan solo los registros nuevos.
      let cedulasNuevas = 0;
      for (const cedula of resultado.cedulas) {
        const nueva = await saveJustiNotificacion({
          userId,
          tipo: cedula.tipo,
          titulo: cedula.titulo,
          contenido: cedula.contenido,
          fechaNotificacion: parseFecha(cedula.fecha),
        });
        if (nueva) cedulasNuevas++;
      }

      let novedadesNuevas = 0;
      for (const novedad of resultado.novedades) {
        const nueva = await saveJustiNovedad({
          userId,
          numero: novedad.numero,
          caratula: novedad.caratula,
          dependencia: novedad.dependencia,
          ultimoMovimiento: novedad.ultimoMovimiento,
          fechaMovimiento: parseFecha(novedad.fechaMovimiento),
          estado: novedad.estado,
        });
        if (nueva) novedadesNuevas++;
      }

      await updateJustiSyncStatus(userId, true);

      if (novedadesNuevas + cedulasNuevas > 0) {
        await notifyOwner({
          title: "Justi - Nuevas novedades",
          content: `Justi: ${novedadesNuevas} despachos nuevos y ${cedulasNuevas} notificaciones nuevas para el usuario ${userId}.`,
        });
      }
    } catch (error: any) {
      console.error(`[Justi Scheduler] Error en escaneo para usuario ${userId}:`, error);
      await updateJustiSyncStatus(userId, false, error.message);
    }
  }

  async iniciarScheduler(userId: number): Promise<void> {
    if (this.scheduledTasks.has(userId)) return;

    const task = cron.schedule(CRON_EXPRESSION, async () => {
      if (isEnFeriaJudicial()) {
        console.log(`[Justi Scheduler] Escaneo omitido para usuario ${userId} - feria judicial`);
        return;
      }
      await this.ejecutarEscaneoParaUsuario(userId);
    });

    this.scheduledTasks.set(userId, task);
  }

  detenerScheduler(userId: number): void {
    const task = this.scheduledTasks.get(userId);
    if (task) {
      task.stop();
      this.scheduledTasks.delete(userId);
    }
  }

  async escaneoManual(userId: number): Promise<void> {
    await this.ejecutarEscaneoParaUsuario(userId);
  }

  obtenerEstado(userId: number): { activo: boolean; proximaEjecucion: string; enFeria: boolean } {
    const activo = this.scheduledTasks.has(userId);
    return {
      activo,
      proximaEjecucion: activo ? "Martes y viernes a las 8:00 AM" : "No programado",
      enFeria: isEnFeriaJudicial(),
    };
  }

  detenerTodos(): void {
    this.scheduledTasks.forEach(task => task.stop());
    this.scheduledTasks.clear();
  }
}

/**
 * Acepta dd/mm/aaaa y aaaa-mm-dd (Justi devuelve este último). Las fechas sin hora se toman
 * como fecha local: `new Date("2026-09-22")` sería UTC y en Argentina mostraría el 21/09.
 */
export function parseFecha(texto: string): Date | undefined {
  const m = texto?.match(/(\d{1,2})\/(\d{1,2})\/(\d{4})/);
  if (m) return new Date(Number(m[3]), Number(m[2]) - 1, Number(m[1]));
  const iso = texto?.match(/^(\d{4})-(\d{2})-(\d{2})$/);
  if (iso) return new Date(Number(iso[1]), Number(iso[2]) - 1, Number(iso[3]));
  const d = new Date(texto);
  return isNaN(d.getTime()) ? undefined : d;
}

let schedulerInstance: JustiSchedulerReal | null = null;

export function getJustiScheduler(): JustiSchedulerReal {
  if (!schedulerInstance) {
    schedulerInstance = new JustiSchedulerReal();
  }
  return schedulerInstance;
}
