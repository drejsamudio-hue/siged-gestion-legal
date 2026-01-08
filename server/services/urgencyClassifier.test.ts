import { describe, it, expect, vi, beforeEach } from "vitest";
import {
  clasificarPrioridad,
  esHabilitableFeria,
  generarSugerenciaEstrategia,
  diasAlProximoPlazo,
  esPerioFeria,
} from "./urgencyClassifier";
import type { Expediente } from "../../drizzle/schema";

describe("urgencyClassifier", () => {
  const mockExpediente: Expediente = {
    id: 1,
    userId: 1,
    numero: "117906/2025",
    caratula: "Test c/ Test",
    dependencia: "Juzgado Civil 1",
    tipoProc: "civil_comercial",
    estadoProcesal: "inicio",
    ultimoMovimiento: "Demanda presentada",
    fechaUltimoMovimiento: new Date(),
    proximoPlazo: null,
    prioridad: "media",
    notas: null,
    createdAt: new Date(),
    updatedAt: new Date(),
  };

  describe("esPerioFeria", () => {
    it("debería retornar true en enero", () => {
      const enero = new Date(2025, 0, 15);
      vi.setSystemTime(enero);
      expect(esPerioFeria()).toBe(true);
      vi.useRealTimers();
    });

    it("debería retornar true en julio", () => {
      const julio = new Date(2025, 6, 15);
      vi.setSystemTime(julio);
      expect(esPerioFeria()).toBe(true);
      vi.useRealTimers();
    });

    it("debería retornar false en otros meses", () => {
      const febrero = new Date(2025, 1, 15);
      vi.setSystemTime(febrero);
      expect(esPerioFeria()).toBe(false);
      vi.useRealTimers();
    });
  });

  describe("clasificarPrioridad", () => {
    it("debería clasificar como alta_feria un expediente de familia en período de feria", () => {
      const enero = new Date(2025, 0, 15);
      vi.setSystemTime(enero);

      const expediente: Expediente = {
        ...mockExpediente,
        tipoProc: "familia",
      };

      expect(clasificarPrioridad(expediente)).toBe("alta_feria");
      vi.useRealTimers();
    });

    it("debería clasificar como alta_feria un expediente penal en período de feria", () => {
      const enero = new Date(2025, 0, 15);
      vi.setSystemTime(enero);

      const expediente: Expediente = {
        ...mockExpediente,
        tipoProc: "penal",
      };

      expect(clasificarPrioridad(expediente)).toBe("alta_feria");
      vi.useRealTimers();
    });

    it("debería clasificar como alta_feria un expediente laboral en período de feria", () => {
      const enero = new Date(2025, 0, 15);
      vi.setSystemTime(enero);

      const expediente: Expediente = {
        ...mockExpediente,
        tipoProc: "laboral",
      };

      expect(clasificarPrioridad(expediente)).toBe("alta_feria");
      vi.useRealTimers();
    });

    it("debería clasificar como media un expediente con plazo próximo (5-15 días)", () => {
      const ahora = new Date();
      const proximoPlazo = new Date(ahora.getTime() + 10 * 24 * 60 * 60 * 1000); // 10 días

      const expediente: Expediente = {
        ...mockExpediente,
        estadoProcesal: "recurso",
        proximoPlazo,
      };

      expect(clasificarPrioridad(expediente)).toBe("media");
    });

    it("debería clasificar como baja un expediente sin urgencia", () => {
      const expediente: Expediente = {
        ...mockExpediente,
        tipoProc: "civil_comercial",
        estadoProcesal: "prueba",
      };

      expect(clasificarPrioridad(expediente)).toBe("baja");
    });
  });

  describe("esHabilitableFeria", () => {
    it("debería retornar true para procesos de familia", () => {
      const expediente: Expediente = {
        ...mockExpediente,
        tipoProc: "familia",
      };

      expect(esHabilitableFeria(expediente)).toBe(true);
    });

    it("debería retornar true para procesos penales", () => {
      const expediente: Expediente = {
        ...mockExpediente,
        tipoProc: "penal",
      };

      expect(esHabilitableFeria(expediente)).toBe(true);
    });

    it("debería retornar true para procesos laborales", () => {
      const expediente: Expediente = {
        ...mockExpediente,
        tipoProc: "laboral",
      };

      expect(esHabilitableFeria(expediente)).toBe(true);
    });

    it("debería retornar true para medidas cautelares con plazo vencido", () => {
      const ahora = new Date();
      const proximoPlazo = new Date(ahora.getTime() - 1 * 24 * 60 * 60 * 1000); // 1 día atrás

      const expediente: Expediente = {
        ...mockExpediente,
        tipoProc: "civil_comercial",
        estadoProcesal: "recurso",
        proximoPlazo,
      };

      expect(esHabilitableFeria(expediente)).toBe(true);
    });

    it("debería retornar false para expedientes ordinarios sin urgencia", () => {
      const expediente: Expediente = {
        ...mockExpediente,
        tipoProc: "civil_comercial",
        estadoProcesal: "prueba",
      };

      expect(esHabilitableFeria(expediente)).toBe(false);
    });
  });

  describe("diasAlProximoPlazo", () => {
    it("debería calcular correctamente los días al próximo plazo", () => {
      const ahora = new Date();
      const proximoPlazo = new Date(ahora.getTime() + 10 * 24 * 60 * 60 * 1000); // 10 días

      const expediente: Expediente = {
        ...mockExpediente,
        proximoPlazo,
      };

      const dias = diasAlProximoPlazo(expediente);
      expect(dias).toBe(10);
    });

    it("debería retornar null si no hay próximo plazo", () => {
      const expediente: Expediente = {
        ...mockExpediente,
        proximoPlazo: null,
      };

      expect(diasAlProximoPlazo(expediente)).toBeNull();
    });

    it("debería retornar número negativo si el plazo ya venció", () => {
      const ahora = new Date();
      const proximoPlazo = new Date(ahora.getTime() - 5 * 24 * 60 * 60 * 1000); // 5 días atrás

      const expediente: Expediente = {
        ...mockExpediente,
        proximoPlazo,
      };

      const dias = diasAlProximoPlazo(expediente);
      expect(dias).toBeLessThan(0);
    });
  });

  describe("generarSugerenciaEstrategia", () => {
    it("debería sugerir habilitación de feria para procesos urgentes en feria", () => {
      const enero = new Date(2025, 0, 15);
      vi.setSystemTime(enero);

      const expediente: Expediente = {
        ...mockExpediente,
        tipoProc: "familia",
      };

      const sugerencia = generarSugerenciaEstrategia(expediente);
      expect(sugerencia).toContain("habilitación de feria");
      vi.useRealTimers();
    });

    it("debería alertar sobre plazo próximo a vencer", () => {
      const febrero = new Date(2025, 1, 15);
      vi.setSystemTime(febrero);

      const ahora = new Date();
      const proximoPlazo = new Date(ahora.getTime() + 3 * 24 * 60 * 60 * 1000);

      const expediente: Expediente = {
        ...mockExpediente,
        tipoProc: "civil_comercial",
        estadoProcesal: "recurso",
        proximoPlazo,
      };

      const sugerencia = generarSugerenciaEstrategia(expediente);
      expect(sugerencia).toContain("ALERTA");
      vi.useRealTimers();
    });

    it("debería recordar carácter alimentario de procesos laborales", () => {
      const febrero = new Date(2025, 1, 15);
      vi.setSystemTime(febrero);

      const expediente: Expediente = {
        ...mockExpediente,
        tipoProc: "laboral",
      };

      const sugerencia = generarSugerenciaEstrategia(expediente);
      expect(sugerencia).toContain("alimentario");
      vi.useRealTimers();
    });

    it("debería sugerir habilitación de feria para procesos de familia", () => {
      const febrero = new Date(2025, 1, 15);
      vi.setSystemTime(febrero);

      const expediente: Expediente = {
        ...mockExpediente,
        tipoProc: "familia",
      };

      const sugerencia = generarSugerenciaEstrategia(expediente);
      expect(sugerencia).toContain("familia");
      vi.useRealTimers();
    });
  });
});
