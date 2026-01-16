import { useEffect, useState } from 'react';
import { Play, Pause, RotateCcw, Power, Settings } from 'lucide-react';
import {
  startBot,
  stopBot,
  pauseBot,
  resumeBot,
  restartBot,
  changeBotConfig,
  getBotStatus,
  BotStatus,
} from '@/lib/botControl';
import { getBotConfigs, BotConfig } from '@/lib/api';

export default function BotControl() {
  const [botStatus, setBotStatus] = useState<BotStatus | null>(null);
  const [botConfigs, setBotConfigs] = useState<BotConfig[]>([]);
  const [loading, setLoading] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      const [status, configs] = await Promise.all([
        getBotStatus(),
        getBotConfigs(),
      ]);
      setBotStatus(status);
      setBotConfigs(configs);
      setLoading(false);
    };

    fetchData();
    const interval = setInterval(fetchData, 10000); // 10초마다 새로고침
    return () => clearInterval(interval);
  }, []);

  const handleAction = async (action: () => Promise<any>) => {
    setActionLoading(true);
    try {
      const result = await action();
      if (result.success) {
        setMessage({ type: 'success', text: result.message });
        // 상태 새로고침
        const status = await getBotStatus();
        setBotStatus(status);
      } else {
        setMessage({ type: 'error', text: result.message });
      }
    } catch (error) {
      setMessage({ type: 'error', text: '작업 실패' });
    } finally {
      setActionLoading(false);
      setTimeout(() => setMessage(null), 3000);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'running':
        return 'text-green-400 bg-green-500/10';
      case 'stopped':
        return 'text-red-400 bg-red-500/10';
      case 'paused':
        return 'text-yellow-400 bg-yellow-500/10';
      case 'error':
        return 'text-red-500 bg-red-500/10';
      default:
        return 'text-gray-400 bg-gray-500/10';
    }
  };

  const getStatusLabel = (status: string) => {
    switch (status) {
      case 'running':
        return '실행 중';
      case 'stopped':
        return '중지됨';
      case 'paused':
        return '일시 정지됨';
      case 'error':
        return '오류';
      default:
        return '알 수 없음';
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="text-center">
          <div className="mb-4 h-8 w-8 animate-spin rounded-full border-4 border-border border-t-accent mx-auto" />
          <p className="text-muted-foreground">봇 상태 로드 중...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* 봇 상태 */}
      {botStatus && (
        <div className="glass rounded-lg border border-white/10 bg-white/5 p-6 backdrop-blur-md">
          <h3 className="mb-4 font-semibold">봇 상태</h3>
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-3">
            <div>
              <p className="text-xs text-muted-foreground">상태</p>
              <p className={`mt-2 inline-block rounded-full px-3 py-1 text-sm font-semibold ${getStatusColor(botStatus.status)}`}>
                {getStatusLabel(botStatus.status)}
              </p>
            </div>
            <div>
              <p className="text-xs text-muted-foreground">가동 시간</p>
              <p className="mt-2 font-semibold">
                {Math.floor(botStatus.uptime / 3600)}시간
              </p>
            </div>
            <div>
              <p className="text-xs text-muted-foreground">게임 수</p>
              <p className="mt-2 font-semibold">{botStatus.gamesPlayed}</p>
            </div>
            <div>
              <p className="text-xs text-muted-foreground">CPU 사용률</p>
              <p className="mt-2 font-semibold text-cyan-400">
                {botStatus.cpuUsage.toFixed(1)}%
              </p>
            </div>
            <div>
              <p className="text-xs text-muted-foreground">메모리 사용률</p>
              <p className="mt-2 font-semibold text-purple-400">
                {botStatus.memoryUsage.toFixed(1)}%
              </p>
            </div>
            <div>
              <p className="text-xs text-muted-foreground">마지막 게임</p>
              <p className="mt-2 text-sm">
                {new Date(botStatus.lastGameTime).toLocaleTimeString('ko-KR')}
              </p>
            </div>
          </div>
        </div>
      )}

      {/* 제어 버튼 */}
      <div className="glass rounded-lg border border-white/10 bg-white/5 p-6 backdrop-blur-md">
        <h3 className="mb-4 font-semibold">봇 제어</h3>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
          <button
            onClick={() => handleAction(startBot)}
            disabled={actionLoading || botStatus?.status === 'running'}
            className="flex items-center justify-center gap-2 rounded-lg bg-green-500/20 px-4 py-3 font-medium text-green-400 hover:bg-green-500/30 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            <Play className="h-4 w-4" />
            <span className="hidden sm:inline">시작</span>
          </button>

          <button
            onClick={() => handleAction(pauseBot)}
            disabled={actionLoading || botStatus?.status !== 'running'}
            className="flex items-center justify-center gap-2 rounded-lg bg-yellow-500/20 px-4 py-3 font-medium text-yellow-400 hover:bg-yellow-500/30 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            <Pause className="h-4 w-4" />
            <span className="hidden sm:inline">일시정지</span>
          </button>

          <button
            onClick={() => handleAction(resumeBot)}
            disabled={actionLoading || botStatus?.status !== 'paused'}
            className="flex items-center justify-center gap-2 rounded-lg bg-blue-500/20 px-4 py-3 font-medium text-blue-400 hover:bg-blue-500/30 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            <Play className="h-4 w-4" />
            <span className="hidden sm:inline">재개</span>
          </button>

          <button
            onClick={() => handleAction(restartBot)}
            disabled={actionLoading}
            className="flex items-center justify-center gap-2 rounded-lg bg-cyan-500/20 px-4 py-3 font-medium text-cyan-400 hover:bg-cyan-500/30 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            <RotateCcw className="h-4 w-4" />
            <span className="hidden sm:inline">재시작</span>
          </button>

          <button
            onClick={() => handleAction(stopBot)}
            disabled={actionLoading || botStatus?.status === 'stopped'}
            className="flex items-center justify-center gap-2 rounded-lg bg-red-500/20 px-4 py-3 font-medium text-red-400 hover:bg-red-500/30 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            <Power className="h-4 w-4" />
            <span className="hidden sm:inline">중지</span>
          </button>
        </div>
      </div>

      {/* 봇 설정 변경 */}
      {botConfigs.length > 0 && (
        <div className="glass rounded-lg border border-white/10 bg-white/5 p-6 backdrop-blur-md">
          <h3 className="mb-4 font-semibold">봇 설정 변경</h3>
          <div className="space-y-3">
            {botConfigs.map((config) => (
              <button
                key={config.id}
                onClick={() => handleAction(() => changeBotConfig(config.id))}
                disabled={actionLoading || config.id === botStatus?.activeConfigId}
                className={`w-full rounded-lg border p-4 text-left transition-colors ${
                  config.id === botStatus?.activeConfigId
                    ? 'border-accent bg-accent/10'
                    : 'border-white/10 bg-white/5 hover:bg-white/10'
                } disabled:opacity-50 disabled:cursor-not-allowed`}
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <h4 className="font-semibold">{config.name}</h4>
                    <p className="mt-1 text-xs text-muted-foreground">
                      {config.description}
                    </p>
                    <p className="mt-2 text-xs">
                      <span className="font-medium">전략:</span> {config.strategy}
                    </p>
                  </div>
                  {config.id === botStatus?.activeConfigId && (
                    <div className="ml-2 flex-shrink-0 rounded-full bg-accent px-3 py-1 text-xs font-semibold text-accent-foreground">
                      활성
                    </div>
                  )}
                </div>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* 메시지 표시 */}
      {message && (
        <div
          className={`rounded-lg border px-4 py-3 text-sm font-medium ${
            message.type === 'success'
              ? 'border-green-500/50 bg-green-500/10 text-green-400'
              : 'border-red-500/50 bg-red-500/10 text-red-400'
          }`}
        >
          {message.text}
        </div>
      )}

      {/* 주의 사항 */}
      <div className="glass rounded-lg border border-white/10 bg-white/5 p-4 backdrop-blur-md">
        <p className="text-sm text-muted-foreground">
          ⚠️ 봇 제어는 신중하게 사용하세요. 봇을 중지하면 게임이 중단됩니다.
        </p>
      </div>
    </div>
  );
}
