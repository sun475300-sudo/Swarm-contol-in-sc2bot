import { describe, expect, it } from "vitest";
import { appRouter } from "./routers";
import type { TrpcContext } from "./_core/context";

type AuthenticatedUser = NonNullable<TrpcContext["user"]>;

function createAuthContext(): { ctx: TrpcContext } {
  const user: AuthenticatedUser = {
    id: 1,
    openId: "test-user",
    email: "test@example.com",
    name: "Test User",
    loginMethod: "manus",
    role: "user",
    createdAt: new Date(),
    updatedAt: new Date(),
    lastSignedIn: new Date(),
  };

  const ctx: TrpcContext = {
    user,
    req: {
      protocol: "https",
      headers: {},
    } as TrpcContext["req"],
    res: {
      clearCookie: () => {},
    } as TrpcContext["res"],
  };

  return { ctx };
}

describe("game router", () => {
  it("should get game stats", async () => {
    const { ctx } = createAuthContext();
    const caller = appRouter.createCaller(ctx);

    const stats = await caller.game.getStats();
    
    expect(stats).toBeDefined();
    expect(typeof stats?.totalGames).toBe("number");
  });

  it("should get game sessions", async () => {
    const { ctx } = createAuthContext();
    const caller = appRouter.createCaller(ctx);

    const sessions = await caller.game.getSessions({ limit: 10 });
    
    expect(Array.isArray(sessions)).toBe(true);
  });

  it("should get current session", async () => {
    const { ctx } = createAuthContext();
    const caller = appRouter.createCaller(ctx);

    const currentSession = await caller.game.getCurrentSession();
    
    // Current session can be null if no game is in progress
    expect(currentSession === null || typeof currentSession === "object").toBe(true);
  });
});

describe("training router", () => {
  it("should get training stats", async () => {
    const { ctx } = createAuthContext();
    const caller = appRouter.createCaller(ctx);

    const stats = await caller.training.getStats();
    
    expect(stats).toBeDefined();
  });

  it("should get training episodes", async () => {
    const { ctx } = createAuthContext();
    const caller = appRouter.createCaller(ctx);

    const episodes = await caller.training.getEpisodes({ limit: 10 });
    
    expect(Array.isArray(episodes)).toBe(true);
  });
});

describe("bot router", () => {
  it("should get bot configs", async () => {
    const { ctx } = createAuthContext();
    const caller = appRouter.createCaller(ctx);

    const configs = await caller.bot.getConfigs();
    
    expect(Array.isArray(configs)).toBe(true);
  });

  it("should get active bot config", async () => {
    const { ctx } = createAuthContext();
    const caller = appRouter.createCaller(ctx);

    const activeConfig = await caller.bot.getActiveConfig();
    
    // Active config can be null if no config is active
    expect(activeConfig === null || typeof activeConfig === "object").toBe(true);
  });
});

describe("arena router", () => {
  it("should get arena stats", async () => {
    const { ctx } = createAuthContext();
    const caller = appRouter.createCaller(ctx);

    const stats = await caller.arena.getStats();
    
    expect(stats).toBeDefined();
  });

  it("should get arena matches", async () => {
    const { ctx } = createAuthContext();
    const caller = appRouter.createCaller(ctx);

    const matches = await caller.arena.getMatches({ limit: 10 });
    
    expect(Array.isArray(matches)).toBe(true);
  });
});
