import { useEffect, useState } from 'react';
import {
  Play,
  Pause,
  SkipBack,
  SkipForward,
  Clock,
  Trophy,
  Swords,
  MapPin,
  Users,
  ChevronRight,
  Download,
  Share2,
  Filter,
  Search,
} from 'lucide-react';
import { getRecentGames, GameSession } from '@/lib/api';

interface ReplayEvent {
  time: number;
  type: 'build' | 'attack' | 'defend' | 'expand' | 'tech';
  description: string;
}

export default function Replays() {
  const [games, setGames] = useState<GameSession[]>([]);
  const [selectedGame, setSelectedGame] = useState<GameSession | null>(null);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [filterResult, setFilterResult] = useState<'all' | 'Victory' | 'Defeat'>('all');
  
  // 리플레이 재생 상태
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [playbackSpeed, setPlaybackSpeed] = useState(1);

  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      try {
        const gamesData = await getRecentGames(50);
        setGames(gamesData);
      } catch (error) {
        console.error('Failed to fetch games:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  // 리플레이 재생 시뮬레이션
  useEffect(() => {
    if (isPlaying && selectedGame) {
      const interval = setInterval(() => {
        setCurrentTime(prev => {
          if (prev >= selectedGame.duration) {
            setIsPlaying(false);
            return selectedGame.duration;
          }
          return prev + playbackSpeed;
        });
      }, 1000);
      return () => clearInterval(interval);
    }
  }, [isPlaying, selectedGame, playbackSpeed]);

  // 필터링된 게임 목록
  const filteredGames = games.filter(game => {
    const matchesSearch = game.mapName.toLowerCase().includes(searchQuery.toLowerCase()) ||
                         game.enemyRace.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesFilter = filterResult === 'all' || game.result === filterResult;
    return matchesSearch && matchesFilter;
  });

  // 시뮬레이션된 이벤트 타임라인
  const generateEvents = (game: GameSession): ReplayEvent[] => {
    const events: ReplayEvent[] = [];
    const duration = game.duration;
    
    // 초반 이벤트
    events.push({ time: 30, type: 'build', description: '첫 번째 일꾼 생산' });
    events.push({ time: 60, type: 'build', description: '스포닝 풀 건설 시작' });
    events.push({ time: 120, type: 'expand', description: '자연 확장 시작' });
    
    // 중반 이벤트
    if (duration > 300) {
      events.push({ time: 180, type: 'tech', description: '레어 업그레이드' });
      events.push({ time: 240, type: 'build', description: '로치 생산 시작' });
      events.push({ time: 300, type: 'attack', description: '첫 번째 공격 시작' });
    }
    
    // 후반 이벤트
    if (duration > 600) {
      events.push({ time: 450, type: 'expand', description: '3번째 확장' });
      events.push({ time: 600, type: 'tech', description: '하이브 업그레이드' });
      events.push({ time: 720, type: 'attack', description: '대규모 공격' });
    }
    
    // 게임 종료
    events.push({ 
      time: duration, 
      type: game.result === 'Victory' ? 'attack' : 'defend', 
      description: game.result === 'Victory' ? '승리!' : '패배' 
    });
    
    return events.filter(e => e.time <= duration);
  };

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${String(secs).padStart(2, '0')}`;
  };

  const getEventIcon = (type: string) => {
    switch (type) {
      case 'build': return '🏗️';
      case 'attack': return '⚔️';
      case 'defend': return '🛡️';
      case 'expand': return '🏠';
      case 'tech': return '🔬';
      default: return '📍';
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="text-center">
          <div className="mb-4 h-8 w-8 animate-spin rounded-full border-4 border-border border-t-accent mx-auto" />
          <p className="text-muted-foreground">리플레이 로드 중...</p>
        </div>
      </div>
    );
  }

  if (selectedGame) {
    const events = generateEvents(selectedGame);
    const currentEvents = events.filter(e => e.time <= currentTime);
    
    return (
      <div className="space-y-6">
        {/* 뒤로 가기 */}
        <button
          onClick={() => {
            setSelectedGame(null);
            setCurrentTime(0);
            setIsPlaying(false);
          }}
          className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground"
        >
          ← 목록으로 돌아가기
        </button>

        {/* 게임 정보 */}
        <div className="glass rounded-xl border border-white/10 bg-white/5 p-6 backdrop-blur-md">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-bold">{selectedGame.mapName}</h2>
            <span className={`rounded-full px-3 py-1 text-sm font-semibold ${
              selectedGame.result === 'Victory' 
                ? 'bg-green-500/20 text-green-400' 
                : 'bg-red-500/20 text-red-400'
            }`}>
              {selectedGame.result === 'Victory' ? '승리' : '패배'}
            </span>
          </div>
          
          <div className="grid grid-cols-3 gap-4 text-center">
            <div>
              <p className="text-xs text-muted-foreground">상대</p>
              <p className="font-semibold">{selectedGame.enemyRace}</p>
            </div>
            <div>
              <p className="text-xs text-muted-foreground">게임 시간</p>
              <p className="font-semibold">{formatTime(selectedGame.duration)}</p>
            </div>
            <div>
              <p className="text-xs text-muted-foreground">K/D</p>
              <p className="font-semibold">{selectedGame.unitsKilled}/{selectedGame.unitsLost}</p>
            </div>
          </div>
        </div>

        {/* 재생 컨트롤 */}
        <div className="glass rounded-xl border border-white/10 bg-white/5 p-6 backdrop-blur-md">
          <div className="flex items-center justify-between mb-4">
            <span className="text-lg font-bold text-cyan-400">{formatTime(currentTime)}</span>
            <span className="text-sm text-muted-foreground">{formatTime(selectedGame.duration)}</span>
          </div>
          
          {/* 진행 바 */}
          <div className="relative mb-4">
            <div className="h-2 rounded-full bg-white/10 overflow-hidden">
              <div
                className="h-full bg-gradient-to-r from-cyan-500 to-blue-500 transition-all duration-300"
                style={{ width: `${(currentTime / selectedGame.duration) * 100}%` }}
              />
            </div>
            {/* 이벤트 마커 */}
            {events.map((event, index) => (
              <div
                key={index}
                className="absolute top-0 w-1 h-2 bg-yellow-400 rounded-full transform -translate-x-1/2"
                style={{ left: `${(event.time / selectedGame.duration) * 100}%` }}
                title={event.description}
              />
            ))}
          </div>
          
          {/* 컨트롤 버튼 */}
          <div className="flex items-center justify-center gap-4">
            <button
              onClick={() => setCurrentTime(Math.max(0, currentTime - 30))}
              className="rounded-full bg-secondary p-3 hover:bg-secondary/80"
            >
              <SkipBack className="h-5 w-5" />
            </button>
            <button
              onClick={() => setIsPlaying(!isPlaying)}
              className="rounded-full bg-accent p-4 text-accent-foreground hover:bg-accent/90"
            >
              {isPlaying ? <Pause className="h-6 w-6" /> : <Play className="h-6 w-6" />}
            </button>
            <button
              onClick={() => setCurrentTime(Math.min(selectedGame.duration, currentTime + 30))}
              className="rounded-full bg-secondary p-3 hover:bg-secondary/80"
            >
              <SkipForward className="h-5 w-5" />
            </button>
          </div>
          
          {/* 재생 속도 */}
          <div className="flex items-center justify-center gap-2 mt-4">
            {[0.5, 1, 2, 4].map(speed => (
              <button
                key={speed}
                onClick={() => setPlaybackSpeed(speed)}
                className={`rounded-lg px-3 py-1 text-sm font-medium transition-colors ${
                  playbackSpeed === speed
                    ? 'bg-accent text-accent-foreground'
                    : 'bg-secondary text-muted-foreground hover:bg-secondary/80'
                }`}
              >
                {speed}x
              </button>
            ))}
          </div>
        </div>

        {/* 이벤트 타임라인 */}
        <div className="glass rounded-xl border border-white/10 bg-white/5 p-6 backdrop-blur-md">
          <h3 className="font-semibold mb-4">이벤트 타임라인</h3>
          <div className="space-y-3 max-h-64 overflow-y-auto">
            {currentEvents.map((event, index) => (
              <div
                key={index}
                className={`flex items-center gap-3 rounded-lg p-3 transition-all ${
                  event.time <= currentTime ? 'bg-white/10' : 'bg-white/5 opacity-50'
                }`}
              >
                <span className="text-xl">{getEventIcon(event.type)}</span>
                <div className="flex-1">
                  <p className="text-sm font-medium">{event.description}</p>
                  <p className="text-xs text-muted-foreground">{formatTime(event.time)}</p>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* 액션 버튼 */}
        <div className="grid grid-cols-2 gap-4">
          <button className="glass flex items-center justify-center gap-2 rounded-xl border border-white/10 bg-white/5 p-4 font-medium backdrop-blur-md hover:bg-white/10">
            <Download className="h-5 w-5" />
            다운로드
          </button>
          <button className="glass flex items-center justify-center gap-2 rounded-xl border border-white/10 bg-white/5 p-4 font-medium backdrop-blur-md hover:bg-white/10">
            <Share2 className="h-5 w-5" />
            공유
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <h2 className="text-xl font-bold flex items-center gap-2">
        <Play className="h-5 w-5 text-cyan-400" />
        리플레이
      </h2>

      {/* 검색 및 필터 */}
      <div className="space-y-4">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <input
            type="text"
            placeholder="맵 이름 또는 종족 검색..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full rounded-lg bg-secondary py-3 pl-10 pr-4 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-accent"
          />
        </div>
        
        <div className="flex gap-2">
          {(['all', 'Victory', 'Defeat'] as const).map(filter => (
            <button
              key={filter}
              onClick={() => setFilterResult(filter)}
              className={`rounded-lg px-4 py-2 text-sm font-medium transition-colors ${
                filterResult === filter
                  ? 'bg-accent text-accent-foreground'
                  : 'bg-secondary text-muted-foreground hover:bg-secondary/80'
              }`}
            >
              {filter === 'all' ? '전체' : filter === 'Victory' ? '승리' : '패배'}
            </button>
          ))}
        </div>
      </div>

      {/* 게임 목록 */}
      <div className="space-y-3">
        {filteredGames.length === 0 ? (
          <div className="glass rounded-xl border border-white/10 bg-white/5 p-8 text-center backdrop-blur-md">
            <Play className="mx-auto h-12 w-12 text-muted-foreground opacity-50" />
            <p className="mt-4 text-muted-foreground">리플레이가 없습니다</p>
          </div>
        ) : (
          filteredGames.map((game) => (
            <button
              key={game.id}
              onClick={() => {
                setSelectedGame(game);
                setCurrentTime(0);
                setIsPlaying(false);
              }}
              className="w-full glass rounded-xl border border-white/10 bg-white/5 p-4 backdrop-blur-md hover:bg-white/10 transition-all text-left"
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-4">
                  <div className={`flex h-12 w-12 items-center justify-center rounded-full ${
                    game.result === 'Victory'
                      ? 'bg-green-500/20 text-green-400'
                      : 'bg-red-500/20 text-red-400'
                  }`}>
                    {game.result === 'Victory' ? (
                      <Trophy className="h-6 w-6" />
                    ) : (
                      <Swords className="h-6 w-6" />
                    )}
                  </div>
                  <div>
                    <p className="font-semibold">{game.mapName}</p>
                    <div className="flex items-center gap-3 text-xs text-muted-foreground mt-1">
                      <span className="flex items-center gap-1">
                        <Users className="h-3 w-3" />
                        vs {game.enemyRace}
                      </span>
                      <span className="flex items-center gap-1">
                        <Clock className="h-3 w-3" />
                        {formatTime(game.duration)}
                      </span>
                    </div>
                  </div>
                </div>
                <ChevronRight className="h-5 w-5 text-muted-foreground" />
              </div>
            </button>
          ))
        )}
      </div>
    </div>
  );
}
