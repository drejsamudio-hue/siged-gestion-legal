import { int, mysqlEnum, mysqlTable, text, timestamp, varchar, decimal, boolean, json } from "drizzle-orm/mysql-core";
import { relations } from "drizzle-orm";

/**
 * Core user table backing auth flow.
 * Extend this file with additional tables as your product grows.
 * Columns use camelCase to match both database fields and generated types.
 */
export const users = mysqlTable("users", {
  /**
   * Surrogate primary key. Auto-incremented numeric value managed by the database.
   * Use this for relations between tables.
   */
  id: int("id").autoincrement().primaryKey(),
  /** Manus OAuth identifier (openId) returned from the OAuth callback. Unique per user. */
  openId: varchar("openId", { length: 64 }).notNull().unique(),
  name: text("name"),
  email: varchar("email", { length: 320 }),
  loginMethod: varchar("loginMethod", { length: 64 }),
  role: mysqlEnum("role", ["user", "admin"]).default("user").notNull(),
  createdAt: timestamp("createdAt").defaultNow().notNull(),
  updatedAt: timestamp("updatedAt").defaultNow().onUpdateNow().notNull(),
  lastSignedIn: timestamp("lastSignedIn").defaultNow().notNull(),
});

export type User = typeof users.$inferSelect;
export type InsertUser = typeof users.$inferInsert;

// ============================================================================
// EXPEDIENTES (Cases)
// ============================================================================

export const expedientes = mysqlTable("expedientes", {
  id: int("id").autoincrement().primaryKey(),
  userId: int("userId").notNull(),
  numero: varchar("numero", { length: 50 }).notNull(), // e.g., "117906/2025"
  caratula: text("caratula").notNull(), // Case name/title
  dependencia: varchar("dependencia", { length: 255 }).notNull(), // Court/Department
  tipoProc: mysqlEnum("tipoProc", [
    "civil_comercial",
    "laboral",
    "familia",
    "penal",
    "administrativo",
    "otro",
  ]).notNull(),
  estadoProcesal: mysqlEnum("estadoProcesal", [
    "inicio",
    "demanda_contestada",
    "prueba",
    "alegatos",
    "sentencia",
    "recurso",
    "ejecucion",
    "finalizado",
    "otro",
  ]).notNull(),
  prioridad: mysqlEnum("prioridad", ["alta_feria", "media", "baja"]).default("media").notNull(),
  ultimoMovimiento: text("ultimoMovimiento"), // Last procedural movement
  fechaUltimoMovimiento: timestamp("fechaUltimoMovimiento"),
  proximoPlazo: timestamp("proximoPlazo"), // Next critical deadline
  notas: text("notas"), // General notes
  archivoUrl: varchar("archivoUrl", { length: 500 }), // S3 URL for case documents
  createdAt: timestamp("createdAt").defaultNow().notNull(),
  updatedAt: timestamp("updatedAt").defaultNow().onUpdateNow().notNull(),
});

export type Expediente = typeof expedientes.$inferSelect;
export type InsertExpediente = typeof expedientes.$inferInsert;

// ============================================================================
// NOTAS Y OBSERVACIONES (Case Notes)
// ============================================================================

export const notas = mysqlTable("notas", {
  id: int("id").autoincrement().primaryKey(),
  expedienteId: int("expedienteId").notNull(),
  userId: int("userId").notNull(),
  contenido: text("contenido").notNull(),
  tipo: mysqlEnum("tipo", ["estrategia", "riesgo", "oportunidad", "observacion"]).default("observacion").notNull(),
  createdAt: timestamp("createdAt").defaultNow().notNull(),
  updatedAt: timestamp("updatedAt").defaultNow().onUpdateNow().notNull(),
});

export type Nota = typeof notas.$inferSelect;
export type InsertNota = typeof notas.$inferInsert;

// ============================================================================
// ESCRITOS GUARDADOS (Saved Legal Documents)
// ============================================================================

export const escritos = mysqlTable("escritos", {
  id: int("id").autoincrement().primaryKey(),
  expedienteId: int("expedienteId"),
  userId: int("userId").notNull(),
  titulo: varchar("titulo", { length: 255 }).notNull(),
  tipo: mysqlEnum("tipo", [
    "habilitacion_feria",
    "apelacion",
    "reposicion",
    "queja",
    "medida_cautelar",
    "medida_autosatisfactiva",
    "otro",
  ]).notNull(),
  contenido: text("contenido").notNull(),
  estado: mysqlEnum("estado", ["borrador", "completado", "presentado"]).default("borrador").notNull(),
  fechaPresentacion: timestamp("fechaPresentacion"),
  urlPDF: varchar("urlPDF", { length: 500 }), // S3 URL for exported PDF
  urlDOCX: varchar("urlDOCX", { length: 500 }), // S3 URL for exported DOCX
  createdAt: timestamp("createdAt").defaultNow().notNull(),
  updatedAt: timestamp("updatedAt").defaultNow().onUpdateNow().notNull(),
});

export type Escrito = typeof escritos.$inferSelect;
export type InsertEscrito = typeof escritos.$inferInsert;

// ============================================================================
// ALERTAS (Alerts)
// ============================================================================

export const alertas = mysqlTable("alertas", {
  id: int("id").autoincrement().primaryKey(),
  expedienteId: int("expedienteId").notNull(),
  userId: int("userId").notNull(),
  titulo: varchar("titulo", { length: 255 }).notNull(),
  descripcion: text("descripcion"),
  tipo: mysqlEnum("tipo", [
    "vencimiento_plazo",
    "audiencia",
    "pericia",
    "vencimiento_recurso",
    "otro",
  ]).notNull(),
  fechaAlerta: timestamp("fechaAlerta").notNull(),
  enviado: boolean("enviado").default(false).notNull(),
  fechaEnvio: timestamp("fechaEnvio"),
  createdAt: timestamp("createdAt").defaultNow().notNull(),
  updatedAt: timestamp("updatedAt").defaultNow().onUpdateNow().notNull(),
});

export type Alerta = typeof alertas.$inferSelect;
export type InsertAlerta = typeof alertas.$inferInsert;

// ============================================================================
// REFERENCIAS LEGALES (Legal References)
// ============================================================================

export const referenciasLegales = mysqlTable("referencias_legales", {
  id: int("id").autoincrement().primaryKey(),
  titulo: varchar("titulo", { length: 255 }).notNull(),
  tipo: mysqlEnum("tipo", [
    "codigo_civil",
    "codigo_penal",
    "codigo_procesal_civil",
    "codigo_procesal_penal",
    "rpj",
    "jurisprudencia",
  ]).notNull(),
  articulo: varchar("articulo", { length: 50 }),
  contenido: text("contenido").notNull(),
  fuente: varchar("fuente", { length: 255 }),
  createdAt: timestamp("createdAt").defaultNow().notNull(),
});

export type ReferenciaLegal = typeof referenciasLegales.$inferSelect;
export type InsertReferenciaLegal = typeof referenciasLegales.$inferInsert;

// ============================================================================
// CONVERSACIONES CON CHATBOT (Chatbot Conversations)
// ============================================================================

export const conversaciones = mysqlTable("conversaciones", {
  id: int("id").autoincrement().primaryKey(),
  expedienteId: int("expedienteId"),
  userId: int("userId").notNull(),
  titulo: varchar("titulo", { length: 255 }),
  mensajes: json("mensajes"), // Array of {role, content} objects
  createdAt: timestamp("createdAt").defaultNow().notNull(),
  updatedAt: timestamp("updatedAt").defaultNow().onUpdateNow().notNull(),
});

export type Conversacion = typeof conversaciones.$inferSelect;
export type InsertConversacion = typeof conversaciones.$inferInsert;

// ============================================================================
// RELACIONES
// ============================================================================

export const expedientesRelations = relations(expedientes, ({ many }) => ({
  notas: many(notas),
  escritos: many(escritos),
  alertas: many(alertas),
  conversaciones: many(conversaciones),
}));

export const notasRelations = relations(notas, ({ one }) => ({
  expediente: one(expedientes, {
    fields: [notas.expedienteId],
    references: [expedientes.id],
  }),
}));

export const escritosRelations = relations(escritos, ({ one }) => ({
  expediente: one(expedientes, {
    fields: [escritos.expedienteId],
    references: [expedientes.id],
  }),
}));

export const alertasRelations = relations(alertas, ({ one }) => ({
  expediente: one(expedientes, {
    fields: [alertas.expedienteId],
    references: [expedientes.id],
  }),
}));

export const conversacionesRelations = relations(conversaciones, ({ one }) => ({
  expediente: one(expedientes, {
    fields: [conversaciones.expedienteId],
    references: [expedientes.id],
  }),
}));