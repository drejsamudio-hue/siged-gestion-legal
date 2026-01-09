import { getDb } from "../db";
import { expedientes, novedadesExpedientes, sigedScans } from "../../drizzle/schema";
import { eq } from "drizzle-orm";
import type { Expediente, InsertSigedScan, InsertNovedadExpediente } from "../../drizzle/schema";

/**
 * Tipos de novedades que pueden encontrarse en el SIGED
 */
export type TipoNovedad = 
  | "despacho"
  | "providencia"
  | "cedula"
  | "sentencia"
  | "resolucion"
  | "traslado"
  | "dictamen"
  | "cambio_estado"
  | "nuevo_plazo"
  | "archivo_documento";

/**
 * Interfaz para representar una novedad encontrada
 */
export interface NovedadEncontrada {
  expedienteId: number;
  tipoNovedad: TipoNovedad;
  descripcion: string;
  estrategiaRecomendada: string;
  escritoSugerido: string;
  urgencia: "baja" | "media" | "alta" | "critica";
}

/**
 * Servicio de scraping del SIGED
 * Simula la obtención de novedades desde el sistema SIGED
 */
export class SigedScraperService {
  /**
   * Escanea todos los expedientes de un usuario en el SIGED
   * En producción, esto se conectaría al SIGED real
   */
  async escanearExpedientes(userId: number): Promise<NovedadEncontrada[]> {
    const db = await getDb();
    if (!db) {
      throw new Error("Database not available");
    }

    // Obtener todos los expedientes del usuario
    const expedientesUsuario = await db
      .select()
      .from(expedientes)
      .where(eq(expedientes.userId, userId));

    const novedades: NovedadEncontrada[] = [];

    // Simular escaneo de cada expediente
    // En producción, aquí iría la lógica de scraping real del SIGED
    for (const exp of expedientesUsuario) {
      const novedadesExp = await this.obtenerNovedadesExpediente(exp);
      novedades.push(...novedadesExp);
    }

    return novedades;
  }

  /**
   * Obtiene novedades de un expediente específico
   * Simula la consulta al SIGED
   */
  private async obtenerNovedadesExpediente(expediente: Expediente): Promise<NovedadEncontrada[]> {
    // En producción, aquí iría la lógica real de scraping
    // Por ahora retorna un array vacío
    // El usuario puede proporcionar las novedades manualmente o integrarse con SIGED real

    const novedades: NovedadEncontrada[] = [];

    // Ejemplo de estructura que se retornaría
    // const ejemploNovedad: NovedadEncontrada = {
    //   expedienteId: expediente.id,
    //   tipoNovedad: "despacho",
    //   descripcion: "Despacho de traslado de demanda",
    //   estrategiaRecomendada: "Presentar contestación dentro del plazo legal",
    //   escritoSugerido: "Contestación de Demanda",
    //   urgencia: "media",
    // };

    return novedades;
  }

  /**
   * Registra un escaneo en la base de datos
   */
  async registrarScan(
    userId: number,
    novedades: NovedadEncontrada[],
    estado: "exitoso" | "error" | "pendiente" = "exitoso",
    detalles?: string
  ): Promise<number> {
    const db = await getDb();
    if (!db) {
      throw new Error("Database not available");
    }

    // Crear registro de escaneo
    const scanData: InsertSigedScan = {
      userId,
      expedientesActualizados: novedades.length,
      novedadesEncontradas: novedades.length,
      estado,
      detalles,
      emailEnviado: 0,
    };

    const result = await db.insert(sigedScans).values(scanData);
    const scanId = result[0].insertId as number;

    // Registrar cada novedad
    for (const novedad of novedades) {
      const novedadData: InsertNovedadExpediente = {
        scanId,
        expedienteId: novedad.expedienteId,
        tipoNovedad: novedad.tipoNovedad,
        descripcion: novedad.descripcion,
        estrategiaRecomendada: novedad.estrategiaRecomendada,
        escritoSugerido: novedad.escritoSugerido,
        urgencia: novedad.urgencia,
      };

      await db.insert(novedadesExpedientes).values(novedadData);
    }

    return scanId;
  }

  /**
   * Obtiene el último escaneo de un usuario
   */
  async obtenerUltimoScan(userId: number) {
    const db = await getDb();
    if (!db) {
      throw new Error("Database not available");
    }

    const resultado = await db
      .select()
      .from(sigedScans)
      .where(eq(sigedScans.userId, userId))
      .orderBy((t) => t.createdAt)
      .limit(1);

    return resultado.length > 0 ? resultado[0] : null;
  }

  /**
   * Obtiene todas las novedades de un escaneo específico
   */
  async obtenerNovedadesDelScan(scanId: number) {
    const db = await getDb();
    if (!db) {
      throw new Error("Database not available");
    }

    return await db
      .select()
      .from(novedadesExpedientes)
      .where(eq(novedadesExpedientes.scanId, scanId));
  }
}

export const sigedScraperService = new SigedScraperService();
