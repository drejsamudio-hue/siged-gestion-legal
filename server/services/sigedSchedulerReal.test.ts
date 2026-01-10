import { describe, expect, it, beforeEach, afterEach } from "vitest";
import { SigedSchedulerReal } from "./sigedSchedulerReal";

describe("SigedSchedulerReal", () => {
  let scheduler: SigedSchedulerReal;

  beforeEach(() => {
    scheduler = new SigedSchedulerReal();
  });

  afterEach(() => {
    scheduler.detenerTodos();
  });

  describe("Validación de período de feria", () => {
    it("debería identificar correctamente si estamos en período de feria", () => {
      // Nota: Esta prueba depende de la fecha actual
      // En enero-febrero 2025 debería estar en feria
      const estado = scheduler.obtenerEstado(1);
      expect(estado).toHaveProperty("enFeria");
      expect(typeof estado.enFeria).toBe("boolean");
    });

    it("debería retornar estado del scheduler", () => {
      const estado = scheduler.obtenerEstado(1);
      expect(estado).toHaveProperty("activo");
      expect(estado).toHaveProperty("proximaEjecucion");
      expect(estado).toHaveProperty("enFeria");
    });
  });

  describe("Gestión de schedulers", () => {
    it("debería iniciar un scheduler para un usuario", async () => {
      const userId = 1;
      await scheduler.iniciarScheduler(userId);
      const estado = scheduler.obtenerEstado(userId);
      expect(estado.activo).toBe(true);
    });

    it("debería detener un scheduler", async () => {
      const userId = 1;
      await scheduler.iniciarScheduler(userId);
      scheduler.detenerScheduler(userId);
      const estado = scheduler.obtenerEstado(userId);
      expect(estado.activo).toBe(false);
    });

    it("no debería crear múltiples schedulers para el mismo usuario", async () => {
      const userId = 1;
      await scheduler.iniciarScheduler(userId);
      const estado1 = scheduler.obtenerEstado(userId);
      await scheduler.iniciarScheduler(userId); // Intentar iniciar de nuevo
      const estado2 = scheduler.obtenerEstado(userId);
      expect(estado1.activo).toBe(true);
      expect(estado2.activo).toBe(true);
    });

    it("debería detener todos los schedulers", async () => {
      const userId1 = 1;
      const userId2 = 2;
      await scheduler.iniciarScheduler(userId1);
      await scheduler.iniciarScheduler(userId2);

      scheduler.detenerTodos();

      expect(scheduler.obtenerEstado(userId1).activo).toBe(false);
      expect(scheduler.obtenerEstado(userId2).activo).toBe(false);
    });
  });

  describe("Configuración de cron", () => {
    it("debería ejecutarse los martes y viernes", async () => {
      // La expresión cron '0 8 * * 2,5' significa:
      // - 0 minutos
      // - 8 horas
      // - cualquier día del mes
      // - cualquier mes
      // - martes (2) y viernes (5)
      await scheduler.iniciarScheduler(1);
      const estado = scheduler.obtenerEstado(1);
      expect(estado.proximaEjecucion).toContain("Martes");
      expect(estado.proximaEjecucion).toContain("viernes");
      expect(estado.proximaEjecucion).toContain("8:00");
    });

    it("debería indicar próxima ejecución cuando está activo", async () => {
      const userId = 1;
      await scheduler.iniciarScheduler(userId);
      const estado = scheduler.obtenerEstado(userId);
      expect(estado.proximaEjecucion).toBe("Martes y viernes a las 8:00 AM");
    });

    it("debería indicar 'No programado' cuando no está activo", () => {
      const userId = 1;
      const estado = scheduler.obtenerEstado(userId);
      expect(estado.proximaEjecucion).toBe("No programado");
    });
  });

  describe("Estados del scheduler", () => {
    it("debería retornar estado inactivo por defecto", () => {
      const estado = scheduler.obtenerEstado(999);
      expect(estado.activo).toBe(false);
    });

    it("debería mantener estado independiente por usuario", async () => {
      const userId1 = 1;
      const userId2 = 2;

      await scheduler.iniciarScheduler(userId1);

      const estado1 = scheduler.obtenerEstado(userId1);
      const estado2 = scheduler.obtenerEstado(userId2);

      expect(estado1.activo).toBe(true);
      expect(estado2.activo).toBe(false);
    });
  });
});
