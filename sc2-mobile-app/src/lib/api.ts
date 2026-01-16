import axios from 'axios';

// 대시보드 API 기본 URL
const DASHBOARD_URL = import.meta.env.VITE_DASHBOARD_URL || 'https://sc2aidash-bncleqgg.manus.space';

const api = axios.create({
  baseURL: `${DASHBOARD_URL}/api/trpc`,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// API 응답 타입
export interface ApiResponse<T> {
  result: {
    data: T;
  };
}

// 게임 세션 타입
export interface GameSession {
  id: number;
  mapName: string;
  enemyRace: string;
  difficulty: string;
  gamePhase: string;
  result: 'Victory' | 'Defeat';
  finalMinerals: number;
  finalGas: number;
  finalSupply: number;
  unitsKilled: number;
  unitsLost: number;
  duration: number;
  createdAt: Date;
}

// 게임 통계 타입
export interface GameStats {
  totalGames: number;
  wins: number;
  losses: number;
  winRate: number;
  averageDuration: number;
  totalUnitsKilled: number;
  totalUnitsLost: number;
}

// 학습 에피소드 타입
export interface TrainingEpisode {
  id: number;
  episodeNumber: number;
  totalReward: number;
  averageReward: number;
  winRate: number;
  gamesPlayed: number;
  loss: number;
  notes?: string;
  createdAt: Date;
}

// 학습 통계 타입
export interface TrainingStats {
  totalEpisodes: number;
  latestReward: number;
  averageReward: number;
  latestWinRate: number;
  latestLoss: number;
}

// 봇 설정 타입
export interface BotConfig {
  id: number;
  name: string;
  strategy: string;
  buildOrder: string;
  description: string;
  isActive: boolean;
  createdAt: Date;
}

// Arena 경기 타입
export interface ArenaMatch {
  id: number;
  matchId: string;
  opponentName: string;
  opponentRace: string;
  mapName: string;
  result: 'Win' | 'Loss';
  elo: number;
  createdAt: Date;
}

// Arena 통계 타입
export interface ArenaStats {
  totalMatches: number;
  wins: number;
  losses: number;
  winRate: number;
  currentElo: number;
  highestElo: number;
}

// 현재 게임 세션 조회
export async function getCurrentGameSession(): Promise<GameSession | null> {
  try {
    const response = await api.post<ApiResponse<GameSession | null>>('game.getCurrentSession', {
      json: {},
    });
    return response.data.result.data;
  } catch (error) {
    console.error('Failed to fetch current game session:', error);
    return null;
  }
}

// 게임 세션 목록 조회
export async function getGameSessions(limit: number = 20): Promise<GameSession[]> {
  try {
    const response = await api.post<ApiResponse<GameSession[]>>('game.getSessions', {
      json: { limit },
    });
    return response.data.result.data || [];
  } catch (error) {
    console.error('Failed to fetch game sessions:', error);
    return [];
  }
}

// 게임 통계 조회
export async function getGameStats(): Promise<GameStats | null> {
  try {
    const response = await api.post<ApiResponse<GameStats>>('game.getStats', {
      json: {},
    });
    return response.data.result.data;
  } catch (error) {
    console.error('Failed to fetch game stats:', error);
    return null;
  }
}

// 학습 에피소드 목록 조회
export async function getTrainingEpisodes(limit: number = 50): Promise<TrainingEpisode[]> {
  try {
    const response = await api.post<ApiResponse<TrainingEpisode[]>>('training.getEpisodes', {
      json: { limit },
    });
    return response.data.result.data || [];
  } catch (error) {
    console.error('Failed to fetch training episodes:', error);
    return [];
  }
}

// 학습 통계 조회
export async function getTrainingStats(): Promise<TrainingStats | null> {
  try {
    const response = await api.post<ApiResponse<TrainingStats>>('training.getStats', {
      json: {},
    });
    return response.data.result.data;
  } catch (error) {
    console.error('Failed to fetch training stats:', error);
    return null;
  }
}

// 봇 설정 목록 조회
export async function getBotConfigs(): Promise<BotConfig[]> {
  try {
    const response = await api.post<ApiResponse<BotConfig[]>>('bot.getConfigs', {
      json: {},
    });
    return response.data.result.data || [];
  } catch (error) {
    console.error('Failed to fetch bot configs:', error);
    return [];
  }
}

// 활성 봇 설정 조회
export async function getActiveBotConfig(): Promise<BotConfig | null> {
  try {
    const response = await api.post<ApiResponse<BotConfig>>('bot.getActiveConfig', {
      json: {},
    });
    return response.data.result.data;
  } catch (error) {
    console.error('Failed to fetch active bot config:', error);
    return null;
  }
}

// Arena 경기 목록 조회
export async function getArenaMatches(limit: number = 30): Promise<ArenaMatch[]> {
  try {
    const response = await api.post<ApiResponse<ArenaMatch[]>>('arena.getMatches', {
      json: { limit },
    });
    return response.data.result.data || [];
  } catch (error) {
    console.error('Failed to fetch arena matches:', error);
    return [];
  }
}

// Arena 통계 조회
export async function getArenaStats(): Promise<ArenaStats | null> {
  try {
    const response = await api.post<ApiResponse<ArenaStats>>('arena.getStats', {
      json: {},
    });
    return response.data.result.data;
  } catch (error) {
    console.error('Failed to fetch arena stats:', error);
    return null;
  }
}

export default api;
