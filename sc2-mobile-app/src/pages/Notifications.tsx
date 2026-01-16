import { useState } from 'react';
import { Bell, Check, X, AlertCircle } from 'lucide-react';

interface Notification {
  id: string;
  type: 'success' | 'warning' | 'error' | 'info';
  title: string;
  message: string;
  timestamp: Date;
  read: boolean;
}

export default function Notifications() {
  const [notifications, setNotifications] = useState<Notification[]>([
    {
      id: '1',
      type: 'success',
      title: '게임 완료',
      message: '게임이 완료되었습니다. 결과: 승리',
      timestamp: new Date(Date.now() - 10 * 60000),
      read: false,
    },
    {
      id: '2',
      type: 'info',
      title: '학습 에피소드 완료',
      message: '에피소드 45가 완료되었습니다. 보상: 245.67',
      timestamp: new Date(Date.now() - 30 * 60000),
      read: false,
    },
    {
      id: '3',
      type: 'warning',
      title: '봇 설정 변경',
      message: '활성 봇 설정이 "공격형 저글링 러시"로 변경되었습니다.',
      timestamp: new Date(Date.now() - 2 * 3600000),
      read: true,
    },
    {
      id: '4',
      type: 'success',
      title: 'Arena 경기 승리',
      message: 'Arena 경기에서 승리했습니다. ELO: +25',
      timestamp: new Date(Date.now() - 24 * 3600000),
      read: true,
    },
  ]);

  const handleMarkAsRead = (id: string) => {
    setNotifications(
      notifications.map((n) =>
        n.id === id ? { ...n, read: true } : n
      )
    );
  };

  const handleDelete = (id: string) => {
    setNotifications(notifications.filter((n) => n.id !== id));
  };

  const handleMarkAllAsRead = () => {
    setNotifications(
      notifications.map((n) => ({ ...n, read: true }))
    );
  };

  const unreadCount = notifications.filter((n) => !n.read).length;

  const getIcon = (type: string) => {
    switch (type) {
      case 'success':
        return <Check className="h-5 w-5 text-green-500" />;
      case 'warning':
        return <AlertCircle className="h-5 w-5 text-yellow-500" />;
      case 'error':
        return <X className="h-5 w-5 text-red-500" />;
      default:
        return <Bell className="h-5 w-5 text-cyan-500" />;
    }
  };

  const getBackgroundColor = (type: string) => {
    switch (type) {
      case 'success':
        return 'bg-green-500/10 border-green-500/20';
      case 'warning':
        return 'bg-yellow-500/10 border-yellow-500/20';
      case 'error':
        return 'bg-red-500/10 border-red-500/20';
      default:
        return 'bg-cyan-500/10 border-cyan-500/20';
    }
  };

  const formatTime = (date: Date) => {
    const now = new Date();
    const diff = now.getTime() - date.getTime();
    const minutes = Math.floor(diff / 60000);
    const hours = Math.floor(diff / 3600000);
    const days = Math.floor(diff / 86400000);

    if (minutes < 1) return '방금 전';
    if (minutes < 60) return `${minutes}분 전`;
    if (hours < 24) return `${hours}시간 전`;
    if (days < 7) return `${days}일 전`;
    return date.toLocaleDateString('ko-KR');
  };

  return (
    <div className="space-y-6">
      {/* 헤더 */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold">알림</h2>
          {unreadCount > 0 && (
            <p className="mt-1 text-sm text-muted-foreground">
              읽지 않은 알림: {unreadCount}개
            </p>
          )}
        </div>
        {unreadCount > 0 && (
          <button
            onClick={handleMarkAllAsRead}
            className="rounded-lg bg-secondary px-3 py-2 text-sm font-medium text-muted-foreground hover:bg-secondary/80"
          >
            모두 읽음
          </button>
        )}
      </div>

      {/* 알림 목록 */}
      {notifications.length === 0 ? (
        <div className="glass rounded-lg border border-white/10 bg-white/5 p-12 text-center backdrop-blur-md">
          <Bell className="mx-auto h-12 w-12 text-muted-foreground opacity-50" />
          <p className="mt-4 text-muted-foreground">알림이 없습니다</p>
        </div>
      ) : (
        <div className="space-y-3">
          {notifications.map((notification) => (
            <div
              key={notification.id}
              className={`glass rounded-lg border p-4 backdrop-blur-md transition-colors ${
                notification.read
                  ? 'border-white/10 bg-white/5'
                  : `border-white/20 ${getBackgroundColor(notification.type)}`
              }`}
            >
              <div className="flex items-start gap-4">
                <div className="mt-1 flex-shrink-0">
                  {getIcon(notification.type)}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <h3 className="font-semibold">{notification.title}</h3>
                      <p className="mt-1 text-sm text-muted-foreground">
                        {notification.message}
                      </p>
                    </div>
                    {!notification.read && (
                      <div className="h-2 w-2 flex-shrink-0 rounded-full bg-cyan-500" />
                    )}
                  </div>
                  <p className="mt-2 text-xs text-muted-foreground">
                    {formatTime(notification.timestamp)}
                  </p>
                </div>
                <div className="flex gap-2 flex-shrink-0">
                  {!notification.read && (
                    <button
                      onClick={() => handleMarkAsRead(notification.id)}
                      className="rounded p-1 hover:bg-white/10"
                      title="읽음 표시"
                    >
                      <Check className="h-4 w-4" />
                    </button>
                  )}
                  <button
                    onClick={() => handleDelete(notification.id)}
                    className="rounded p-1 hover:bg-white/10"
                    title="삭제"
                  >
                    <X className="h-4 w-4" />
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* 알림 설정 안내 */}
      <div className="glass rounded-lg border border-white/10 bg-white/5 p-4 backdrop-blur-md">
        <p className="text-sm text-muted-foreground">
          💡 알림 설정은 <span className="font-semibold">설정</span> 페이지에서 변경할 수 있습니다.
        </p>
      </div>
    </div>
  );
}
