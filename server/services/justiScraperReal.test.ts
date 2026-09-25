import { describe, expect, it } from "vitest";
import { mapearDespachos, mapearNotificaciones } from "./justiScraperReal";
import { parseFecha } from "./justiSchedulerReal";

// Forma relevada de la API de Justi el 25/09/2026. Datos ficticios.
const despachoItem = {
  id_despacho: 991,
  nro_expediente: "12345/2024",
  dependencia_nombre: "Juzgado Civil y Comercial N° 9 - Posadas",
  secretaria_nombre: "SECRETARÍA ÚNICA",
  descripcion_tipo_despacho: "Normal",
  designacion: "PEREZ JUAN C/ EMPRESA SA S/ Daños y Perjuicios",
  sale_con: "Providencia",
};

describe("mapearDespachos", () => {
  it("aplana despachos agrupados por fecha dentro de { data }", () => {
    const r = mapearDespachos({ data: [{ fecha: "2026-09-22", items: [despachoItem] }] });
    expect(r).toHaveLength(1);
    expect(r[0]).toMatchObject({
      numero: "12345/2024",
      caratula: "PEREZ JUAN C/ EMPRESA SA S/ Daños y Perjuicios",
      dependencia: "Juzgado Civil y Comercial N° 9 - Posadas - SECRETARÍA ÚNICA",
      fechaMovimiento: "2026-09-22",
      estado: "normal",
    });
    expect(r[0].ultimoMovimiento).toContain("#991");
    expect(r[0].ultimoMovimiento).toContain("sale con Providencia");
  });

  it("acepta un array plano de despachos con fecha propia", () => {
    const r = mapearDespachos([{ ...despachoItem, fecha: "2026-09-18" }]);
    expect(r[0].fechaMovimiento).toBe("2026-09-18");
  });

  it("dos despachos del mismo expediente generan movimientos distintos", () => {
    const r = mapearDespachos({
      data: [
        { fecha: "2026-09-22", items: [despachoItem] },
        { fecha: "2026-09-25", items: [{ ...despachoItem, id_despacho: 992 }] },
      ],
    });
    expect(r[0].ultimoMovimiento).not.toBe(r[1].ultimoMovimiento);
  });

  it("ignora respuestas vacías o de error", () => {
    expect(mapearDespachos(null)).toEqual([]);
    expect(mapearDespachos({ error: "El usuario y el Token no son correspondientes" })).toEqual([]);
    expect(mapearDespachos({ data: [] })).toEqual([]);
  });
});

describe("mapearNotificaciones", () => {
  it("convierte notificaciones detalladas en cédulas", () => {
    const r = mapearNotificaciones({
      data: [
        {
          numero_expediente: "12345/2024",
          caratula: "PEREZ JUAN C/ EMPRESA SA",
          fecha_envio_notificacion: "2026-09-24",
          dependencia: "Juzgado Civil y Comercial N° 9",
          remitente: "Secretaría",
          documento_adjunto: "cedula.pdf",
        },
      ],
    });
    expect(r).toEqual([
      {
        tipo: "cédula",
        titulo: "Expte. 12345/2024 - PEREZ JUAN C/ EMPRESA SA",
        contenido: "Dependencia: Juzgado Civil y Comercial N° 9\nRemitente: Secretaría\nDocumento: cedula.pdf",
        fecha: "2026-09-24",
        expediente: "12345/2024",
      },
    ]);
  });

  it("devuelve vacío sin notificaciones", () => {
    expect(mapearNotificaciones([])).toEqual([]);
    expect(mapearNotificaciones([{ cantidad: 0 }])).toEqual([]);
  });
});

describe("parseFecha con el formato de Justi", () => {
  it("toma aaaa-mm-dd como fecha local (no corre al día anterior)", () => {
    const d = parseFecha("2026-09-22")!;
    expect([d.getFullYear(), d.getMonth(), d.getDate()]).toEqual([2026, 8, 22]);
  });
});
