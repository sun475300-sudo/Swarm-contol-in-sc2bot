import { useEffect, useState } from 'react';
import { BarChart, Bar, LineChart, Line, PieChart, Pie, Cell, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { getGameSessions, getTrainingEpisodes, GameSession, TrainingEpisode } from '@/lib/api';
import { format } from 'date-fns';
import { ko } from 'date-fns/locale';

export default function Analytics() {
  const [gameSessions, setGameSessions] = useState<GameSession[]>([]);
  const [trainingEpisodes, setTrainingEpisodes] = useState<TrainingEpisode[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      const [games, training] = await Promise.all([
        getGameSessions(20),
        getTrainingEpisodes(20),
      ]);
      setGameSessions(games);
      setTrainingEpisodes(training);
      setLoading(false);
    };

    fetchData();
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="text-center">
          <div className="mb-4 h-8 w-8 animate-spin rounded-full border-4 border-border border-t-accent mx-auto" />
          <p className="text-muted-foreground">데이터 로드 중...</p>
        </div>
      </div>
    );
  }

  // 게임 결과 분석
  const gameResultData = [
    {
      name: '승리',
      value: gameSessions.filter(g => g.result === 'Victory').length,
      fill: '#10b981',
    },
    {
      name: '패배',
      value: gameSessions.filter(g => g.result === 'Defeat').length,
      fill: '#ef4444',
    },
  ];

  // 최근 게임 승률
  const recentGameData = gameSessions.slice().reverse().map((game, index) => ({
    name: `게임 ${index + 1}`,
    result: game.result === 'Victory' ? 1 : 0,
    unitsKilled: game.unitsKilled,
    unitsLost: game.unitsLost,
  }));

  // 학습 진행 데이터
  const trainingData = trainingEpisodes.slice().reverse().map(ep => ({
    episode: ep.episodeNumber,
    reward: ep.totalReward,
    winRate: ep.winRate * 100,
    loss: ep.loss,
  }));

  return (
    <div className="space-y-6">
      {/* 게임 결과 분포 */}
      <div className="glass rounded-lg border border-white/10 bg-white/5 p-6 backdrop-blur-md">
        <h3 className="mb-4 font-semibold">게임 결과 분포</h3>
        <div className="flex flex-col items-center sm:flex-row">
          <div className="flex-1">
            <ResponsiveContainer width="100%" height={200}>
              <PieChart>
                <Pie
                  data={gameResultData}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={80}
                  paddingAngle={5}
                  dataKey="value"
                >
                  {gameResultData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.fill} />
                  ))}
                </Pie>
                <Tooltip
                  contentStyle={{
                    backgroundColor: 'rgba(15, 23, 42, 0.8)',
                    border: '1px solid rgba(255, 255, 255, 0.1)',
                    borderRadius: '0.5rem',
                  }}
                />
              </PieChart>
            </ResponsiveContainer>
          </div>
          <div className="mt-4 space-y-2 sm:mt-0 sm:ml-4">
            {gameResultData.map((item) => (
              <div key={item.name} className="flex items-center gap-2">
                <div
                  className="h-3 w-3 rounded-full"
                  style={{ backgroundColor: item.fill }}
                />
                <span className="text-sm">
                  {item.name}: {item.value}게임
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* 최근 게임 성과 */}
      <div className="glass rounded-lg border border-white/10 bg-white/5 p-6 backdrop-blur-md">
        <h3 className="mb-4 font-semibold">최근 게임 유닛 교환 비율</h3>
        <ResponsiveContainer width="100%" height={250}>
          <BarChart data={recentGameData}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255, 255, 255, 0.1)" />
            <XAxis dataKey="name" stroke="rgba(255, 255, 255, 0.5)" />
            <YAxis stroke="rgba(255, 255, 255, 0.5)" />
            <Tooltip
              contentStyle={{
                backgroundColor: 'rgba(15, 23, 42, 0.8)',
                border: '1px solid rgba(255, 255, 255, 0.1)',
                borderRadius: '0.5rem',
              }}
            />
            <Bar dataKey="unitsKilled" fill="#10b981" name="처치" />
            <Bar dataKey="unitsLost" fill="#ef4444" name="손실" />
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* 학습 진행 */}
      {trainingData.length > 0 && (
        <div className="glass rounded-lg border border-white/10 bg-white/5 p-6 backdrop-blur-md">
          <h3 className="mb-4 font-semibold">학습 진행 - 보상</h3>
          <ResponsiveContainer width="100%" height={250}>
            <LineChart data={trainingData}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255, 255, 255, 0.1)" />
              <XAxis dataKey="episode" stroke="rgba(255, 255, 255, 0.5)" />
              <YAxis stroke="rgba(255, 255, 255, 0.5)" />
              <Tooltip
                contentStyle={{
                  backgroundColor: 'rgba(15, 23, 42, 0.8)',
                  border: '1px solid rgba(255, 255, 255, 0.1)',
                  borderRadius: '0.5rem',
                }}
              />
              <Line
                type="monotone"
                dataKey="reward"
                stroke="#06b6d4"
                dot={false}
                strokeWidth={2}
                name="보상"
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* 최근 게임 목록 */}
      <div className="glass rounded-lg border border-white/10 bg-white/5 p-6 backdrop-blur-md">
        <h3 className="mb-4 font-semibold">최근 게임 기록</h3>
        <div className="space-y-2 max-h-64 overflow-y-auto">
          {gameSessions.slice().reverse().map((game, index) => (
            <div
              key={game.id}
              className="flex items-center justify-between rounded-lg bg-white/5 p-3"
            >
              <div className="flex-1">
                <div className="flex items-center gap-2">
                  <span className="text-xs text-muted-foreground">#{index + 1}</span>
                  <span className="text-sm font-medium">{game.mapName}</span>
                  <span
                    className={`text-xs font-semibold ${
                      game.result === 'Victory'
                        ? 'text-green-400'
                        : 'text-red-400'
                    }`}
                  >
                    {game.result === 'Victory' ? '승' : '패'}
                  </span>
                </div>
                <p className="mt-1 text-xs text-muted-foreground">
                  vs {game.enemyRace} ({game.difficulty})
                </p>
              </div>
              <div className="text-right text-xs">
                <p className="font-semibold">{game.unitsKilled}/{game.unitsLost}</p>
                <p className="text-muted-foreground">
                  {Math.floor(game.duration / 60)}분
                </p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
