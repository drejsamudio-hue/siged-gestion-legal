import { getDb } from "../db";
import { sigedScans, novedadesExpedientes, expedientes } from "../../drizzle/schema";
import { eq } from "drizzle-orm";
import type { SigedScan, NovedadExpediente } from "../../drizzle/schema";

/**
 * Interfaz para el informe generado
 */
export interface InformeEscaneo {
  fecha: Date;
  totalExpedientes: number;
  totalNovedades: number;
  expedientesConNovedades: number;
  novedadesPorUrgencia: {
    critica: number;
    alta: number;
    media: number;
    baja: number;
  };
  detalleNovedades: Array<{
    numeroExpediente: string;
    caratula: string;
    tipoNovedad: string;
    descripcion: string;
    estrategiaRecomendada: string;
    escritoSugerido: string;
    urgencia: string;
  }>;
  resumenEstrategias: string;
  proximosEscritos: Array<{
    tipo: string;
    expedientes: string[];
    prioridad: string;
  }>;
}

/**
 * Servicio para generar informes de escaneos del SIGED
 */
export class ReportGeneratorService {
  /**
   * Genera un informe completo de un escaneo
   */
  async generarInforme(scanId: number): Promise<InformeEscaneo> {
    const db = await getDb();
    if (!db) {
      throw new Error("Database not available");
    }

    // Obtener datos del escaneo
    const scan = await db.select().from(sigedScans).where(eq(sigedScans.id, scanId));
    if (scan.length === 0) {
      throw new Error("Scan not found");
    }

    const scanData = scan[0];

    // Obtener novedades del escaneo
    const novedades = await db
      .select()
      .from(novedadesExpedientes)
      .where(eq(novedadesExpedientes.scanId, scanId));

    // Enriquecer novedades con información de expedientes
    const novedadesEnriquecidas = await Promise.all(
      novedades.map(async (novedad) => {
        const exp = await db
          .select()
          .from(expedientes)
          .where(eq(expedientes.id, novedad.expedienteId));

        return {
          ...novedad,
          numeroExpediente: exp[0]?.numero || "N/A",
          caratula: exp[0]?.caratula || "N/A",
        };
      })
    );

    // Calcular estadísticas
    const urgenciaCount = {
      critica: novedades.filter((n) => n.urgencia === "critica").length,
      alta: novedades.filter((n) => n.urgencia === "alta").length,
      media: novedades.filter((n) => n.urgencia === "media").length,
      baja: novedades.filter((n) => n.urgencia === "baja").length,
    };

    // Agrupar escritos sugeridos
    const escritosPorTipo = this.agruparEscritos(novedadesEnriquecidas);

    // Generar resumen de estrategias
    const resumenEstrategias = this.generarResumenEstrategias(novedadesEnriquecidas);

    return {
      fecha: scanData.createdAt,
      totalExpedientes: scanData.expedientesActualizados || 0,
      totalNovedades: scanData.novedadesEncontradas || 0,
      expedientesConNovedades: new Set(novedades.map((n) => n.expedienteId)).size,
      novedadesPorUrgencia: urgenciaCount,
      detalleNovedades: novedadesEnriquecidas.map((n) => ({
        numeroExpediente: n.numeroExpediente,
        caratula: n.caratula,
        tipoNovedad: n.tipoNovedad,
        descripcion: n.descripcion || "",
        estrategiaRecomendada: n.estrategiaRecomendada || "",
        escritoSugerido: n.escritoSugerido || "",
        urgencia: (n.urgencia as string) || "media",
      })),
      resumenEstrategias,
      proximosEscritos: escritosPorTipo,
    };
  }

  /**
   * Agrupa escritos sugeridos por tipo
   */
  private agruparEscritos(
    novedades: Array<
      NovedadExpediente & {
        numeroExpediente: string;
        caratula: string;
      }
    >
  ) {
    const escritos: Record<
      string,
      {
        tipo: string;
        expedientes: string[];
        prioridad: string;
      }
    > = {};

    for (const novedad of novedades) {
      if (!novedad.escritoSugerido) continue;

      const tipo = novedad.escritoSugerido as string;
      if (!escritos[tipo]) {
        escritos[tipo] = {
          tipo,
          expedientes: [],
          prioridad: novedad.urgencia as string,
        };
      }

      escritos[tipo].expedientes.push(novedad.numeroExpediente);

      // Actualizar prioridad si es más urgente
      const urgenciaOrder = { critica: 4, alta: 3, media: 2, baja: 1 };
      if (
        urgenciaOrder[novedad.urgencia as keyof typeof urgenciaOrder] >
        urgenciaOrder[escritos[tipo].prioridad as keyof typeof urgenciaOrder]
      ) {
        escritos[tipo].prioridad = novedad.urgencia as string;
      }
    }

    return Object.values(escritos).sort((a, b) => {
      const urgenciaOrder = { critica: 4, alta: 3, media: 2, baja: 1 };
      return (
        urgenciaOrder[b.prioridad as keyof typeof urgenciaOrder] -
        urgenciaOrder[a.prioridad as keyof typeof urgenciaOrder]
      );
    });
  }

  /**
   * Genera un resumen ejecutivo de estrategias
   */
  private generarResumenEstrategias(
    novedades: Array<
      NovedadExpediente & {
        numeroExpediente: string;
        caratula: string;
      }
    >
  ): string {
    const estrategias = new Set<string>();

      for (const novedad of novedades) {
        if (novedad.estrategiaRecomendada) {
          estrategias.add(novedad.estrategiaRecomendada as string);
        }
      }

    if (estrategias.size === 0) {
      return "No hay estrategias recomendadas en este escaneo.";
    }

    const lista = Array.from(estrategias)
      .map((e, i) => `${i + 1}. ${e}`)
      .join("\n");

    return `Se identificaron ${estrategias.size} estrategias recomendadas:\n\n${lista}`;
  }

  /**
   * Formatea el informe como HTML para email
   */
  formatearInformeHTML(informe: InformeEscaneo): string {
    const fecha = informe.fecha.toLocaleDateString("es-AR");
    const hora = informe.fecha.toLocaleTimeString("es-AR");

    let html = `
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <style>
    body { font-family: Arial, sans-serif; color: #333; }
    .header { background: #1e40af; color: white; padding: 20px; border-radius: 5px; margin-bottom: 20px; }
    .stats { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; margin-bottom: 20px; }
    .stat-box { background: #f0f0f0; padding: 15px; border-radius: 5px; text-align: center; }
    .stat-number { font-size: 24px; font-weight: bold; color: #1e40af; }
    .stat-label { font-size: 12px; color: #666; }
    .urgencia-critica { color: #dc2626; font-weight: bold; }
    .urgencia-alta { color: #ea580c; font-weight: bold; }
    .urgencia-media { color: #f59e0b; }
    .urgencia-baja { color: #10b981; }
    table { width: 100%; border-collapse: collapse; margin: 20px 0; }
    th { background: #1e40af; color: white; padding: 10px; text-align: left; }
    td { padding: 10px; border-bottom: 1px solid #ddd; }
    tr:nth-child(even) { background: #f9f9f9; }
    .section { margin: 20px 0; }
    .section-title { font-size: 16px; font-weight: bold; color: #1e40af; margin-bottom: 10px; border-bottom: 2px solid #1e40af; padding-bottom: 5px; }
    .footer { margin-top: 30px; padding-top: 20px; border-top: 1px solid #ddd; font-size: 12px; color: #666; }
  </style>
</head>
<body>
  <div class="header">
    <h1>📋 Informe de Escaneo SIGED</h1>
    <p>Generado: ${fecha} a las ${hora}</p>
  </div>

  <div class="section">
    <div class="section-title">📊 Estadísticas Generales</div>
    <div class="stats">
      <div class="stat-box">
        <div class="stat-number">${informe.totalExpedientes}</div>
        <div class="stat-label">Expedientes Escaneados</div>
      </div>
      <div class="stat-box">
        <div class="stat-number">${informe.totalNovedades}</div>
        <div class="stat-label">Novedades Encontradas</div>
      </div>
      <div class="stat-box">
        <div class="stat-number">${informe.expedientesConNovedades}</div>
        <div class="stat-label">Expedientes Afectados</div>
      </div>
      <div class="stat-box">
        <div class="stat-number">${informe.novedadesPorUrgencia.critica}</div>
        <div class="stat-label">Críticas</div>
      </div>
    </div>
  </div>

  <div class="section">
    <div class="section-title">🎯 Urgencias Identificadas</div>
    <table>
      <tr>
        <th>Nivel</th>
        <th>Cantidad</th>
      </tr>
      <tr>
        <td><span class="urgencia-critica">CRÍTICA</span></td>
        <td>${informe.novedadesPorUrgencia.critica}</td>
      </tr>
      <tr>
        <td><span class="urgencia-alta">ALTA</span></td>
        <td>${informe.novedadesPorUrgencia.alta}</td>
      </tr>
      <tr>
        <td><span class="urgencia-media">MEDIA</span></td>
        <td>${informe.novedadesPorUrgencia.media}</td>
      </tr>
      <tr>
        <td><span class="urgencia-baja">BAJA</span></td>
        <td>${informe.novedadesPorUrgencia.baja}</td>
      </tr>
    </table>
  </div>

  <div class="section">
    <div class="section-title">📝 Detalle de Novedades</div>
    <table>
      <tr>
        <th>Expediente</th>
        <th>Tipo Novedad</th>
        <th>Descripción</th>
        <th>Estrategia</th>
        <th>Escrito</th>
        <th>Urgencia</th>
      </tr>
      ${informe.detalleNovedades
        .map(
          (n) => `
      <tr>
        <td><strong>${n.numeroExpediente}</strong><br/>${n.caratula}</td>
        <td>${n.tipoNovedad}</td>
        <td>${n.descripcion}</td>
        <td>${n.estrategiaRecomendada}</td>
        <td>${n.escritoSugerido}</td>
        <td><span class="urgencia-${n.urgencia}">${n.urgencia.toUpperCase()}</span></td>
      </tr>
      `
        )
        .join("")}
    </table>
  </div>

  <div class="section">
    <div class="section-title">💡 Estrategias Recomendadas</div>
    <pre>${informe.resumenEstrategias}</pre>
  </div>

  <div class="section">
    <div class="section-title">✍️ Próximos Escritos a Presentar</div>
    ${informe.proximosEscritos
      .map(
        (e) => `
    <div style="margin-bottom: 15px; padding: 10px; background: #f9f9f9; border-left: 4px solid #1e40af;">
      <strong>${e.tipo}</strong> (Prioridad: <span class="urgencia-${e.prioridad}">${e.prioridad}</span>)<br/>
      Expedientes: ${e.expedientes.join(", ")}
    </div>
    `
      )
      .join("")}
  </div>

  <div class="footer">
    <p>Este informe fue generado automáticamente por SIGED Gestión Legal.</p>
    <p>Para más información, accede a la plataforma en: https://siged-gestion-legal.manus.space</p>
  </div>
</body>
</html>
    `;

    return html;
  }

  /**
   * Formatea el informe como texto plano para email
   */
  formatearInformeTexto(informe: InformeEscaneo): string {
    const fecha = informe.fecha.toLocaleDateString("es-AR");
    const hora = informe.fecha.toLocaleTimeString("es-AR");

    let texto = `
INFORME DE ESCANEO SIGED
========================
Generado: ${fecha} a las ${hora}

ESTADÍSTICAS GENERALES
======================
- Expedientes Escaneados: ${informe.totalExpedientes}
- Novedades Encontradas: ${informe.totalNovedades}
- Expedientes Afectados: ${informe.expedientesConNovedades}

URGENCIAS IDENTIFICADAS
=======================
- CRÍTICA: ${informe.novedadesPorUrgencia.critica}
- ALTA: ${informe.novedadesPorUrgencia.alta}
- MEDIA: ${informe.novedadesPorUrgencia.media}
- BAJA: ${informe.novedadesPorUrgencia.baja}

DETALLE DE NOVEDADES
====================
${informe.detalleNovedades
  .map(
    (n) => `
Expediente: ${n.numeroExpediente}
Carátula: ${n.caratula}
Tipo: ${n.tipoNovedad}
Descripción: ${n.descripcion}
Estrategia: ${n.estrategiaRecomendada}
Escrito: ${n.escritoSugerido}
Urgencia: ${n.urgencia}
---
`
  )
  .join("")}

ESTRATEGIAS RECOMENDADAS
========================
${informe.resumenEstrategias}

PRÓXIMOS ESCRITOS A PRESENTAR
=============================
${informe.proximosEscritos
  .map((e) => `- ${e.tipo} (${e.expedientes.join(", ")}) - Prioridad: ${e.prioridad}`)
  .join("\n")}

---
Este informe fue generado automáticamente por SIGED Gestión Legal.
    `;

    return texto;
  }
}

export const reportGeneratorService = new ReportGeneratorService();
