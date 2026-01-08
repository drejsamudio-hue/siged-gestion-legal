import { COOKIE_NAME } from "@shared/const";
import { getSessionCookieOptions } from "./_core/cookies";
import { systemRouter } from "./_core/systemRouter";
import { publicProcedure, protectedProcedure, router } from "./_core/trpc";
import { z } from "zod";
import * as db from "./db";

export const appRouter = router({
  system: systemRouter,
  auth: router({
    me: publicProcedure.query(opts => opts.ctx.user),
    logout: publicProcedure.mutation(({ ctx }) => {
      const cookieOptions = getSessionCookieOptions(ctx.req);
      ctx.res.clearCookie(COOKIE_NAME, { ...cookieOptions, maxAge: -1 });
      return {
        success: true,
      } as const;
    }),
  }),

  expedientes: router({
    list: protectedProcedure.query(({ ctx }) =>
      db.getExpedientesByUserId(ctx.user.id)
    ),
    get: protectedProcedure
      .input(z.object({ id: z.number() }))
      .query(({ input }) => db.getExpedienteById(input.id)),
    create: protectedProcedure
      .input(
        z.object({
          numero: z.string(),
          caratula: z.string(),
          dependencia: z.string(),
          tipoProc: z.enum(["civil_comercial", "laboral", "familia", "penal", "administrativo", "otro"]),
          estadoProcesal: z.enum(["inicio", "demanda_contestada", "prueba", "alegatos", "sentencia", "recurso", "ejecucion", "finalizado", "otro"]),
          ultimoMovimiento: z.string().optional(),
          fechaUltimoMovimiento: z.date().optional(),
          proximoPlazo: z.date().optional(),
        })
      )
      .mutation(({ ctx, input }) =>
        db.createExpediente({
          ...input,
          userId: ctx.user.id,
          prioridad: "media",
        })
      ),
    update: protectedProcedure
      .input(
        z.object({
          id: z.number(),
          numero: z.string().optional(),
          caratula: z.string().optional(),
          dependencia: z.string().optional(),
          estadoProcesal: z.enum(["inicio", "demanda_contestada", "prueba", "alegatos", "sentencia", "recurso", "ejecucion", "finalizado", "otro"]).optional(),
          ultimoMovimiento: z.string().optional(),
          fechaUltimoMovimiento: z.date().optional(),
          proximoPlazo: z.date().optional(),
          notas: z.string().optional(),
        })
      )
      .mutation(({ input }) => {
        const { id, ...data } = input;
        return db.updateExpediente(id, data);
      }),
    delete: protectedProcedure
      .input(z.object({ id: z.number() }))
      .mutation(({ input }) => db.deleteExpediente(input.id)),
  }),

  escritos: router({
    list: protectedProcedure.query(({ ctx }) =>
      db.getEscritosByUserId(ctx.user.id)
    ),
    getByExpediente: protectedProcedure
      .input(z.object({ expedienteId: z.number() }))
      .query(({ input }) => db.getEscritosByExpedienteId(input.expedienteId)),
    get: protectedProcedure
      .input(z.object({ id: z.number() }))
      .query(({ input }) => db.getEscritoById(input.id)),
    create: protectedProcedure
      .input(
        z.object({
          expedienteId: z.number().optional(),
          titulo: z.string(),
          tipo: z.enum(["habilitacion_feria", "apelacion", "reposicion", "queja", "medida_cautelar", "medida_autosatisfactiva", "otro"]),
          contenido: z.string(),
        })
      )
      .mutation(({ ctx, input }) =>
        db.createEscrito({
          ...input,
          userId: ctx.user.id,
          estado: "borrador",
        })
      ),
    update: protectedProcedure
      .input(
        z.object({
          id: z.number(),
          titulo: z.string().optional(),
          contenido: z.string().optional(),
          estado: z.enum(["borrador", "completado", "presentado"]).optional(),
          fechaPresentacion: z.date().optional(),
          urlPDF: z.string().optional(),
          urlDOCX: z.string().optional(),
        })
      )
      .mutation(({ input }) => {
        const { id, ...data } = input;
        return db.updateEscrito(id, data);
      }),
    delete: protectedProcedure
      .input(z.object({ id: z.number() }))
      .mutation(({ input }) => db.deleteEscrito(input.id)),
  }),

  notas: router({
    list: protectedProcedure
      .input(z.object({ expedienteId: z.number() }))
      .query(({ input }) => db.getNotasByExpedienteId(input.expedienteId)),
    create: protectedProcedure
      .input(
        z.object({
          expedienteId: z.number(),
          contenido: z.string(),
          tipo: z.enum(["estrategia", "riesgo", "oportunidad", "observacion"]),
        })
      )
      .mutation(({ ctx, input }) =>
        db.createNota({
          ...input,
          userId: ctx.user.id,
        })
      ),
    delete: protectedProcedure
      .input(z.object({ id: z.number() }))
      .mutation(({ input }) => db.deleteNota(input.id)),
  }),

  alertas: router({
    list: protectedProcedure.query(({ ctx }) =>
      db.getAlertasByUserId(ctx.user.id)
    ),
    create: protectedProcedure
      .input(
        z.object({
          expedienteId: z.number(),
          titulo: z.string(),
          descripcion: z.string().optional(),
          tipo: z.enum(["vencimiento_plazo", "audiencia", "pericia", "vencimiento_recurso", "otro"]),
          fechaAlerta: z.date(),
        })
      )
      .mutation(({ ctx, input }) =>
        db.createAlerta({
          ...input,
          userId: ctx.user.id,
          enviado: false,
        })
      ),
    update: protectedProcedure
      .input(
        z.object({
          id: z.number(),
          enviado: z.boolean().optional(),
          fechaEnvio: z.date().optional(),
        })
      )
      .mutation(({ input }) => {
        const { id, ...data } = input;
        return db.updateAlerta(id, data);
      }),
  }),
});

export type AppRouter = typeof appRouter;
