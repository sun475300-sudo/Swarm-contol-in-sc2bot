import { useEffect, useState } from 'react';
import {
  TrendingUp,
  TrendingDown,
  Trophy,
  Swords,
  Brain,
  Activity,
  Zap,
  Target,
  Clock,
  Wifi,
  WifiOff,
  RefreshCw,
  ChevronRight,
  Gamepad2,
} from 'lucide-react';
import { getGameStats, getTrainingStats, getArenaStats, getRecentGames, GameStats, TrainingStats, ArenaStats, GameSession } from '@/lib/api';
import { getRepositoryStats, formatRelativeTime, GitHubCommit } from '@/lib/github';

export default function Dashboard() {
  const [gameStats, setGameStats] = useState<GameStats | null>(null);
  const [trainingStats, setTrainingStats] = useState<TrainingStats | null>(null);
  const [arenaStats, setArenaStats] = useState<ArenaStats | null>(null);
  const [recentGames, setRecentGames] = useState<GameSession[]>([]);
  const [recentCommits, setRecentCommits] = useState<GitHubCommit[]>([]);
  const [loading, setLoading] = useState(true);
  const [isOnline, setIsOnline] = useState(navigator.onLine);
  const [lastUpdate, setLastUpdate] = useState<Date>(new Date());

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

  const fetchData = async () => {
    setLoading(true);
    try {
      const [games, training, arena, recent, githubStats] = await Promise.all([
        getGameStats(),
        getTrainingStats(),
        getArenaStats(),
        getRecentGames(5),
        getRepositoryStats().catch(() => ({ recentCommits: [] })),
      ]);

      setGameStats(games);
      setTrainingStats(training);
      setArenaStats(arena);
      setRecentGames(recent);
      setRecentCommits(githubStats.recentCommits?.slice(0, 3) || []);
      setLastUpdate(new Date());
    } catch (error) {
      console.error('Failed to fetch dashboard data:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 30000); // 30초마다 새로고침
    return () => clearInterval(interval);
  }, []);

  if (loading && !gameStats) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="text-center">
          <div className="mb-4 h-8 w-8 animate-spin rounded-full border-4 border-border border-t-accent mx-auto" />
          <p className="text-muted-foreground">대시보드 로드 중...</p>
        </div>
      </div>
    );
  }

  const winRate = gameStats ? gameStats.winRate * 100 : 0;

  return (
    <div className="space-y-6">
      {/* 상태 바 */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          {isOnline ? (
            <Wifi className="h-4 w-4 text-green-400" />
          ) : (
            <WifiOff className="h-4 w-4 text-red-400" />
          )}
          <span className="text-xs text-muted-foreground">
            {isOnline ? '온라인' : '오프라인'}
          </span>
        </div>
        <div className="flex items-center gap-2">
          <Clock className="h-4 w-4 text-muted-foreground" />
          <span className="text-xs text-muted-foreground">
            {lastUpdate.toLocaleTimeString('ko-KR')}
          </span>
          <button
            onClick={fetchData}
            className="rounded-lg p-1 hover:bg-secondary"
            disabled={loading}
          >
            <RefreshCw className={`h-4 w-4 text-muted-foreground ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* 주요 지표 카드 */}
      <div className="grid grid-cols-2 gap-4">
        {/* 승률 */}
        <div className="glass rounded-xl border border-white/10 bg-gradient-to-br from-cyan-500/10 to-blue-500/10 p-4 backdrop-blur-md">
          <div className="flex items-center justify-between">
            <Trophy className="h-5 w-5 text-cyan-400" />
            <span className="text-xs text-muted-foreground">
              {gameStats?.wins || 0}승 {gameStats?.losses || 0}패
            </span>
          </div>
          <p className="mt-3 text-2xl font-bold">{winRate.toFixed(1)}%</p>
          <p className="mt-1 text-xs text-muted-foreground">승률</p>
        </div>

        {/* ELO */}
        <div className="glass rounded-xl border border-white/10 bg-gradient-to-br from-purple-500/10 to-pink-500/10 p-4 backdrop-blur-md">
          <div className="flex items-center justify-between">
            <Target className="h-5 w-5 text-purple-400" />
            <span className="text-xs text-muted-foreground">
              최고: {arenaStats?.highestElo || 0}
            </span>
          </div>
          <p className="mt-3 text-2xl font-bold">{arenaStats?.currentElo || 0}</p>
          <p className="mt-1 text-xs text-muted-foreground">Arena ELO</p>
        </div>

        {/* 학습 보상 */}
        <div className="glass rounded-xl border border-white/10 bg-gradient-to-br from-green-500/10 to-emerald-500/10 p-4 backdrop-blur-md">
          <div className="flex items-center justify-between">
            <Brain className="h-5 w-5 text-green-400" />
            <span className="text-xs text-muted-foreground">
              평균: {trainingStats?.averageReward.toFixed(1) || 0}
            </span>
          </div>
          <p className="mt-3 text-2xl font-bold">{trainingStats?.latestReward.toFixed(1) || 0}</p>
          <p className="mt-1 text-xs text-muted-foreground">최근 보상</p>
        </div>

        {/* 총 게임 수 */}
        <div className="glass rounded-xl border border-white/10 bg-gradient-to-br from-orange-500/10 to-yellow-500/10 p-4 backdrop-blur-md">
          <div className="flex items-center justify-between">
            <Swords className="h-5 w-5 text-orange-400" />
            <span className="text-xs text-muted-foreground">
              에피소드: {trainingStats?.totalEpisodes || 0}
            </span>
          </div>
          <p className="mt-3 text-2xl font-bold">{gameStats?.totalGames || 0}</p>
          <p className="mt-1 text-xs text-muted-foreground">총 게임</p>
        </div>
      </div>

      {/* 실시간 상태 */}
      <div className="glass rounded-xl border border-white/10 bg-white/5 p-4 backdrop-blur-md">
        <div className="flex items-center justify-between">
          <h3 className="flex items-center gap-2 font-semibold">
            <Activity className="h-4 w-4 text-cyan-400" />
            실시간 상태
          </h3>
          <div className="flex items-center gap-2">
            <span className="relative flex h-2 w-2">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-green-400 opacity-75"></span>
              <span className="relative inline-flex h-2 w-2 rounded-full bg-green-500"></span>
            </span>
            <span className="text-xs text-green-400">활성</span>
          </div>
        </div>
        <div className="mt-4 grid grid-cols-3 gap-4 text-center">
          <div>
            <p className="text-lg font-bold text-cyan-400">대기 중</p>
            <p className="text-xs text-muted-foreground">게임 상태</p>
          </div>
          <div>
            <p className="text-lg font-bold text-purple-400">학습 중</p>
            <p className="text-xs text-muted-foreground">AI 상태</p>
          </div>
          <div>
            <p className="text-lg font-bold text-green-400">정상</p>
            <p className="text-xs text-muted-foreground">시스템</p>
          </div>
        </div>
      </div>

      {/* 최근 게임 */}
      <div className="glass rounded-xl border border-white/10 bg-white/5 p-4 backdrop-blur-md">
        <div className="flex items-center justify-between">
          <h3 className="flex items-center gap-2 font-semibold">
            <Swords className="h-4 w-4 text-orange-400" />
            최근 게임
          </h3>
          <button className="flex items-center gap-1 text-xs text-accent hover:underline">
            전체 보기 <ChevronRight className="h-3 w-3" />
          </button>
        </div>
        <div className="mt-4 space-y-2">
          {recentGames.length === 0 ? (
            <p className="text-center text-sm text-muted-foreground py-4">
              최근 게임 기록이 없습니다
            </p>
          ) : (
            recentGames.map((game) => (
              <div
                key={game.id}
                className="flex items-center justify-between rounded-lg bg-white/5 p-3"
              >
                <div className="flex items-center gap-3">
                  <div
                    className={`flex h-8 w-8 items-center justify-center rounded-full ${
                      game.result === 'Victory'
                        ? 'bg-green-500/20 text-green-400'
                        : 'bg-red-500/20 text-red-400'
                    }`}
                  >
                    {game.result === 'Victory' ? (
                      <Trophy className="h-4 w-4" />
                    ) : (
                      <Swords className="h-4 w-4" />
                    )}
                  </div>
                  <div>
                    <p className="text-sm font-medium">{game.mapName}</p>
                    <p className="text-xs text-muted-foreground">
                      vs {game.enemyRace} • {Math.floor(game.duration / 60)}분
                    </p>
                  </div>
                </div>
                <div className="text-right">
                  <p
                    className={`text-sm font-semibold ${
                      game.result === 'Victory' ? 'text-green-400' : 'text-red-400'
                    }`}
                  >
                    {game.result === 'Victory' ? '승리' : '패배'}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    {game.unitsKilled}K / {game.unitsLost}D
                  </p>
                </div>
              </div>
            ))
          )}
        </div>
      </div>

      {/* GitHub 업데이트 */}
      {recentCommits.length > 0 && (
        <div className="glass rounded-xl border border-white/10 bg-white/5 p-4 backdrop-blur-md">
          <div className="flex items-center justify-between">
            <h3 className="flex items-center gap-2 font-semibold">
              <Zap className="h-4 w-4 text-yellow-400" />
              GitHub 업데이트
            </h3>
            <button className="flex items-center gap-1 text-xs text-accent hover:underline">
              전체 보기 <ChevronRight className="h-3 w-3" />
            </button>
          </div>
          <div className="mt-4 space-y-2">
            {recentCommits.map((commit) => (
              <a
                key={commit.sha}
                href={commit.html_url}
                target="_blank"
                rel="noopener noreferrer"
                className="block rounded-lg bg-white/5 p-3 hover:bg-white/10"
              >
                <p className="text-sm font-medium line-clamp-1">
                  {commit.message.split('\n')[0]}
                </p>
                <p className="mt-1 text-xs text-muted-foreground">
                  {commit.author.name} • {formatRelativeTime(commit.author.date)}
                </p>
              </a>
            ))}
          </div>
        </div>
      )}

      {/* 빠른 정보 */}
      <div className="grid grid-cols-2 gap-4">
        <div className="glass rounded-lg border border-white/10 bg-white/5 p-4 backdrop-blur-md">
          <p className="text-xs text-muted-foreground">총 유닛 처치</p>
          <p className="mt-2 text-xl font-bold text-cyan-400">
            {gameStats?.totalUnitsKilled || 0}
          </p>
        </div>
        <div className="glass rounded-lg border border-white/10 bg-white/5 p-4 backdrop-blur-md">
          <p className="text-xs text-muted-foreground">총 유닛 손실</p>
          <p className="mt-2 text-xl font-bold text-orange-400">
            {gameStats?.totalUnitsLost || 0}
          </p>
        </div>
      </div>

      {/* 빠른 액션 */}
      <div className="grid grid-cols-2 gap-4">
        <button className="glass flex items-center justify-center gap-2 rounded-xl border border-white/10 bg-gradient-to-br from-cyan-500/20 to-blue-500/20 p-4 font-medium text-cyan-400 backdrop-blur-md hover:from-cyan-500/30 hover:to-blue-500/30 transition-all">
          <Activity className="h-5 w-5" />
          모니터링
        </button>
        <button className="glass flex items-center justify-center gap-2 rounded-xl border border-white/10 bg-gradient-to-br from-purple-500/20 to-pink-500/20 p-4 font-medium text-purple-400 backdrop-blur-md hover:from-purple-500/30 hover:to-pink-500/30 transition-all">
          <Brain className="h-5 w-5" />
          학습 현황
        </button>
      </div>
    </div>
  );
}
