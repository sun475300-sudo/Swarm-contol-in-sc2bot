/**
 * WebSocket 실시간 데이터 연동
 * 폴링 대신 WebSocket을 사용하여 실시간 업데이트 구현
 */

export type MessageType =
  | 'game_state_update'
  | 'game_end'
  | 'training_update'
  | 'training_complete'
  | 'arena_match'
  | 'bot_config_change'
  | 'connection'
  | 'error';

export interface WebSocketMessage {
  type: MessageType;
  data: any;
  timestamp: number;
}

export interface GameStateUpdate {
  mapName: string;
  enemyRace: string;
  gamePhase: string;
  duration: number;
  finalMinerals: number;
  finalGas: number;
  finalSupply: number;
  unitsKilled: number;
  unitsLost: number;
}

export interface GameEndMessage {
  result: 'Victory' | 'Defeat';
  mapName: string;
  duration: number;
  unitsKilled: number;
  unitsLost: number;
  finalMinerals: number;
  finalGas: number;
}

export interface TrainingUpdate {
  episodeNumber: number;
  totalReward: number;
  averageReward: number;
  winRate: number;
  gamesPlayed: number;
  loss: number;
}

export interface ArenaMatchMessage {
  matchId: string;
  opponentName: string;
  result: 'Win' | 'Loss';
  elo: number;
  eloDelta: number;
}

export interface BotConfigChangeMessage {
  configId: number;
  configName: string;
  strategy: string;
}

type MessageHandler = (data: any) => void;

class WebSocketManager {
  private ws: WebSocket | null = null;
  private url: string;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 3000;
  private messageHandlers: Map<MessageType, Set<MessageHandler>> = new Map();
  private isManuallyDisconnected = false;

  constructor(url: string) {
    this.url = this.convertHttpToWs(url);
  }

  /**
   * HTTP URL을 WebSocket URL로 변환
   */
  private convertHttpToWs(url: string): string {
    return url
      .replace(/^http:\/\//, 'ws://')
      .replace(/^https:\/\//, 'wss://')
      .replace(/\/$/, '');
  }

  /**
   * WebSocket 연결
   */
  public connect(): Promise<void> {
    return new Promise((resolve, reject) => {
      try {
        this.ws = new WebSocket(`${this.url}/ws`);

        this.ws.onopen = () => {
          console.log('WebSocket connected');
          this.reconnectAttempts = 0;
          this.emit('connection', { status: 'connected' });
          resolve();
        };

        this.ws.onmessage = (event) => {
          try {
            const message: WebSocketMessage = JSON.parse(event.data);
            this.handleMessage(message);
          } catch (error) {
            console.error('Failed to parse WebSocket message:', error);
          }
        };

        this.ws.onerror = (error) => {
          console.error('WebSocket error:', error);
          this.emit('error', { message: 'WebSocket connection error' });
          reject(error);
        };

        this.ws.onclose = () => {
          console.log('WebSocket disconnected');
          this.emit('connection', { status: 'disconnected' });

          if (!this.isManuallyDisconnected) {
            this.attemptReconnect();
          }
        };
      } catch (error) {
        reject(error);
      }
    });
  }

  /**
   * WebSocket 재연결 시도
   */
  private attemptReconnect(): void {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error('Max reconnect attempts reached');
      this.emit('error', { message: 'Failed to reconnect after multiple attempts' });
      return;
    }

    this.reconnectAttempts++;
    const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1);
    console.log(`Attempting to reconnect in ${delay}ms (attempt ${this.reconnectAttempts})`);

    setTimeout(() => {
      this.connect().catch((error) => {
        console.error('Reconnection failed:', error);
      });
    }, delay);
  }

  /**
   * 메시지 처리
   */
  private handleMessage(message: WebSocketMessage): void {
    const handlers = this.messageHandlers.get(message.type);
    if (handlers) {
      handlers.forEach((handler) => {
        try {
          handler(message.data);
        } catch (error) {
          console.error('Error in message handler:', error);
        }
      });
    }
  }

  /**
   * 메시지 핸들러 등록
   */
  public on(type: MessageType, handler: MessageHandler): () => void {
    if (!this.messageHandlers.has(type)) {
      this.messageHandlers.set(type, new Set());
    }

    this.messageHandlers.get(type)!.add(handler);

    // 핸들러 제거 함수 반환
    return () => {
      this.messageHandlers.get(type)?.delete(handler);
    };
  }

  /**
   * 메시지 발송
   */
  public send(message: WebSocketMessage): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(message));
    } else {
      console.warn('WebSocket is not connected');
    }
  }

  /**
   * 메시지 발송 (헬퍼)
   */
  private emit(type: MessageType, data: any): void {
    this.send({
      type,
      data,
      timestamp: Date.now(),
    });
  }

  /**
   * 연결 해제
   */
  public disconnect(): void {
    this.isManuallyDisconnected = true;
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }

  /**
   * 연결 상태 확인
   */
  public isConnected(): boolean {
    return this.ws !== null && this.ws.readyState === WebSocket.OPEN;
  }

  /**
   * URL 변경
   */
  public setUrl(url: string): void {
    this.url = this.convertHttpToWs(url);
    if (this.isConnected()) {
      this.disconnect();
      this.isManuallyDisconnected = false;
      this.connect().catch((error) => {
        console.error('Failed to reconnect with new URL:', error);
      });
    }
  }
}

// 싱글톤 인스턴스
let wsManager: WebSocketManager | null = null;

/**
 * WebSocket 매니저 초기화
 */
export function initializeWebSocket(url: string): WebSocketManager {
  if (!wsManager) {
    wsManager = new WebSocketManager(url);
  }
  return wsManager;
}

/**
 * WebSocket 매니저 가져오기
 */
export function getWebSocketManager(): WebSocketManager | null {
  return wsManager;
}

/**
 * WebSocket 연결
 */
export async function connectWebSocket(url: string): Promise<void> {
  const manager = initializeWebSocket(url);
  await manager.connect();
}

/**
 * WebSocket 연결 해제
 */
export function disconnectWebSocket(): void {
  if (wsManager) {
    wsManager.disconnect();
    wsManager = null;
  }
}

/**
 * 게임 상태 업데이트 구독
 */
export function onGameStateUpdate(handler: (data: GameStateUpdate) => void): () => void {
  const manager = getWebSocketManager();
  if (!manager) {
    console.warn('WebSocket not initialized');
    return () => {};
  }
  return manager.on('game_state_update', handler);
}

/**
 * 게임 종료 구독
 */
export function onGameEnd(handler: (data: GameEndMessage) => void): () => void {
  const manager = getWebSocketManager();
  if (!manager) {
    console.warn('WebSocket not initialized');
    return () => {};
  }
  return manager.on('game_end', handler);
}

/**
 * 학습 업데이트 구독
 */
export function onTrainingUpdate(handler: (data: TrainingUpdate) => void): () => void {
  const manager = getWebSocketManager();
  if (!manager) {
    console.warn('WebSocket not initialized');
    return () => {};
  }
  return manager.on('training_update', handler);
}

/**
 * 학습 완료 구독
 */
export function onTrainingComplete(handler: (data: TrainingUpdate) => void): () => void {
  const manager = getWebSocketManager();
  if (!manager) {
    console.warn('WebSocket not initialized');
    return () => {};
  }
  return manager.on('training_complete', handler);
}

/**
 * Arena 경기 구독
 */
export function onArenaMatch(handler: (data: ArenaMatchMessage) => void): () => void {
  const manager = getWebSocketManager();
  if (!manager) {
    console.warn('WebSocket not initialized');
    return () => {};
  }
  return manager.on('arena_match', handler);
}

/**
 * 봇 설정 변경 구독
 */
export function onBotConfigChange(handler: (data: BotConfigChangeMessage) => void): () => void {
  const manager = getWebSocketManager();
  if (!manager) {
    console.warn('WebSocket not initialized');
    return () => {};
  }
  return manager.on('bot_config_change', handler);
}

/**
 * 연결 상태 구독
 */
export function onConnectionChange(handler: (data: { status: 'connected' | 'disconnected' }) => void): () => void {
  const manager = getWebSocketManager();
  if (!manager) {
    console.warn('WebSocket not initialized');
    return () => {};
  }
  return manager.on('connection', handler);
}

/**
 * 에러 구독
 */
export function onWebSocketError(handler: (data: { message: string }) => void): () => void {
  const manager = getWebSocketManager();
  if (!manager) {
    console.warn('WebSocket not initialized');
    return () => {};
  }
  return manager.on('error', handler);
}
