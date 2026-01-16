import DashboardLayout from "@/components/DashboardLayout";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { trpc } from "@/lib/trpc";
import { Brain, TrendingUp, Zap } from "lucide-react";
import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

export default function Training() {
  const { data: episodes } = trpc.training.getEpisodes.useQuery({ limit: 50 });
  const { data: trainingStats } = trpc.training.getStats.useQuery();

  // 에피소드 데이터를 차트용으로 변환
  const rewardChartData = episodes
    ?.slice()
    .reverse()
    .map((episode) => ({
      episode: episode.episodeNumber,
      totalReward: episode.totalReward,
      avgReward: episode.averageReward || 0,
    })) || [];

  const winRateChartData = episodes
    ?.slice()
    .reverse()
    .map((episode) => ({
      episode: episode.episodeNumber,
      winRate: (episode.winRate || 0) * 100,
    })) || [];

  const lossChartData = episodes
    ?.slice()
    .reverse()
    .filter((episode) => episode.loss !== null)
    .map((episode) => ({
      episode: episode.episodeNumber,
      loss: episode.loss || 0,
    })) || [];

  const stats = [
    {
      title: "총 에피소드",
      value: trainingStats?.totalEpisodes || 0,
      icon: Brain,
      color: "text-chart-1",
    },
    {
      title: "평균 보상",
      value: trainingStats?.avgReward?.toFixed(2) || "0.00",
      icon: TrendingUp,
      color: "text-chart-2",
    },
    {
      title: "평균 승률",
      value: trainingStats?.avgWinRate
        ? `${(trainingStats.avgWinRate * 100).toFixed(1)}%`
        : "0%",
      icon: Zap,
      color: "text-chart-3",
    },
    {
      title: "총 게임 수",
      value: trainingStats?.totalGames || 0,
      icon: Brain,
      color: "text-chart-4",
    },
  ];

  return (
    <DashboardLayout>
      <div className="space-y-8 animate-slide-up">
        {/* 헤더 */}
        <div className="space-y-2">
          <h1 className="text-4xl font-bold tracking-tight glow-text">
            학습 진행 상황
          </h1>
          <p className="text-muted-foreground text-lg">
            강화학습 에피소드와 성능 개선 추이를 추적합니다
          </p>
        </div>

        {/* 통계 카드 */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {stats.map((stat, index) => {
            const Icon = stat.icon;
            return (
              <Card key={index} className="glass-card hover:glow-effect transition-all">
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium">
                    {stat.title}
                  </CardTitle>
                  <Icon className={`w-4 h-4 ${stat.color}`} />
                </CardHeader>
                <CardContent>
                  <div className={`text-3xl font-bold ${stat.color}`}>
                    {stat.value}
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>

        {/* 보상 함수 그래프 */}
        {rewardChartData.length > 0 && (
          <Card className="glass-card">
            <CardHeader>
              <CardTitle>보상 함수 추이</CardTitle>
              <CardDescription>에피소드별 총 보상 및 평균 보상</CardDescription>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={350}>
                <LineChart data={rewardChartData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
                  <XAxis
                    dataKey="episode"
                    stroke="rgba(255,255,255,0.5)"
                    label={{ value: "에피소드", position: "insideBottom", offset: -5 }}
                  />
                  <YAxis stroke="rgba(255,255,255,0.5)" />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "rgba(0,0,0,0.8)",
                      border: "1px solid rgba(255,255,255,0.1)",
                      borderRadius: "8px",
                    }}
                  />
                  <Legend />
                  <Line
                    type="monotone"
                    dataKey="totalReward"
                    stroke="hsl(var(--chart-1))"
                    strokeWidth={2}
                    dot={{ r: 4 }}
                    name="총 보상"
                  />
                  <Line
                    type="monotone"
                    dataKey="avgReward"
                    stroke="hsl(var(--chart-2))"
                    strokeWidth={2}
                    dot={{ r: 4 }}
                    name="평균 보상"
                  />
                </LineChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        )}

        {/* 승률 추이 그래프 */}
        {winRateChartData.length > 0 && (
          <Card className="glass-card">
            <CardHeader>
              <CardTitle>승률 개선 추이</CardTitle>
              <CardDescription>에피소드별 승률 변화</CardDescription>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={350}>
                <LineChart data={winRateChartData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
                  <XAxis
                    dataKey="episode"
                    stroke="rgba(255,255,255,0.5)"
                    label={{ value: "에피소드", position: "insideBottom", offset: -5 }}
                  />
                  <YAxis
                    stroke="rgba(255,255,255,0.5)"
                    label={{ value: "승률 (%)", angle: -90, position: "insideLeft" }}
                  />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "rgba(0,0,0,0.8)",
                      border: "1px solid rgba(255,255,255,0.1)",
                      borderRadius: "8px",
                    }}
                    formatter={(value: number) => `${value.toFixed(1)}%`}
                  />
                  <Legend />
                  <Line
                    type="monotone"
                    dataKey="winRate"
                    stroke="hsl(var(--chart-3))"
                    strokeWidth={3}
                    dot={{ r: 5 }}
                    name="승률"
                  />
                </LineChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        )}

        {/* Loss 함수 그래프 */}
        {lossChartData.length > 0 && (
          <Card className="glass-card">
            <CardHeader>
              <CardTitle>Loss 함수</CardTitle>
              <CardDescription>학습 손실 함수의 변화</CardDescription>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={350}>
                <LineChart data={lossChartData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
                  <XAxis
                    dataKey="episode"
                    stroke="rgba(255,255,255,0.5)"
                    label={{ value: "에피소드", position: "insideBottom", offset: -5 }}
                  />
                  <YAxis stroke="rgba(255,255,255,0.5)" />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "rgba(0,0,0,0.8)",
                      border: "1px solid rgba(255,255,255,0.1)",
                      borderRadius: "8px",
                    }}
                  />
                  <Legend />
                  <Line
                    type="monotone"
                    dataKey="loss"
                    stroke="hsl(var(--chart-4))"
                    strokeWidth={2}
                    dot={{ r: 4 }}
                    name="Loss"
                  />
                </LineChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        )}

        {/* 최근 에피소드 목록 */}
        <Card className="glass-card">
          <CardHeader>
            <CardTitle>최근 학습 에피소드</CardTitle>
            <CardDescription>최근 10개 에피소드의 상세 정보</CardDescription>
          </CardHeader>
          <CardContent>
            {episodes && episodes.length > 0 ? (
              <div className="space-y-4">
                {episodes.slice(0, 10).map((episode) => (
                  <div
                    key={episode.id}
                    className="p-4 rounded-lg bg-secondary/50 hover:bg-secondary transition-colors"
                  >
                    <div className="flex items-center justify-between mb-2">
                      <h3 className="font-semibold text-lg">
                        에피소드 #{episode.episodeNumber}
                      </h3>
                      <span className="text-sm text-muted-foreground">
                        {new Date(episode.createdAt).toLocaleDateString()}
                      </span>
                    </div>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                      <div>
                        <p className="text-muted-foreground">총 보상</p>
                        <p className="font-semibold text-chart-1">
                          {episode.totalReward.toFixed(2)}
                        </p>
                      </div>
                      <div>
                        <p className="text-muted-foreground">승률</p>
                        <p className="font-semibold text-chart-2">
                          {episode.winRate
                            ? `${(episode.winRate * 100).toFixed(1)}%`
                            : "-"}
                        </p>
                      </div>
                      <div>
                        <p className="text-muted-foreground">게임 수</p>
                        <p className="font-semibold">{episode.gamesPlayed}</p>
                      </div>
                      <div>
                        <p className="text-muted-foreground">Loss</p>
                        <p className="font-semibold text-chart-4">
                          {episode.loss?.toFixed(4) || "-"}
                        </p>
                      </div>
                    </div>
                    {episode.notes && (
                      <p className="mt-2 text-sm text-muted-foreground">
                        {episode.notes}
                      </p>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-12 text-muted-foreground">
                아직 학습 에피소드가 없습니다
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </DashboardLayout>
  );
}
