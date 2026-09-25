import { describe, expect, it, afterEach } from "vitest";
import { JustiSchedulerReal, isEnFeriaJudicial, parseFecha } from "./justiSchedulerReal";

describe("isEnFeriaJudicial", () => {
  it("enero completo es feria", () => {
    expect(isEnFeriaJudicial(new Date(2026, 0, 20, 12), "")).toBe(true);
  });

  it("usa los rangos configurados para la feria de invierno", () => {
    const ferias = "2026-07-13:2026-07-24";
    expect(isEnFeriaJudicial(new Date(2026, 6, 15, 12), ferias)).toBe(true);
    expect(isEnFeriaJudicial(new Date(2026, 6, 27, 12), ferias)).toBe(false);
  });

  it("un día hábil común no es feria", () => {
    expect(isEnFeriaJudicial(new Date(2026, 8, 25, 12), "")).toBe(false);
  });
});

describe("parseFecha", () => {
  it("interpreta dd/mm/aaaa", () => {
    const d = parseFecha("05/03/2026")!;
    expect([d.getFullYear(), d.getMonth(), d.getDate()]).toEqual([2026, 2, 5]);
  });

  it("interpreta ISO", () => {
    expect(parseFecha("2026-03-05T10:00:00Z")?.toISOString()).toBe("2026-03-05T10:00:00.000Z");
  });

  it("devuelve undefined si no es una fecha", () => {
    expect(parseFecha("sin fecha")).toBeUndefined();
  });
});

describe("JustiSchedulerReal", () => {
  const scheduler = new JustiSchedulerReal();
  afterEach(() => scheduler.detenerTodos());

  it("inicia y detiene por usuario", async () => {
    await scheduler.iniciarScheduler(1);
    expect(scheduler.obtenerEstado(1).activo).toBe(true);
    expect(scheduler.obtenerEstado(2).activo).toBe(false);
    scheduler.detenerScheduler(1);
    expect(scheduler.obtenerEstado(1).activo).toBe(false);
  });
});
