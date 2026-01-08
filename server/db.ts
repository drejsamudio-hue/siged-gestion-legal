import { eq } from "drizzle-orm";
import { drizzle } from "drizzle-orm/mysql2";
import {
  InsertUser,
  users,
  expedientes,
  InsertExpediente,
  notas,
  InsertNota,
  escritos,
  InsertEscrito,
  alertas,
  InsertAlerta,
  referenciasLegales,
  conversaciones,
  InsertConversacion,
} from "../drizzle/schema";
import { ENV } from './_core/env';

let _db: ReturnType<typeof drizzle> | null = null;

// Lazily create the drizzle instance so local tooling can run without a DB.
export async function getDb() {
  if (!_db && process.env.DATABASE_URL) {
    try {
      _db = drizzle(process.env.DATABASE_URL);
    } catch (error) {
      console.warn("[Database] Failed to connect:", error);
      _db = null;
    }
  }
  return _db;
}

export async function upsertUser(user: InsertUser): Promise<void> {
  if (!user.openId) {
    throw new Error("User openId is required for upsert");
  }

  const db = await getDb();
  if (!db) {
    console.warn("[Database] Cannot upsert user: database not available");
    return;
  }

  try {
    const values: InsertUser = {
      openId: user.openId,
    };
    const updateSet: Record<string, unknown> = {};

    const textFields = ["name", "email", "loginMethod"] as const;
    type TextField = (typeof textFields)[number];

    const assignNullable = (field: TextField) => {
      const value = user[field];
      if (value === undefined) return;
      const normalized = value ?? null;
      values[field] = normalized;
      updateSet[field] = normalized;
    };

    textFields.forEach(assignNullable);

    if (user.lastSignedIn !== undefined) {
      values.lastSignedIn = user.lastSignedIn;
      updateSet.lastSignedIn = user.lastSignedIn;
    }
    if (user.role !== undefined) {
      values.role = user.role;
      updateSet.role = user.role;
    } else if (user.openId === ENV.ownerOpenId) {
      values.role = 'admin';
      updateSet.role = 'admin';
    }

    if (!values.lastSignedIn) {
      values.lastSignedIn = new Date();
    }

    if (Object.keys(updateSet).length === 0) {
      updateSet.lastSignedIn = new Date();
    }

    await db.insert(users).values(values).onDuplicateKeyUpdate({
      set: updateSet,
    });
  } catch (error) {
    console.error("[Database] Failed to upsert user:", error);
    throw error;
  }
}

export async function getUserByOpenId(openId: string) {
  const db = await getDb();
  if (!db) {
    console.warn("[Database] Cannot get user: database not available");
    return undefined;
  }

  const result = await db.select().from(users).where(eq(users.openId, openId)).limit(1);

  return result.length > 0 ? result[0] : undefined;
}

// ============================================================================
// EXPEDIENTES QUERIES
// ============================================================================

export async function getExpedientesByUserId(userId: number) {
  const db = await getDb();
  if (!db) return [];
  return db.select().from(expedientes).where(eq(expedientes.userId, userId));
}

export async function getExpedienteById(id: number) {
  const db = await getDb();
  if (!db) return undefined;
  const result = await db.select().from(expedientes).where(eq(expedientes.id, id)).limit(1);
  return result.length > 0 ? result[0] : undefined;
}

export async function createExpediente(data: InsertExpediente) {
  const db = await getDb();
  if (!db) throw new Error("Database not available");
  const result = await db.insert(expedientes).values(data);
  return result;
}

export async function updateExpediente(id: number, data: Partial<InsertExpediente>) {
  const db = await getDb();
  if (!db) throw new Error("Database not available");
  return db.update(expedientes).set(data).where(eq(expedientes.id, id));
}

export async function deleteExpediente(id: number) {
  const db = await getDb();
  if (!db) throw new Error("Database not available");
  return db.delete(expedientes).where(eq(expedientes.id, id));
}

// ============================================================================
// NOTAS QUERIES
// ============================================================================

export async function getNotasByExpedienteId(expedienteId: number) {
  const db = await getDb();
  if (!db) return [];
  return db.select().from(notas).where(eq(notas.expedienteId, expedienteId));
}

export async function createNota(data: InsertNota) {
  const db = await getDb();
  if (!db) throw new Error("Database not available");
  return db.insert(notas).values(data);
}

export async function deleteNota(id: number) {
  const db = await getDb();
  if (!db) throw new Error("Database not available");
  return db.delete(notas).where(eq(notas.id, id));
}

// ============================================================================
// ESCRITOS QUERIES
// ============================================================================

export async function getEscritosByUserId(userId: number) {
  const db = await getDb();
  if (!db) return [];
  return db.select().from(escritos).where(eq(escritos.userId, userId));
}

export async function getEscritosByExpedienteId(expedienteId: number) {
  const db = await getDb();
  if (!db) return [];
  return db.select().from(escritos).where(eq(escritos.expedienteId, expedienteId));
}

export async function getEscritoById(id: number) {
  const db = await getDb();
  if (!db) return undefined;
  const result = await db.select().from(escritos).where(eq(escritos.id, id)).limit(1);
  return result.length > 0 ? result[0] : undefined;
}

export async function createEscrito(data: InsertEscrito) {
  const db = await getDb();
  if (!db) throw new Error("Database not available");
  return db.insert(escritos).values(data);
}

export async function updateEscrito(id: number, data: Partial<InsertEscrito>) {
  const db = await getDb();
  if (!db) throw new Error("Database not available");
  return db.update(escritos).set(data).where(eq(escritos.id, id));
}

export async function deleteEscrito(id: number) {
  const db = await getDb();
  if (!db) throw new Error("Database not available");
  return db.delete(escritos).where(eq(escritos.id, id));
}

// ============================================================================
// ALERTAS QUERIES
// ============================================================================

export async function getAlertasByUserId(userId: number) {
  const db = await getDb();
  if (!db) return [];
  return db.select().from(alertas).where(eq(alertas.userId, userId));
}

export async function getAlertasPendientes() {
  const db = await getDb();
  if (!db) return [];
  return db.select().from(alertas).where(eq(alertas.enviado, false));
}

export async function createAlerta(data: InsertAlerta) {
  const db = await getDb();
  if (!db) throw new Error("Database not available");
  return db.insert(alertas).values(data);
}

export async function updateAlerta(id: number, data: Partial<InsertAlerta>) {
  const db = await getDb();
  if (!db) throw new Error("Database not available");
  return db.update(alertas).set(data).where(eq(alertas.id, id));
}

// ============================================================================
// REFERENCIAS LEGALES QUERIES
// ============================================================================

export async function getReferenciasLegales() {
  const db = await getDb();
  if (!db) return [];
  return db.select().from(referenciasLegales);
}

export async function getReferenciasLegalesByTipo(tipoRef: "codigo_civil" | "codigo_penal" | "codigo_procesal_civil" | "codigo_procesal_penal" | "rpj" | "jurisprudencia") {
  const db = await getDb();
  if (!db) return [];
  return db.select().from(referenciasLegales).where(eq(referenciasLegales.tipo, tipoRef));
}

// ============================================================================
// CONVERSACIONES QUERIES
// ============================================================================

export async function getConversacionesByUserId(userId: number) {
  const db = await getDb();
  if (!db) return [];
  return db.select().from(conversaciones).where(eq(conversaciones.userId, userId));
}

export async function getConversacionById(id: number) {
  const db = await getDb();
  if (!db) return undefined;
  const result = await db.select().from(conversaciones).where(eq(conversaciones.id, id)).limit(1);
  return result.length > 0 ? result[0] : undefined;
}

export async function createConversacion(data: InsertConversacion) {
  const db = await getDb();
  if (!db) throw new Error("Database not available");
  return db.insert(conversaciones).values(data);
}

export async function updateConversacion(id: number, data: Partial<InsertConversacion>) {
  const db = await getDb();
  if (!db) throw new Error("Database not available");
  return db.update(conversaciones).set(data).where(eq(conversaciones.id, id));
}
