import axios from 'axios';

const DASHBOARD_URL = import.meta.env.VITE_DASHBOARD_URL || 'https://sc2aidash-bncleqgg.manus.space';

const api = axios.create({
  baseURL: `${DASHBOARD_URL}/api/trpc`,
  timeout: 10000,
});

/**
 * 봇 제어 요청 타입
 */
export interface BotControlRequest {
  action: 'start' | 'stop' | 'pause' | 'resume' | 'restart' | 'change_config';
  configId?: number;
  parameters?: Record<string, any>;
}

/**
 * 봇 제어 응답 타입
 */
export interface BotControlResponse {
  success: boolean;
  message: string;
  data?: any;
}

/**
 * 봇 상태 타입
 */
export interface BotStatus {
  id: number;
  status: 'running' | 'stopped' | 'paused' | 'error';
  activeConfigId: number;
  uptime: number;
  gamesPlayed: number;
  lastGameTime: Date;
  cpuUsage: number;
  memoryUsage: number;
}

/**
 * 봇 시작
 */
export async function startBot(): Promise<BotControlResponse> {
  try {
    const response = await api.post<{ result: { data: BotControlResponse } }>(
      'bot.start',
      { json: {} }
    );
    return response.data.result.data;
  } catch (error) {
    console.error('Failed to start bot:', error);
    return {
      success: false,
      message: '봇 시작에 실패했습니다.',
    };
  }
}

/**
 * 봇 중지
 */
export async function stopBot(): Promise<BotControlResponse> {
  try {
    const response = await api.post<{ result: { data: BotControlResponse } }>(
      'bot.stop',
      { json: {} }
    );
    return response.data.result.data;
  } catch (error) {
    console.error('Failed to stop bot:', error);
    return {
      success: false,
      message: '봇 중지에 실패했습니다.',
    };
  }
}

/**
 * 봇 일시 정지
 */
export async function pauseBot(): Promise<BotControlResponse> {
  try {
    const response = await api.post<{ result: { data: BotControlResponse } }>(
      'bot.pause',
      { json: {} }
    );
    return response.data.result.data;
  } catch (error) {
    console.error('Failed to pause bot:', error);
    return {
      success: false,
      message: '봇 일시 정지에 실패했습니다.',
    };
  }
}

/**
 * 봇 재개
 */
export async function resumeBot(): Promise<BotControlResponse> {
  try {
    const response = await api.post<{ result: { data: BotControlResponse } }>(
      'bot.resume',
      { json: {} }
    );
    return response.data.result.data;
  } catch (error) {
    console.error('Failed to resume bot:', error);
    return {
      success: false,
      message: '봇 재개에 실패했습니다.',
    };
  }
}

/**
 * 봇 재시작
 */
export async function restartBot(): Promise<BotControlResponse> {
  try {
    const response = await api.post<{ result: { data: BotControlResponse } }>(
      'bot.restart',
      { json: {} }
    );
    return response.data.result.data;
  } catch (error) {
    console.error('Failed to restart bot:', error);
    return {
      success: false,
      message: '봇 재시작에 실패했습니다.',
    };
  }
}

/**
 * 봇 설정 변경
 */
export async function changeBotConfig(configId: number): Promise<BotControlResponse> {
  try {
    const response = await api.post<{ result: { data: BotControlResponse } }>(
      'bot.changeConfig',
      { json: { configId } }
    );
    return response.data.result.data;
  } catch (error) {
    console.error('Failed to change bot config:', error);
    return {
      success: false,
      message: '봇 설정 변경에 실패했습니다.',
    };
  }
}

/**
 * 봇 상태 조회
 */
export async function getBotStatus(): Promise<BotStatus | null> {
  try {
    const response = await api.post<{ result: { data: BotStatus } }>(
      'bot.getStatus',
      { json: {} }
    );
    return response.data.result.data;
  } catch (error) {
    console.error('Failed to get bot status:', error);
    return null;
  }
}

/**
 * 봇 설정 매개변수 업데이트
 */
export async function updateBotParameters(
  parameters: Record<string, any>
): Promise<BotControlResponse> {
  try {
    const response = await api.post<{ result: { data: BotControlResponse } }>(
      'bot.updateParameters',
      { json: { parameters } }
    );
    return response.data.result.data;
  } catch (error) {
    console.error('Failed to update bot parameters:', error);
    return {
      success: false,
      message: '봇 매개변수 업데이트에 실패했습니다.',
    };
  }
}

/**
 * 봇 로그 조회
 */
export async function getBotLogs(limit: number = 100): Promise<string[]> {
  try {
    const response = await api.post<{ result: { data: string[] } }>(
      'bot.getLogs',
      { json: { limit } }
    );
    return response.data.result.data || [];
  } catch (error) {
    console.error('Failed to get bot logs:', error);
    return [];
  }
}

/**
 * 봇 성능 메트릭 조회
 */
export async function getBotMetrics(): Promise<Record<string, any> | null> {
  try {
    const response = await api.post<{ result: { data: Record<string, any> } }>(
      'bot.getMetrics',
      { json: {} }
    );
    return response.data.result.data;
  } catch (error) {
    console.error('Failed to get bot metrics:', error);
    return null;
  }
}
