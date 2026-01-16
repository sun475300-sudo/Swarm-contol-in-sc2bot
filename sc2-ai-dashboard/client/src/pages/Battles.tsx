import DashboardLayout from "@/components/DashboardLayout";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { trpc } from "@/lib/trpc";
import { BarChart3, TrendingDown, TrendingUp } from "lucide-react";
import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

export default function Battles() {
  const { data: gameSessions } = trpc.game.getSessions.useQuery({ limit: 20 });
  const { data: gameStats } = trpc.game.getStats.useQuery();

  const winRate = gameStats?.totalGames
    ? (Number(gameStats.wins) / Number(gameStats.totalGames)) * 100
    : 0;

  const lossRate = 100 - winRate;

  // 최근 게임 결과를 차트 데이터로 변환
  const chartData = gameSessions
    ?.filter((session) => session.result !== "InProgress")
    .slice(0, 10)
    .reverse()
    .map((session, index) => ({
      name: `게임 ${index + 1}`,
      승리: session.result === "Victory" ? 1 : 0,
      패배: session.result === "Defeat" ? 1 : 0,
      처치: session.unitsKilled || 0,
      손실: session.unitsLost || 0,
    })) || [];

  const stats = [
    {
      title: "총 게임 수",
      value: gameStats?.totalGames || 0,
      icon: BarChart3,
      color: "text-chart-1",
    },
    {
      title: "승리",
      value: gameStats?.wins || 0,
      icon: TrendingUp,
      color: "text-green-400",
    },
    {
      title: "패배",
      value: gameStats?.losses || 0,
      icon: TrendingDown,
      color: "text-red-400",
    },
    {
      title: "승률",
      value: `${winRate.toFixed(1)}%`,
      icon: BarChart3,
      color: "text-chart-2",
    },
  ];

  return (
    <DashboardLayout>
      <div className="space-y-8 animate-slide-up">
        {/* 헤더 */}
        <div className="space-y-2">
          <h1 className="text-4xl font-bold tracking-tight glow-text">
            전투 분석
          </h1>
          <p className="text-muted-foreground text-lg">
            게임 통계와 전투 결과를 분석합니다
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

        {/* 승률 차트 */}
        <Card className="glass-card">
          <CardHeader>
            <CardTitle>승률 분석</CardTitle>
            <CardDescription>승리와 패배 비율</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
              <div className="space-y-4">
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm font-medium">승리</span>
                    <span className="text-sm font-bold text-green-400">
                      {winRate.toFixed(1)}%
                    </span>
                  </div>
                  <div className="h-4 bg-secondary rounded-full overflow-hidden">
                    <div
                      className="h-full bg-green-400 transition-all"
                      style={{ width: `${winRate}%` }}
                    />
                  </div>
                </div>
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm font-medium">패배</span>
                    <span className="text-sm font-bold text-red-400">
                      {lossRate.toFixed(1)}%
                    </span>
                  </div>
                  <div className="h-4 bg-secondary rounded-full overflow-hidden">
                    <div
                      className="h-full bg-red-400 transition-all"
                      style={{ width: `${lossRate}%` }}
                    />
                  </div>
                </div>
              </div>
              <div className="flex items-center justify-center">
                <div className="relative w-48 h-48">
                  <svg className="w-full h-full transform -rotate-90">
                    <circle
                      cx="96"
                      cy="96"
                      r="80"
                      stroke="currentColor"
                      strokeWidth="16"
                      fill="none"
                      className="text-secondary"
                    />
                    <circle
                      cx="96"
                      cy="96"
                      r="80"
                      stroke="currentColor"
                      strokeWidth="16"
                      fill="none"
                      strokeDasharray={`${(winRate / 100) * 502.65} 502.65`}
                      className="text-green-400 transition-all"
                    />
                  </svg>
                  <div className="absolute inset-0 flex items-center justify-center">
                    <div className="text-center">
                      <div className="text-3xl font-bold text-green-400">
                        {winRate.toFixed(1)}%
                      </div>
                      <div className="text-sm text-muted-foreground">승률</div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* 최근 게임 결과 차트 */}
        {chartData.length > 0 && (
          <Card className="glass-card">
            <CardHeader>
              <CardTitle>최근 게임 결과</CardTitle>
              <CardDescription>최근 10게임의 승패 기록</CardDescription>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
                  <XAxis dataKey="name" stroke="rgba(255,255,255,0.5)" />
                  <YAxis stroke="rgba(255,255,255,0.5)" />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "rgba(0,0,0,0.8)",
                      border: "1px solid rgba(255,255,255,0.1)",
                      borderRadius: "8px",
                    }}
                  />
                  <Legend />
                  <Bar dataKey="승리" fill="#4ade80" />
                  <Bar dataKey="패배" fill="#f87171" />
                </BarChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        )}

        {/* 유닛 교환 비율 차트 */}
        {chartData.length > 0 && (
          <Card className="glass-card">
            <CardHeader>
              <CardTitle>유닛 교환 비율</CardTitle>
              <CardDescription>처치한 유닛 vs 잃은 유닛</CardDescription>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
                  <XAxis dataKey="name" stroke="rgba(255,255,255,0.5)" />
                  <YAxis stroke="rgba(255,255,255,0.5)" />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "rgba(0,0,0,0.8)",
                      border: "1px solid rgba(255,255,255,0.1)",
                      borderRadius: "8px",
                    }}
                  />
                  <Legend />
                  <Bar dataKey="처치" fill="hsl(var(--chart-1))" />
                  <Bar dataKey="손실" fill="hsl(var(--chart-2))" />
                </BarChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        )}

        {/* 최근 게임 목록 */}
        <Card className="glass-card">
          <CardHeader>
            <CardTitle>최근 게임 기록</CardTitle>
            <CardDescription>최근 20게임의 상세 기록</CardDescription>
          </CardHeader>
          <CardContent>
            {gameSessions && gameSessions.length > 0 ? (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>맵</TableHead>
                    <TableHead>상대 종족</TableHead>
                    <TableHead>난이도</TableHead>
                    <TableHead>결과</TableHead>
                    <TableHead>처치</TableHead>
                    <TableHead>손실</TableHead>
                    <TableHead>시간</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {gameSessions.map((session) => (
                    <TableRow key={session.id}>
                      <TableCell className="font-medium">{session.mapName}</TableCell>
                      <TableCell>{session.enemyRace}</TableCell>
                      <TableCell>{session.difficulty}</TableCell>
                      <TableCell>
                        <span
                          className={`px-2 py-1 rounded-full text-xs font-semibold ${
                            session.result === "Victory"
                              ? "bg-green-400/20 text-green-400"
                              : session.result === "Defeat"
                              ? "bg-red-400/20 text-red-400"
                              : "bg-yellow-400/20 text-yellow-400"
                          }`}
                        >
                          {session.result === "Victory"
                            ? "승리"
                            : session.result === "Defeat"
                            ? "패배"
                            : "진행중"}
                        </span>
                      </TableCell>
                      <TableCell>{session.unitsKilled || 0}</TableCell>
                      <TableCell>{session.unitsLost || 0}</TableCell>
                      <TableCell>
                        {session.duration
                          ? `${Math.floor(session.duration / 60)}:${(
                              session.duration % 60
                            )
                              .toString()
                              .padStart(2, "0")}`
                          : "-"}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            ) : (
              <div className="text-center py-12 text-muted-foreground">
                아직 게임 기록이 없습니다
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </DashboardLayout>
  );
}
