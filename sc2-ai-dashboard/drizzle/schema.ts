import { int, mysqlEnum, mysqlTable, text, timestamp, varchar, float, boolean } from "drizzle-orm/mysql-core";

/**
 * Core user table backing auth flow.
 */
export const users = mysqlTable("users", {
  id: int("id").autoincrement().primaryKey(),
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

/**
 * Game sessions - 각 게임 세션의 정보
 */
export const gameSessions = mysqlTable("game_sessions", {
  id: int("id").autoincrement().primaryKey(),
  userId: int("userId").notNull(),
  mapName: varchar("mapName", { length: 255 }).notNull(),
  enemyRace: mysqlEnum("enemyRace", ["Terran", "Protoss", "Zerg", "Random"]).notNull(),
  difficulty: varchar("difficulty", { length: 50 }).notNull(),
  result: mysqlEnum("result", ["Victory", "Defeat", "InProgress"]).default("InProgress").notNull(),
  gamePhase: varchar("gamePhase", { length: 50 }),
  duration: int("duration"), // 게임 시간 (초)
  finalSupply: int("finalSupply"),
  finalMinerals: int("finalMinerals"),
  finalGas: int("finalGas"),
  unitsKilled: int("unitsKilled"),
  unitsLost: int("unitsLost"),
  createdAt: timestamp("createdAt").defaultNow().notNull(),
  updatedAt: timestamp("updatedAt").defaultNow().onUpdateNow().notNull(),
});

export type GameSession = typeof gameSessions.$inferSelect;
export type InsertGameSession = typeof gameSessions.$inferInsert;

/**
 * Battles - 전투 기록
 */
export const battles = mysqlTable("battles", {
  id: int("id").autoincrement().primaryKey(),
  sessionId: int("sessionId").notNull(),
  battleTime: int("battleTime").notNull(), // 게임 내 시간 (초)
  location: varchar("location", { length: 255 }),
  unitsEngaged: int("unitsEngaged"),
  unitsKilled: int("unitsKilled"),
  unitsLost: int("unitsLost"),
  damageDealt: float("damageDealt"),
  damageTaken: float("damageTaken"),
  result: mysqlEnum("result", ["Win", "Loss", "Retreat"]).notNull(),
  createdAt: timestamp("createdAt").defaultNow().notNull(),
});

export type Battle = typeof battles.$inferSelect;
export type InsertBattle = typeof battles.$inferInsert;

/**
 * Training episodes - 강화학습 에피소드
 */
export const trainingEpisodes = mysqlTable("training_episodes", {
  id: int("id").autoincrement().primaryKey(),
  userId: int("userId").notNull(),
  episodeNumber: int("episodeNumber").notNull(),
  totalReward: float("totalReward").notNull(),
  averageReward: float("averageReward"),
  winRate: float("winRate"),
  gamesPlayed: int("gamesPlayed").notNull(),
  learningRate: float("learningRate"),
  epsilon: float("epsilon"),
  loss: float("loss"),
  notes: text("notes"),
  createdAt: timestamp("createdAt").defaultNow().notNull(),
});

export type TrainingEpisode = typeof trainingEpisodes.$inferSelect;
export type InsertTrainingEpisode = typeof trainingEpisodes.$inferInsert;

/**
 * Bot configurations - 봇 설정
 */
export const botConfigs = mysqlTable("bot_configs", {
  id: int("id").autoincrement().primaryKey(),
  userId: int("userId").notNull(),
  name: varchar("name", { length: 255 }).notNull(),
  strategy: mysqlEnum("strategy", ["Aggressive", "Defensive", "Balanced", "Economic", "Rush"]).default("Balanced").notNull(),
  buildOrder: text("buildOrder"), // JSON string
  isActive: boolean("isActive").default(false).notNull(),
  description: text("description"),
  createdAt: timestamp("createdAt").defaultNow().notNull(),
  updatedAt: timestamp("updatedAt").defaultNow().onUpdateNow().notNull(),
});

export type BotConfig = typeof botConfigs.$inferSelect;
export type InsertBotConfig = typeof botConfigs.$inferInsert;

/**
 * AI Arena matches - AI Arena 경기 기록
 */
export const arenaMatches = mysqlTable("arena_matches", {
  id: int("id").autoincrement().primaryKey(),
  userId: int("userId").notNull(),
  matchId: varchar("matchId", { length: 255 }),
  opponentName: varchar("opponentName", { length: 255 }),
  opponentRace: mysqlEnum("opponentRace", ["Terran", "Protoss", "Zerg"]),
  mapName: varchar("mapName", { length: 255 }),
  result: mysqlEnum("result", ["Win", "Loss", "Tie"]).notNull(),
  ranking: int("ranking"),
  elo: int("elo"),
  replayUrl: varchar("replayUrl", { length: 512 }),
  createdAt: timestamp("createdAt").defaultNow().notNull(),
});

export type ArenaMatch = typeof arenaMatches.$inferSelect;
export type InsertArenaMatch = typeof arenaMatches.$inferInsert;
