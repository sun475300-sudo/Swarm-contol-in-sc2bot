import { useEffect, useState, useCallback } from 'react';
import {
  Activity,
  Cpu,
  HardDrive,
  Zap,
  Clock,
  RefreshCw,
  Play,
  Pause,
  Wifi,
  WifiOff,
  ChevronUp,
  ChevronDown,
  AlertTriangle,
  CheckCircle,
} from 'lucide-react';
import { getCurrentGameSession, GameSession } from '@/lib/api';

interface SystemMetrics {
  cpuUsage: number;
  memoryUsage: number;
  gpuUsage: number;
  networkLatency: number;
}

export default function Monitor() {
  const [gameSession, setGameSession] = useState<GameSession | null>(null);
  const [systemMetrics, setSystemMetrics] = useState<SystemMetrics>({
    cpuUsage: 45,
    memoryUsage: 62,
    gpuUsage: 78,
    networkLatency: 23,
  });
  const [loading, setLoading] = useState(true);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [refreshInterval, setRefreshInterval] = useState(5);
  const [isOnline, setIsOnline] = useState(navigator.onLine);
  const [lastUpdate, setLastUpdate] = useState<Date>(new Date());
  const [connectionStatus, setConnectionStatus] = useState<'connected' | 'connecting' | 'disconnected'>('connecting');

  useEffect(() => {
    const handleOnline = () => setIsOnline(true);
    const handleOffline = () => setIsOnline(false);

    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);

    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, []);

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const session = await getCurrentGameSession();
      setGameSession(session);
      setLastUpdate(new Date());
      setConnectionStatus('connected');

      // 시뮬레이션된 시스템 메트릭
      setSystemMetrics({
        cpuUsage: 40 + Math.random() * 30,
        memoryUsage: 55 + Math.random() * 20,
        gpuUsage: 70 + Math.random() * 20,
        networkLatency: 15 + Math.random() * 30,
      });
    } catch (error) {
      console.error('Failed to fetch game data:', error);
      setConnectionStatus('disconnected');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();

    if (autoRefresh) {
      const interval = setInterval(fetchData, refreshInterval * 1000);
      return () => clearInterval(interval);
    }
  }, [autoRefresh, refreshInterval, fetchData]);

  const getProgressColor = (value: number) => {
    if (value < 50) return 'bg-green-500';
    if (value < 75) return 'bg-yellow-500';
    return 'bg-red-500';
  };

  const getStatusIcon = () => {
    switch (connectionStatus) {
      case 'connected':
        return <CheckCircle className="h-4 w-4 text-green-400" />;
      case 'connecting':
        return <RefreshCw className="h-4 w-4 text-yellow-400 animate-spin" />;
      case 'disconnected':
        return <AlertTriangle className="h-4 w-4 text-red-400" />;
    }
  };

  const getGamePhaseColor = (phase: string) => {
    switch (phase?.toLowerCase()) {
      case 'early':
        return 'text-green-400 bg-green-500/20';
      case 'mid':
        return 'text-yellow-400 bg-yellow-500/20';
      case 'late':
        return 'text-red-400 bg-red-500/20';
      default:
        return 'text-gray-400 bg-gray-500/20';
    }
  };

  const progressPercentage = gameSession ? (gameSession.duration / 3600) * 100 : 0;

  return (
    <div className="space-y-6">
      {/* 상태 바 */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          {getStatusIcon()}
          <span className="text-sm font-medium">
            {connectionStatus === 'connected' ? '연결됨' : 
             connectionStatus === 'connecting' ? '연결 중...' : '연결 끊김'}
          </span>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setAutoRefresh(!autoRefresh)}
            className={`rounded-lg p-2 transition-colors ${
              autoRefresh ? 'bg-accent text-accent-foreground' : 'bg-secondary text-muted-foreground'
            }`}
          >
            {autoRefresh ? <Pause className="h-4 w-4" /> : <Play className="h-4 w-4" />}
          </button>
          <button
            onClick={fetchData}
            disabled={loading}
            className="rounded-lg bg-secondary p-2 text-muted-foreground hover:bg-secondary/80"
          >
            <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* 새로고침 간격 설정 */}
      <div className="glass rounded-lg border border-white/10 bg-white/5 p-4 backdrop-blur-md">
        <div className="flex items-center justify-between">
          <span className="text-sm font-medium">새로고침 간격</span>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setRefreshInterval(Math.max(1, refreshInterval - 1))}
              className="rounded-lg bg-secondary p-1 hover:bg-secondary/80"
            >
              <ChevronDown className="h-4 w-4" />
            </button>
            <span className="w-12 text-center font-bold">{refreshInterval}초</span>
            <button
              onClick={() => setRefreshInterval(Math.min(60, refreshInterval + 1))}
              className="rounded-lg bg-secondary p-1 hover:bg-secondary/80"
            >
              <ChevronUp className="h-4 w-4" />
            </button>
          </div>
        </div>
      </div>

      {/* 현재 게임 상태 */}
      <div className="glass rounded-xl border border-white/10 bg-white/5 p-6 backdrop-blur-md">
        <div className="flex items-center justify-between mb-4">
          <h3 className="flex items-center gap-2 font-semibold">
            <Activity className="h-5 w-5 text-cyan-400" />
            현재 게임
          </h3>
          {gameSession && (
            <span className={`rounded-full px-3 py-1 text-xs font-semibold ${getGamePhaseColor(gameSession.gamePhase)}`}>
              {gameSession.gamePhase || '대기 중'}
            </span>
          )}
        </div>

        {gameSession ? (
          <div className="space-y-4">
            {/* 맵 및 상대 정보 */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="text-xs text-muted-foreground">맵</p>
                <p className="mt-1 font-semibold">{gameSession.mapName}</p>
              </div>
              <div>
                <p className="text-xs text-muted-foreground">상대 종족</p>
                <p className="mt-1 font-semibold">{gameSession.enemyRace}</p>
              </div>
            </div>

            {/* 게임 시간 */}
            <div>
              <p className="text-xs text-muted-foreground">게임 시간</p>
              <p className="mt-1 text-2xl font-bold text-cyan-400">
                {Math.floor(gameSession.duration / 60)}:{String(gameSession.duration % 60).padStart(2, '0')}
              </p>
            </div>

            {/* 진행 바 */}
            <div>
              <div className="mb-2 flex items-center justify-between">
                <span className="text-xs text-muted-foreground">게임 진행</span>
                <span className="text-xs font-semibold">{Math.min(100, progressPercentage).toFixed(0)}%</span>
              </div>
              <div className="h-2 w-full overflow-hidden rounded-full bg-white/10">
                <div
                  className="h-full bg-gradient-to-r from-cyan-500 to-blue-500 transition-all duration-500"
                  style={{ width: `${Math.min(100, progressPercentage)}%` }}
                />
              </div>
            </div>

            {/* 자원 */}
            <div className="grid grid-cols-3 gap-4">
              <div className="rounded-lg bg-blue-500/10 p-3 text-center">
                <p className="text-xs text-muted-foreground">미네랄</p>
                <p className="mt-1 text-lg font-bold text-blue-400">{gameSession.finalMinerals}</p>
              </div>
              <div className="rounded-lg bg-green-500/10 p-3 text-center">
                <p className="text-xs text-muted-foreground">가스</p>
                <p className="mt-1 text-lg font-bold text-green-400">{gameSession.finalGas}</p>
              </div>
              <div className="rounded-lg bg-yellow-500/10 p-3 text-center">
                <p className="text-xs text-muted-foreground">인구</p>
                <p className="mt-1 text-lg font-bold text-yellow-400">{gameSession.finalSupply}</p>
              </div>
            </div>

            {/* 유닛 통계 */}
            <div className="grid grid-cols-2 gap-4">
              <div className="rounded-lg bg-cyan-500/10 p-3">
                <p className="text-xs text-muted-foreground">유닛 처치</p>
                <p className="mt-1 text-xl font-bold text-cyan-400">{gameSession.unitsKilled}</p>
              </div>
              <div className="rounded-lg bg-red-500/10 p-3">
                <p className="text-xs text-muted-foreground">유닛 손실</p>
                <p className="mt-1 text-xl font-bold text-red-400">{gameSession.unitsLost}</p>
              </div>
            </div>

            {/* K/D 비율 바 */}
            <div>
              <div className="flex justify-between text-xs text-muted-foreground mb-1">
                <span>K/D 비율</span>
                <span>
                  {gameSession.unitsLost > 0 
                    ? (gameSession.unitsKilled / gameSession.unitsLost).toFixed(2) 
                    : gameSession.unitsKilled}
                </span>
              </div>
              <div className="h-2 rounded-full bg-white/10 overflow-hidden">
                <div
                  className="h-full bg-gradient-to-r from-cyan-500 to-green-500 transition-all duration-500"
                  style={{
                    width: `${Math.min(100, (gameSession.unitsKilled / (gameSession.unitsKilled + gameSession.unitsLost + 1)) * 100)}%`,
                  }}
                />
              </div>
            </div>

            {/* 결과 */}
            {gameSession.result && (
              <div className={`rounded-lg p-4 text-center ${
                gameSession.result === 'Victory' ? 'bg-green-500/20' : 'bg-red-500/20'
              }`}>
                <p className={`text-xl font-bold ${
                  gameSession.result === 'Victory' ? 'text-green-400' : 'text-red-400'
                }`}>
                  {gameSession.result === 'Victory' ? '🎉 승리!' : '😢 패배'}
                </p>
              </div>
            )}
          </div>
        ) : (
          <div className="py-8 text-center">
            <Activity className="mx-auto h-12 w-12 text-muted-foreground opacity-50" />
            <p className="mt-4 text-muted-foreground">현재 진행 중인 게임이 없습니다</p>
            <p className="mt-2 text-xs text-muted-foreground">게임이 시작되면 자동으로 업데이트됩니다</p>
          </div>
        )}
      </div>

      {/* 시스템 메트릭 */}
      <div className="glass rounded-xl border border-white/10 bg-white/5 p-6 backdrop-blur-md">
        <h3 className="flex items-center gap-2 font-semibold mb-4">
          <Cpu className="h-5 w-5 text-purple-400" />
          시스템 상태
        </h3>

        <div className="space-y-4">
          {/* CPU */}
          <div>
            <div className="flex justify-between text-sm mb-1">
              <span className="flex items-center gap-2">
                <Cpu className="h-4 w-4 text-blue-400" />
                CPU
              </span>
              <span className="font-semibold">{systemMetrics.cpuUsage.toFixed(1)}%</span>
            </div>
            <div className="h-2 rounded-full bg-white/10 overflow-hidden">
              <div
                className={`h-full transition-all duration-500 ${getProgressColor(systemMetrics.cpuUsage)}`}
                style={{ width: `${systemMetrics.cpuUsage}%` }}
              />
            </div>
          </div>

          {/* Memory */}
          <div>
            <div className="flex justify-between text-sm mb-1">
              <span className="flex items-center gap-2">
                <HardDrive className="h-4 w-4 text-green-400" />
                메모리
              </span>
              <span className="font-semibold">{systemMetrics.memoryUsage.toFixed(1)}%</span>
            </div>
            <div className="h-2 rounded-full bg-white/10 overflow-hidden">
              <div
                className={`h-full transition-all duration-500 ${getProgressColor(systemMetrics.memoryUsage)}`}
                style={{ width: `${systemMetrics.memoryUsage}%` }}
              />
            </div>
          </div>

          {/* GPU */}
          <div>
            <div className="flex justify-between text-sm mb-1">
              <span className="flex items-center gap-2">
                <Zap className="h-4 w-4 text-yellow-400" />
                GPU
              </span>
              <span className="font-semibold">{systemMetrics.gpuUsage.toFixed(1)}%</span>
            </div>
            <div className="h-2 rounded-full bg-white/10 overflow-hidden">
              <div
                className={`h-full transition-all duration-500 ${getProgressColor(systemMetrics.gpuUsage)}`}
                style={{ width: `${systemMetrics.gpuUsage}%` }}
              />
            </div>
          </div>

          {/* Network */}
          <div>
            <div className="flex justify-between text-sm mb-1">
              <span className="flex items-center gap-2">
                {isOnline ? <Wifi className="h-4 w-4 text-cyan-400" /> : <WifiOff className="h-4 w-4 text-red-400" />}
                네트워크 지연
              </span>
              <span className="font-semibold">{systemMetrics.networkLatency.toFixed(0)}ms</span>
            </div>
            <div className="h-2 rounded-full bg-white/10 overflow-hidden">
              <div
                className={`h-full transition-all duration-500 ${
                  systemMetrics.networkLatency < 30 ? 'bg-green-500' :
                  systemMetrics.networkLatency < 60 ? 'bg-yellow-500' : 'bg-red-500'
                }`}
                style={{ width: `${Math.min(100, systemMetrics.networkLatency)}%` }}
              />
            </div>
          </div>
        </div>
      </div>

      {/* 마지막 업데이트 */}
      <div className="text-center text-xs text-muted-foreground">
        <Clock className="inline h-3 w-3 mr-1" />
        마지막 업데이트: {lastUpdate.toLocaleTimeString('ko-KR')}
      </div>
    </div>
  );
}
