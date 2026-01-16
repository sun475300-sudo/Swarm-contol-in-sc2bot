import { eq, desc, and, sql } from "drizzle-orm";
import { drizzle } from "drizzle-orm/mysql2";
import { 
  InsertUser, 
  users, 
  gameSessions, 
  battles, 
  trainingEpisodes, 
  botConfigs, 
  arenaMatches,
  InsertGameSession,
  InsertBattle,
  InsertTrainingEpisode,
  InsertBotConfig,
  InsertArenaMatch
} from "../drizzle/schema";
import { ENV } from './_core/env';

let _db: ReturnType<typeof drizzle> | null = null;

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

// Game Sessions
export async function createGameSession(session: InsertGameSession) {
  const db = await getDb();
  if (!db) throw new Error("Database not available");
  
  const result = await db.insert(gameSessions).values(session);
  return result;
}

export async function getGameSessions(userId: number, limit: number = 50) {
  const db = await getDb();
  if (!db) return [];
  
  return await db
    .select()
    .from(gameSessions)
    .where(eq(gameSessions.userId, userId))
    .orderBy(desc(gameSessions.createdAt))
    .limit(limit);
}

export async function getLatestGameSession(userId: number) {
  const db = await getDb();
  if (!db) return null;
  
  const result = await db
    .select()
    .from(gameSessions)
    .where(and(
      eq(gameSessions.userId, userId),
      eq(gameSessions.result, "InProgress")
    ))
    .orderBy(desc(gameSessions.createdAt))
    .limit(1);
  
  return result.length > 0 ? result[0] : null;
}

export async function updateGameSession(id: number, data: Partial<InsertGameSession>) {
  const db = await getDb();
  if (!db) throw new Error("Database not available");
  
  return await db.update(gameSessions).set(data).where(eq(gameSessions.id, id));
}

// Battles
export async function createBattle(battle: InsertBattle) {
  const db = await getDb();
  if (!db) throw new Error("Database not available");
  
  return await db.insert(battles).values(battle);
}

export async function getBattlesBySession(sessionId: number) {
  const db = await getDb();
  if (!db) return [];
  
  return await db
    .select()
    .from(battles)
    .where(eq(battles.sessionId, sessionId))
    .orderBy(battles.battleTime);
}

// Training Episodes
export async function createTrainingEpisode(episode: InsertTrainingEpisode) {
  const db = await getDb();
  if (!db) throw new Error("Database not available");
  
  return await db.insert(trainingEpisodes).values(episode);
}

export async function getTrainingEpisodes(userId: number, limit: number = 100) {
  const db = await getDb();
  if (!db) return [];
  
  return await db
    .select()
    .from(trainingEpisodes)
    .where(eq(trainingEpisodes.userId, userId))
    .orderBy(desc(trainingEpisodes.episodeNumber))
    .limit(limit);
}

export async function getTrainingStats(userId: number) {
  const db = await getDb();
  if (!db) return null;
  
  const result = await db
    .select({
      totalEpisodes: sql<number>`COUNT(*)`,
      avgReward: sql<number>`AVG(${trainingEpisodes.totalReward})`,
      avgWinRate: sql<number>`AVG(${trainingEpisodes.winRate})`,
      totalGames: sql<number>`SUM(${trainingEpisodes.gamesPlayed})`,
    })
    .from(trainingEpisodes)
    .where(eq(trainingEpisodes.userId, userId));
  
  return result[0] || null;
}

// Bot Configs
export async function createBotConfig(config: InsertBotConfig) {
  const db = await getDb();
  if (!db) throw new Error("Database not available");
  
  // 새로운 설정이 active면 다른 설정들을 비활성화
  if (config.isActive) {
    await db
      .update(botConfigs)
      .set({ isActive: false })
      .where(eq(botConfigs.userId, config.userId));
  }
  
  return await db.insert(botConfigs).values(config);
}

export async function getBotConfigs(userId: number) {
  const db = await getDb();
  if (!db) return [];
  
  return await db
    .select()
    .from(botConfigs)
    .where(eq(botConfigs.userId, userId))
    .orderBy(desc(botConfigs.createdAt));
}

export async function getActiveBotConfig(userId: number) {
  const db = await getDb();
  if (!db) return null;
  
  const result = await db
    .select()
    .from(botConfigs)
    .where(and(
      eq(botConfigs.userId, userId),
      eq(botConfigs.isActive, true)
    ))
    .limit(1);
  
  return result.length > 0 ? result[0] : null;
}

export async function updateBotConfig(id: number, userId: number, data: Partial<InsertBotConfig>) {
  const db = await getDb();
  if (!db) throw new Error("Database not available");
  
  // active 상태를 변경하는 경우
  if (data.isActive === true) {
    await db
      .update(botConfigs)
      .set({ isActive: false })
      .where(eq(botConfigs.userId, userId));
  }
  
  return await db
    .update(botConfigs)
    .set(data)
    .where(and(
      eq(botConfigs.id, id),
      eq(botConfigs.userId, userId)
    ));
}

export async function deleteBotConfig(id: number, userId: number) {
  const db = await getDb();
  if (!db) throw new Error("Database not available");
  
  return await db
    .delete(botConfigs)
    .where(and(
      eq(botConfigs.id, id),
      eq(botConfigs.userId, userId)
    ));
}

// Arena Matches
export async function createArenaMatch(match: InsertArenaMatch) {
  const db = await getDb();
  if (!db) throw new Error("Database not available");
  
  return await db.insert(arenaMatches).values(match);
}

export async function getArenaMatches(userId: number, limit: number = 50) {
  const db = await getDb();
  if (!db) return [];
  
  return await db
    .select()
    .from(arenaMatches)
    .where(eq(arenaMatches.userId, userId))
    .orderBy(desc(arenaMatches.createdAt))
    .limit(limit);
}

export async function getArenaStats(userId: number) {
  const db = await getDb();
  if (!db) return null;
  
  const result = await db
    .select({
      totalMatches: sql<number>`COUNT(*)`,
      wins: sql<number>`SUM(CASE WHEN ${arenaMatches.result} = 'Win' THEN 1 ELSE 0 END)`,
      losses: sql<number>`SUM(CASE WHEN ${arenaMatches.result} = 'Loss' THEN 1 ELSE 0 END)`,
      currentElo: sql<number>`MAX(${arenaMatches.elo})`,
      currentRanking: sql<number>`MAX(${arenaMatches.ranking})`,
    })
    .from(arenaMatches)
    .where(eq(arenaMatches.userId, userId));
  
  return result[0] || null;
}

// Game Statistics
export async function getGameStats(userId: number) {
  const db = await getDb();
  if (!db) return null;
  
  const result = await db
    .select({
      totalGames: sql<number>`COUNT(*)`,
      wins: sql<number>`SUM(CASE WHEN ${gameSessions.result} = 'Victory' THEN 1 ELSE 0 END)`,
      losses: sql<number>`SUM(CASE WHEN ${gameSessions.result} = 'Defeat' THEN 1 ELSE 0 END)`,
      avgDuration: sql<number>`AVG(${gameSessions.duration})`,
      totalUnitsKilled: sql<number>`SUM(${gameSessions.unitsKilled})`,
      totalUnitsLost: sql<number>`SUM(${gameSessions.unitsLost})`,
    })
    .from(gameSessions)
    .where(eq(gameSessions.userId, userId));
  
  return result[0] || null;
}
