import { eq, and } from "drizzle-orm";
import { drizzle } from "drizzle-orm/mysql2";
import { InsertUser, users, expedientes, notas, escritos, alertas, sigedCredentials, sigedNotificaciones, InsertSigedCredentials, InsertSigedNotificaciones } from "../drizzle/schema";
import { ENV } from './_core/env';
import { encryptText, decryptText } from "./services/encryptionService";

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
// SIGED CREDENTIALS
// ============================================================================

export async function saveSigedCredentials(
  userId: number,
  username: string,
  password: string,
  notificationEmail: string
): Promise<void> {
  const db = await getDb();
  if (!db) {
    throw new Error("Database not available");
  }

  const encryptedUsername = encryptText(username);
  const encryptedPassword = encryptText(password);

  const existing = await db
    .select()
    .from(sigedCredentials)
    .where(eq(sigedCredentials.userId, userId))
    .limit(1);

  if (existing.length > 0) {
    await db
      .update(sigedCredentials)
      .set({
        username: encryptedUsername,
        password: encryptedPassword,
        notificationEmail,
        updatedAt: new Date(),
      })
      .where(eq(sigedCredentials.userId, userId));
  } else {
    await db.insert(sigedCredentials).values({
      userId,
      username: encryptedUsername,
      password: encryptedPassword,
      notificationEmail,
      isActive: 1,
    });
  }
}

export async function getSigedCredentials(userId: number) {
  const db = await getDb();
  if (!db) {
    throw new Error("Database not available");
  }

  const result = await db
    .select()
    .from(sigedCredentials)
    .where(and(eq(sigedCredentials.userId, userId), eq(sigedCredentials.isActive, 1)))
    .limit(1);

  if (result.length === 0) {
    return null;
  }

  const creds = result[0];
  return {
    ...creds,
    username: decryptText(creds.username),
    password: decryptText(creds.password),
  };
}

export async function updateSigedSyncStatus(
  userId: number,
  success: boolean,
  error?: string
): Promise<void> {
  const db = await getDb();
  if (!db) {
    throw new Error("Database not available");
  }

  const updateData: any = {
    updatedAt: new Date(),
  };

  if (success) {
    updateData.lastSuccessfulSync = new Date();
    updateData.lastSyncError = null;
  } else {
    updateData.lastSyncError = error || "Unknown error";
  }

  await db
    .update(sigedCredentials)
    .set(updateData)
    .where(eq(sigedCredentials.userId, userId));
}

// ============================================================================
// SIGED NOTIFICACIONES
// ============================================================================

export async function saveSigedNotificacion(
  data: InsertSigedNotificaciones
): Promise<void> {
  const db = await getDb();
  if (!db) {
    throw new Error("Database not available");
  }

  await db.insert(sigedNotificaciones).values(data);
}

export async function getSigedNotificacionesPorUsuario(userId: number, leidas = false) {
  const db = await getDb();
  if (!db) {
    throw new Error("Database not available");
  }

  const result = await db
    .select()
    .from(sigedNotificaciones)
    .where(
      and(
        eq(sigedNotificaciones.userId, userId),
        eq(sigedNotificaciones.leida, leidas ? 1 : 0)
      )
    );

  return result;
}

export async function marcarNotificacionComoLeida(notificacionId: number): Promise<void> {
  const db = await getDb();
  if (!db) {
    throw new Error("Database not available");
  }

  await db
    .update(sigedNotificaciones)
    .set({ leida: 1, updatedAt: new Date() })
    .where(eq(sigedNotificaciones.id, notificacionId));
}

// TODO: add feature queries here as your schema grows.


// ============================================================================
// EXPEDIENTES
// ============================================================================

export async function getExpedientesByUserId(userId: number) {
  const db = await getDb();
  if (!db) return [];
  return db.select().from(expedientes).where(eq(expedientes.userId, userId));
}

export async function getExpedienteById(id: number) {
  const db = await getDb();
  if (!db) return null;
  const result = await db.select().from(expedientes).where(eq(expedientes.id, id)).limit(1);
  return result.length > 0 ? result[0] : null;
}

export async function createExpediente(data: any) {
  const db = await getDb();
  if (!db) throw new Error("Database not available");
  await db.insert(expedientes).values(data);
}

export async function updateExpediente(id: number, data: any) {
  const db = await getDb();
  if (!db) throw new Error("Database not available");
  await db.update(expedientes).set(data).where(eq(expedientes.id, id));
}

// ============================================================================
// NOTAS
// ============================================================================

export async function getNotasByExpedienteId(expedienteId: number) {
  const db = await getDb();
  if (!db) return [];
  return db.select().from(notas).where(eq(notas.expedienteId, expedienteId));
}

export async function createNota(data: any) {
  const db = await getDb();
  if (!db) throw new Error("Database not available");
  await db.insert(notas).values(data);
}

export async function deleteNota(id: number) {
  const db = await getDb();
  if (!db) throw new Error("Database not available");
  await db.delete(notas).where(eq(notas.id, id));
}

// ============================================================================
// ALERTAS
// ============================================================================

export async function getAlertasByUserId(userId: number) {
  const db = await getDb();
  if (!db) return [];
  return db.select().from(alertas).where(eq(alertas.userId, userId));
}

export async function createAlerta(data: any) {
  const db = await getDb();
  if (!db) throw new Error("Database not available");
  await db.insert(alertas).values(data);
}

export async function updateAlerta(id: number, data: any) {
  const db = await getDb();
  if (!db) throw new Error("Database not available");
  await db.update(alertas).set(data).where(eq(alertas.id, id));
}

export async function deleteAlerta(id: number) {
  const db = await getDb();
  if (!db) throw new Error("Database not available");
  await db.delete(alertas).where(eq(alertas.id, id));
}

// ============================================================================
// ESCRITOS
// ============================================================================

export async function getEscritosByExpedienteId(expedienteId: number) {
  const db = await getDb();
  if (!db) return [];
  return db.select().from(escritos).where(eq(escritos.expedienteId, expedienteId));
}

export async function createEscrito(data: any) {
  const db = await getDb();
  if (!db) throw new Error("Database not available");
  await db.insert(escritos).values(data);
}

export async function updateEscrito(id: number, data: any) {
  const db = await getDb();
  if (!db) throw new Error("Database not available");
  await db.update(escritos).set(data).where(eq(escritos.id, id));
}


export async function deleteExpediente(id: number) {
  const db = await getDb();
  if (!db) throw new Error("Database not available");
  await db.delete(expedientes).where(eq(expedientes.id, id));
}

export async function getEscritosByUserId(userId: number) {
  const db = await getDb();
  if (!db) return [];
  return db.select().from(escritos).where(eq(escritos.userId, userId));
}

export async function getEscritoById(id: number) {
  const db = await getDb();
  if (!db) return null;
  const result = await db.select().from(escritos).where(eq(escritos.id, id)).limit(1);
  return result.length > 0 ? result[0] : null;
}

export async function deleteEscrito(id: number) {
  const db = await getDb();
  if (!db) throw new Error("Database not available");
  await db.delete(escritos).where(eq(escritos.id, id));
}
