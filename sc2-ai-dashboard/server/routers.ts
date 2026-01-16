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

  // Game Sessions
  game: router({
    // 현재 진행 중인 게임 세션 가져오기
    getCurrentSession: protectedProcedure.query(async ({ ctx }) => {
      return await db.getLatestGameSession(ctx.user.id);
    }),

    // 게임 세션 목록
    getSessions: protectedProcedure
      .input(z.object({ limit: z.number().optional() }))
      .query(async ({ ctx, input }) => {
        return await db.getGameSessions(ctx.user.id, input.limit);
      }),

    // 게임 세션 생성
    createSession: protectedProcedure
      .input(z.object({
        mapName: z.string(),
        enemyRace: z.enum(["Terran", "Protoss", "Zerg", "Random"]),
        difficulty: z.string(),
      }))
      .mutation(async ({ ctx, input }) => {
        return await db.createGameSession({
          userId: ctx.user.id,
          ...input,
        });
      }),

    // 게임 세션 업데이트
    updateSession: protectedProcedure
      .input(z.object({
        id: z.number(),
        result: z.enum(["Victory", "Defeat", "InProgress"]).optional(),
        gamePhase: z.string().optional(),
        duration: z.number().optional(),
        finalSupply: z.number().optional(),
        finalMinerals: z.number().optional(),
        finalGas: z.number().optional(),
        unitsKilled: z.number().optional(),
        unitsLost: z.number().optional(),
      }))
      .mutation(async ({ input }) => {
        const { id, ...data } = input;
        return await db.updateGameSession(id, data);
      }),

    // 게임 통계
    getStats: protectedProcedure.query(async ({ ctx }) => {
      return await db.getGameStats(ctx.user.id);
    }),
  }),

  // Battles
  battle: router({
    // 세션별 전투 기록
    getBySession: protectedProcedure
      .input(z.object({ sessionId: z.number() }))
      .query(async ({ input }) => {
        return await db.getBattlesBySession(input.sessionId);
      }),

    // 전투 기록 생성
    create: protectedProcedure
      .input(z.object({
        sessionId: z.number(),
        battleTime: z.number(),
        location: z.string().optional(),
        unitsEngaged: z.number().optional(),
        unitsKilled: z.number().optional(),
        unitsLost: z.number().optional(),
        damageDealt: z.number().optional(),
        damageTaken: z.number().optional(),
        result: z.enum(["Win", "Loss", "Retreat"]),
      }))
      .mutation(async ({ input }) => {
        return await db.createBattle(input);
      }),
  }),

  // Training Episodes
  training: router({
    // 학습 에피소드 목록
    getEpisodes: protectedProcedure
      .input(z.object({ limit: z.number().optional() }))
      .query(async ({ ctx, input }) => {
        return await db.getTrainingEpisodes(ctx.user.id, input.limit);
      }),

    // 학습 통계
    getStats: protectedProcedure.query(async ({ ctx }) => {
      return await db.getTrainingStats(ctx.user.id);
    }),

    // 학습 에피소드 생성
    createEpisode: protectedProcedure
      .input(z.object({
        episodeNumber: z.number(),
        totalReward: z.number(),
        averageReward: z.number().optional(),
        winRate: z.number().optional(),
        gamesPlayed: z.number(),
        learningRate: z.number().optional(),
        epsilon: z.number().optional(),
        loss: z.number().optional(),
        notes: z.string().optional(),
      }))
      .mutation(async ({ ctx, input }) => {
        return await db.createTrainingEpisode({
          userId: ctx.user.id,
          ...input,
        });
      }),
  }),

  // Bot Configurations
  bot: router({
    // 봇 설정 목록
    getConfigs: protectedProcedure.query(async ({ ctx }) => {
      return await db.getBotConfigs(ctx.user.id);
    }),

    // 활성 봇 설정
    getActiveConfig: protectedProcedure.query(async ({ ctx }) => {
      return await db.getActiveBotConfig(ctx.user.id);
    }),

    // 봇 설정 생성
    createConfig: protectedProcedure
      .input(z.object({
        name: z.string(),
        strategy: z.enum(["Aggressive", "Defensive", "Balanced", "Economic", "Rush"]),
        buildOrder: z.string().optional(),
        isActive: z.boolean().optional(),
        description: z.string().optional(),
      }))
      .mutation(async ({ ctx, input }) => {
        return await db.createBotConfig({
          userId: ctx.user.id,
          ...input,
        });
      }),

    // 봇 설정 업데이트
    updateConfig: protectedProcedure
      .input(z.object({
        id: z.number(),
        name: z.string().optional(),
        strategy: z.enum(["Aggressive", "Defensive", "Balanced", "Economic", "Rush"]).optional(),
        buildOrder: z.string().optional(),
        isActive: z.boolean().optional(),
        description: z.string().optional(),
      }))
      .mutation(async ({ ctx, input }) => {
        const { id, ...data } = input;
        return await db.updateBotConfig(id, ctx.user.id, data);
      }),

    // 봇 설정 삭제
    deleteConfig: protectedProcedure
      .input(z.object({ id: z.number() }))
      .mutation(async ({ ctx, input }) => {
        return await db.deleteBotConfig(input.id, ctx.user.id);
      }),
  }),

  // AI Arena
  arena: router({
    // 경기 목록
    getMatches: protectedProcedure
      .input(z.object({ limit: z.number().optional() }))
      .query(async ({ ctx, input }) => {
        return await db.getArenaMatches(ctx.user.id, input.limit);
      }),

    // Arena 통계
    getStats: protectedProcedure.query(async ({ ctx }) => {
      return await db.getArenaStats(ctx.user.id);
    }),

    // 경기 기록 생성
    createMatch: protectedProcedure
      .input(z.object({
        matchId: z.string().optional(),
        opponentName: z.string().optional(),
        opponentRace: z.enum(["Terran", "Protoss", "Zerg"]).optional(),
        mapName: z.string().optional(),
        result: z.enum(["Win", "Loss", "Tie"]),
        ranking: z.number().optional(),
        elo: z.number().optional(),
        replayUrl: z.string().optional(),
      }))
      .mutation(async ({ ctx, input }) => {
        return await db.createArenaMatch({
          userId: ctx.user.id,
          ...input,
        });
      }),
  }),
});

export type AppRouter = typeof appRouter;
