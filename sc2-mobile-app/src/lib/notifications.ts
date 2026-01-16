/**
 * 푸시 알림 서비스
 * Web Push API를 사용하여 브라우저 알림 구현
 */

export interface NotificationOptions {
  title: string;
  body: string;
  icon?: string;
  badge?: string;
  tag?: string;
  requireInteraction?: boolean;
  actions?: Array<{
    action: string;
    title: string;
  }>;
}

/**
 * 푸시 알림 지원 여부 확인
 */
export function isPushNotificationSupported(): boolean {
  return 'serviceWorker' in navigator && 'Notification' in window;
}

/**
 * 푸시 알림 권한 요청
 */
export async function requestNotificationPermission(): Promise<NotificationPermission> {
  if (!isPushNotificationSupported()) {
    console.warn('Push notifications are not supported');
    return 'denied';
  }

  if (Notification.permission === 'granted') {
    return 'granted';
  }

  if (Notification.permission !== 'denied') {
    const permission = await Notification.requestPermission();
    return permission;
  }

  return 'denied';
}

/**
 * 브라우저 알림 표시
 */
export function showNotification(options: NotificationOptions): void {
  if (!isPushNotificationSupported()) {
    console.warn('Push notifications are not supported');
    return;
  }

  if (Notification.permission !== 'granted') {
    console.warn('Notification permission not granted');
    return;
  }

  const notification = new Notification(options.title, {
    body: options.body,
    icon: options.icon || '/icon-192.png',
    badge: options.badge || '/icon-192.png',
    tag: options.tag || 'sc2-notification',
    requireInteraction: options.requireInteraction || false,
    actions: options.actions || [],
  });

  // 알림 클릭 이벤트
  notification.addEventListener('click', () => {
    window.focus();
    notification.close();
  });
}

/**
 * 게임 종료 알림
 */
export function notifyGameEnd(result: 'Victory' | 'Defeat', mapName: string): void {
  const title = result === 'Victory' ? '🎉 게임 승리!' : '😢 게임 패배';
  const body = `${mapName}에서 ${result === 'Victory' ? '승리' : '패배'}했습니다.`;

  showNotification({
    title,
    body,
    tag: 'game-end',
    requireInteraction: true,
  });
}

/**
 * 학습 완료 알림
 */
export function notifyTrainingComplete(episodeNumber: number, reward: number): void {
  showNotification({
    title: '📚 학습 에피소드 완료',
    body: `에피소드 ${episodeNumber}가 완료되었습니다. 보상: ${reward.toFixed(2)}`,
    tag: 'training-complete',
    requireInteraction: true,
  });
}

/**
 * Arena 경기 승리 알림
 */
export function notifyArenaWin(elo: number, opponent: string): void {
  showNotification({
    title: '🏆 Arena 경기 승리!',
    body: `${opponent}을(를) 이겼습니다. ELO: +${elo}`,
    tag: 'arena-win',
    requireInteraction: true,
  });
}

/**
 * Arena 경기 패배 알림
 */
export function notifyArenaLoss(elo: number, opponent: string): void {
  showNotification({
    title: '⚔️ Arena 경기 패배',
    body: `${opponent}에게 졌습니다. ELO: -${elo}`,
    tag: 'arena-loss',
  });
}

/**
 * 봇 설정 변경 알림
 */
export function notifyBotConfigChanged(configName: string): void {
  showNotification({
    title: '⚙️ 봇 설정 변경',
    body: `활성 봇 설정이 "${configName}"으로 변경되었습니다.`,
    tag: 'bot-config-changed',
  });
}

/**
 * 일반 정보 알림
 */
export function notifyInfo(title: string, body: string): void {
  showNotification({
    title,
    body,
    tag: 'info',
  });
}

/**
 * 에러 알림
 */
export function notifyError(title: string, body: string): void {
  showNotification({
    title,
    body,
    tag: 'error',
    requireInteraction: true,
  });
}

/**
 * 알림 권한 상태 확인
 */
export function getNotificationPermission(): NotificationPermission {
  if (!isPushNotificationSupported()) {
    return 'denied';
  }
  return Notification.permission;
}

/**
 * 모든 알림 닫기
 */
export async function closeAllNotifications(): Promise<void> {
  if (!isPushNotificationSupported()) {
    return;
  }

  const registration = await navigator.serviceWorker.ready;
  const notifications = await registration.getNotifications();
  notifications.forEach((notification) => {
    notification.close();
  });
}

/**
 * 특정 태그의 알림 닫기
 */
export async function closeNotificationByTag(tag: string): Promise<void> {
  if (!isPushNotificationSupported()) {
    return;
  }

  const registration = await navigator.serviceWorker.ready;
  const notifications = await registration.getNotifications({ tag });
  notifications.forEach((notification) => {
    notification.close();
  });
}
