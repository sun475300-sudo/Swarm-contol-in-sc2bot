/**
 * 로컬 스토리지를 사용한 데이터 동기화 및 오프라인 지원
 */

import { GameSession, TrainingEpisode, ArenaMatch } from './api';

const STORAGE_PREFIX = 'sc2_mobile_';

interface StorageData {
  gameSessions: GameSession[];
  trainingEpisodes: TrainingEpisode[];
  arenaMatches: ArenaMatch[];
  lastSyncTime: number;
  syncStatus: 'synced' | 'pending' | 'failed';
}

/**
 * 저장소 초기화
 */
export function initializeStorage(): void {
  const existing = localStorage.getItem(`${STORAGE_PREFIX}data`);
  if (!existing) {
    const initialData: StorageData = {
      gameSessions: [],
      trainingEpisodes: [],
      arenaMatches: [],
      lastSyncTime: 0,
      syncStatus: 'synced',
    };
    localStorage.setItem(`${STORAGE_PREFIX}data`, JSON.stringify(initialData));
  }
}

/**
 * 저장소 데이터 가져오기
 */
export function getStorageData(): StorageData {
  initializeStorage();
  const data = localStorage.getItem(`${STORAGE_PREFIX}data`);
  if (!data) {
    return {
      gameSessions: [],
      trainingEpisodes: [],
      arenaMatches: [],
      lastSyncTime: 0,
      syncStatus: 'synced',
    };
  }
  return JSON.parse(data);
}

/**
 * 저장소 데이터 업데이트
 */
export function updateStorageData(data: Partial<StorageData>): void {
  const current = getStorageData();
  const updated = { ...current, ...data, lastSyncTime: Date.now() };
  localStorage.setItem(`${STORAGE_PREFIX}data`, JSON.stringify(updated));
}

/**
 * 게임 세션 저장
 */
export function saveGameSession(session: GameSession): void {
  const data = getStorageData();
  const existing = data.gameSessions.findIndex((s) => s.id === session.id);
  if (existing >= 0) {
    data.gameSessions[existing] = session;
  } else {
    data.gameSessions.unshift(session);
  }
  // 최근 100개만 유지
  data.gameSessions = data.gameSessions.slice(0, 100);
  updateStorageData(data);
}

/**
 * 게임 세션 목록 가져오기
 */
export function getGameSessionsFromStorage(): GameSession[] {
  return getStorageData().gameSessions;
}

/**
 * 학습 에피소드 저장
 */
export function saveTrainingEpisode(episode: TrainingEpisode): void {
  const data = getStorageData();
  const existing = data.trainingEpisodes.findIndex((e) => e.id === episode.id);
  if (existing >= 0) {
    data.trainingEpisodes[existing] = episode;
  } else {
    data.trainingEpisodes.unshift(episode);
  }
  // 최근 100개만 유지
  data.trainingEpisodes = data.trainingEpisodes.slice(0, 100);
  updateStorageData(data);
}

/**
 * 학습 에피소드 목록 가져오기
 */
export function getTrainingEpisodesFromStorage(): TrainingEpisode[] {
  return getStorageData().trainingEpisodes;
}

/**
 * Arena 경기 저장
 */
export function saveArenaMatch(match: ArenaMatch): void {
  const data = getStorageData();
  const existing = data.arenaMatches.findIndex((m) => m.id === match.id);
  if (existing >= 0) {
    data.arenaMatches[existing] = match;
  } else {
    data.arenaMatches.unshift(match);
  }
  // 최근 100개만 유지
  data.arenaMatches = data.arenaMatches.slice(0, 100);
  updateStorageData(data);
}

/**
 * Arena 경기 목록 가져오기
 */
export function getArenaMatchesFromStorage(): ArenaMatch[] {
  return getStorageData().arenaMatches;
}

/**
 * 마지막 동기화 시간 가져오기
 */
export function getLastSyncTime(): number {
  return getStorageData().lastSyncTime;
}

/**
 * 동기화 상태 가져오기
 */
export function getSyncStatus(): 'synced' | 'pending' | 'failed' {
  return getStorageData().syncStatus;
}

/**
 * 동기화 상태 업데이트
 */
export function setSyncStatus(status: 'synced' | 'pending' | 'failed'): void {
  const data = getStorageData();
  updateStorageData({ ...data, syncStatus: status });
}

/**
 * 저장소 크기 확인
 */
export function getStorageSize(): number {
  const data = localStorage.getItem(`${STORAGE_PREFIX}data`);
  return data ? new Blob([data]).size : 0;
}

/**
 * 저장소 초기화 (모든 데이터 삭제)
 */
export function clearStorage(): void {
  localStorage.removeItem(`${STORAGE_PREFIX}data`);
  initializeStorage();
}

/**
 * 오래된 데이터 정리 (7일 이상)
 */
export function cleanupOldData(): void {
  const data = getStorageData();
  const sevenDaysAgo = Date.now() - 7 * 24 * 60 * 60 * 1000;

  data.gameSessions = data.gameSessions.filter(
    (s) => new Date(s.createdAt).getTime() > sevenDaysAgo
  );
  data.trainingEpisodes = data.trainingEpisodes.filter(
    (e) => new Date(e.createdAt).getTime() > sevenDaysAgo
  );
  data.arenaMatches = data.arenaMatches.filter(
    (m) => new Date(m.createdAt).getTime() > sevenDaysAgo
  );

  updateStorageData(data);
}

/**
 * 데이터 내보내기 (JSON)
 */
export function exportData(): string {
  const data = getStorageData();
  return JSON.stringify(data, null, 2);
}

/**
 * 데이터 가져오기 (JSON)
 */
export function importData(jsonString: string): boolean {
  try {
    const data = JSON.parse(jsonString) as StorageData;
    localStorage.setItem(`${STORAGE_PREFIX}data`, JSON.stringify(data));
    return true;
  } catch (error) {
    console.error('Failed to import data:', error);
    return false;
  }
}

/**
 * 저장소 통계
 */
export function getStorageStats() {
  const data = getStorageData();
  return {
    totalGameSessions: data.gameSessions.length,
    totalTrainingEpisodes: data.trainingEpisodes.length,
    totalArenaMatches: data.arenaMatches.length,
    lastSyncTime: new Date(data.lastSyncTime),
    syncStatus: data.syncStatus,
    storageSize: getStorageSize(),
  };
}
