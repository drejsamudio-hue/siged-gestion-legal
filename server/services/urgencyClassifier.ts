/**
 * Servicio de Clasificación de Urgencia para Expedientes
 * Basado en el Reglamento para el Poder Judicial de Misiones (RPJ)
 * y los Códigos Procesales de Misiones
 */

import type { Expediente } from "../../drizzle/schema";

export type PrioridadFeria = "alta_feria" | "media" | "baja";

/**
 * Determina si estamos en período de feria judicial
 * Feria judicial típicamente: 1-31 de enero y 1-31 de julio
 */
export function esPerioFeria(): boolean {
  const now = new Date();
  const mes = now.getMonth() + 1; // 1-12
  return mes === 1 || mes === 7;
}

/**
 * Tipos de procesos que admiten habilitación de feria
 * (urgencia inherente según RPJ de Misiones)
 */
const TIPOS_FERIA = [
  "familia", // Alimentos, guarda, cuestiones de menores
  "penal", // Libertad, integridad física
  "laboral", // Carácter alimentario
];

/**
 * Estados procesales que indican urgencia
 */
const ESTADOS_URGENTES = [
  "recurso", // Recursos pendientes
  "sentencia", // Sentencia reciente, posible recurso
  "ejecucion", // Ejecución de sentencia
];

/**
 * Clasifica la prioridad de un expediente según:
 * 1. Período de feria judicial
 * 2. Tipo de proceso
 * 3. Estado procesal
 * 4. Proximidad de plazos críticos
 */
export function clasificarPrioridad(expediente: Expediente): PrioridadFeria {
  const enFeria = esPerioFeria();
  const tipoEsFeria = TIPOS_FERIA.includes(expediente.tipoProc);
  const estadoEsUrgente = ESTADOS_URGENTES.includes(expediente.estadoProcesal);

  // Lógica de clasificación
  if (enFeria && tipoEsFeria) {
    // En feria, procesos de familia, penal y laboral son ALTA prioridad
    return "alta_feria";
  }

  if (estadoEsUrgente && expediente.proximoPlazo) {
    const ahora = new Date();
    const diasAlPlazo = Math.ceil(
      (expediente.proximoPlazo.getTime() - ahora.getTime()) / (1000 * 60 * 60 * 24)
    );

    if (diasAlPlazo <= 5) {
      // Plazo muy próximo = ALTA prioridad
      return "alta_feria";
    }

    if (diasAlPlazo <= 15) {
      // Plazo moderadamente próximo = MEDIA prioridad
      return "media";
    }
  }

  // Por defecto, BAJA prioridad
  return "baja";
}

/**
 * Determina si un expediente es susceptible de habilitación de feria
 * Según RPJ Misiones y Códigos Procesales
 */
export function esHabilitableFeria(expediente: Expediente): boolean {
  // 1. Procesos inherentemente urgentes (familia, penal, laboral)
  if (TIPOS_FERIA.includes(expediente.tipoProc)) {
    return true;
  }

  // 2. Medidas cautelares y autosatisfactivas (cualquier fuero)
  if (
    expediente.estadoProcesal === "inicio" &&
    expediente.ultimoMovimiento?.includes("medida")
  ) {
    return true;
  }

  // 3. Recursos con plazo vencido o próximo a vencer
  if (expediente.estadoProcesal === "recurso" && expediente.proximoPlazo) {
    const ahora = new Date();
    const diasAlPlazo = Math.ceil(
      (expediente.proximoPlazo.getTime() - ahora.getTime()) / (1000 * 60 * 60 * 24)
    );
    return diasAlPlazo <= 3;
  }

  return false;
}

/**
 * Genera una sugerencia de estrategia según el estado del expediente
 */
export function generarSugerenciaEstrategia(expediente: Expediente): string {
  const enFeria = esPerioFeria();
  const esHabilitable = esHabilitableFeria(expediente);

  if (enFeria && esHabilitable) {
    return "URGENTE: Considere solicitar habilitación de feria para este expediente. El período de feria judicial permite tramitar asuntos urgentes sin interrupción.";
  }

  if (expediente.estadoProcesal === "recurso" && expediente.proximoPlazo) {
    const ahora = new Date();
    const diasAlPlazo = Math.ceil(
      (expediente.proximoPlazo.getTime() - ahora.getTime()) / (1000 * 60 * 60 * 24)
    );

    if (diasAlPlazo <= 5) {
      return `ALERTA: Plazo vencido en ${diasAlPlazo} días. Prepare el recurso inmediatamente.`;
    }

    if (diasAlPlazo <= 15) {
      return `ATENCIÓN: Plazo vencido en ${diasAlPlazo} días. Comience a preparar el recurso.`;
    }
  }

  if (expediente.tipoProc === "laboral") {
    return "Recuerde que los procesos laborales tienen carácter alimentario. Priorice la percepción de fondos y honorarios.";
  }

  if (expediente.tipoProc === "familia") {
    return "Procesos de familia admiten habilitación de feria por su naturaleza urgente. Considere esta vía si hay riesgo en la demora.";
  }

  return "Expediente en trámite ordinario. Monitoree los plazos y próximos movimientos.";
}

/**
 * Calcula el número de días hasta el próximo plazo crítico
 */
export function diasAlProximoPlazo(expediente: Expediente): number | null {
  if (!expediente.proximoPlazo) return null;

  const ahora = new Date();
  const diasAlPlazo = Math.ceil(
    (expediente.proximoPlazo.getTime() - ahora.getTime()) / (1000 * 60 * 60 * 24)
  );

  return diasAlPlazo;
}
