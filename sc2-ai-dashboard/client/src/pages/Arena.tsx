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
import { Award, TrendingDown, TrendingUp, Trophy } from "lucide-react";

export default function Arena() {
  const { data: matches } = trpc.arena.getMatches.useQuery({ limit: 20 });
  const { data: arenaStats } = trpc.arena.getStats.useQuery();

  const winRate = arenaStats?.totalMatches
    ? (Number(arenaStats.wins) / Number(arenaStats.totalMatches)) * 100
    : 0;

  const stats = [
    {
      title: "총 경기 수",
      value: arenaStats?.totalMatches || 0,
      icon: Trophy,
      color: "text-chart-1",
    },
    {
      title: "승리",
      value: arenaStats?.wins || 0,
      icon: TrendingUp,
      color: "text-green-400",
    },
    {
      title: "패배",
      value: arenaStats?.losses || 0,
      icon: TrendingDown,
      color: "text-red-400",
    },
    {
      title: "현재 ELO",
      value: arenaStats?.currentElo || "-",
      icon: Award,
      color: "text-chart-2",
    },
  ];

  return (
    <DashboardLayout>
      <div className="space-y-8 animate-slide-up">
        {/* 헤더 */}
        <div className="space-y-2">
          <h1 className="text-4xl font-bold tracking-tight glow-text">
            AI Arena
          </h1>
          <p className="text-muted-foreground text-lg">
            AI Arena 경기 기록과 랭킹 정보
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

        {/* 랭킹 정보 */}
        {arenaStats && arenaStats.currentRanking && (
          <Card className="glass-card border-primary/20 animate-pulse-glow">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Trophy className="w-5 h-5 text-primary" />
                현재 랭킹
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">순위</p>
                  <p className="text-4xl font-bold text-primary">
                    #{arenaStats.currentRanking}
                  </p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">ELO 레이팅</p>
                  <p className="text-4xl font-bold text-chart-2">
                    {arenaStats.currentElo}
                  </p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">승률</p>
                  <p className="text-4xl font-bold text-green-400">
                    {winRate.toFixed(1)}%
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        )}

        {/* 승률 분석 */}
        <Card className="glass-card">
          <CardHeader>
            <CardTitle>Arena 승률</CardTitle>
            <CardDescription>전체 경기 승패 비율</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-medium">승리</span>
                  <span className="text-sm font-bold text-green-400">
                    {arenaStats?.wins || 0} ({winRate.toFixed(1)}%)
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
                    {arenaStats?.losses || 0} ({(100 - winRate).toFixed(1)}%)
                  </span>
                </div>
                <div className="h-4 bg-secondary rounded-full overflow-hidden">
                  <div
                    className="h-full bg-red-400 transition-all"
                    style={{ width: `${100 - winRate}%` }}
                  />
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* monsterbot 정보 */}
        <Card className="glass-card bg-gradient-to-br from-chart-1/10 to-chart-2/10">
          <CardHeader>
            <CardTitle>monsterbot</CardTitle>
            <CardDescription>AI Arena 참가 봇 정보</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                <div>
                  <p className="text-sm text-muted-foreground">봇 이름</p>
                  <p className="font-semibold">monsterbot</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">종족</p>
                  <p className="font-semibold">Zerg</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">상태</p>
                  <span className="inline-block px-2 py-1 rounded-full text-xs font-semibold bg-green-400/20 text-green-400">
                    활성
                  </span>
                </div>
              </div>
              <p className="text-sm text-muted-foreground">
                챌린저급 실력을 목표로 설계된 모듈형 저그 AI입니다. 정찰 기반 동적
                빌드오더 전환과 지능형 마이크로 컨트롤을 특징으로 합니다.
              </p>
            </div>
          </CardContent>
        </Card>

        {/* 최근 경기 기록 */}
        <Card className="glass-card">
          <CardHeader>
            <CardTitle>최근 경기 기록</CardTitle>
            <CardDescription>최근 20경기의 상세 기록</CardDescription>
          </CardHeader>
          <CardContent>
            {matches && matches.length > 0 ? (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Match ID</TableHead>
                    <TableHead>상대</TableHead>
                    <TableHead>종족</TableHead>
                    <TableHead>맵</TableHead>
                    <TableHead>결과</TableHead>
                    <TableHead>ELO</TableHead>
                    <TableHead>날짜</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {matches.map((match) => (
                    <TableRow key={match.id}>
                      <TableCell className="font-mono text-xs">
                        {match.matchId || "-"}
                      </TableCell>
                      <TableCell className="font-medium">
                        {match.opponentName || "Unknown"}
                      </TableCell>
                      <TableCell>{match.opponentRace || "-"}</TableCell>
                      <TableCell>{match.mapName || "-"}</TableCell>
                      <TableCell>
                        <span
                          className={`px-2 py-1 rounded-full text-xs font-semibold ${
                            match.result === "Win"
                              ? "bg-green-400/20 text-green-400"
                              : match.result === "Loss"
                              ? "bg-red-400/20 text-red-400"
                              : "bg-yellow-400/20 text-yellow-400"
                          }`}
                        >
                          {match.result === "Win"
                            ? "승리"
                            : match.result === "Loss"
                            ? "패배"
                            : "무승부"}
                        </span>
                      </TableCell>
                      <TableCell className="font-semibold">
                        {match.elo || "-"}
                      </TableCell>
                      <TableCell className="text-sm text-muted-foreground">
                        {new Date(match.createdAt).toLocaleDateString()}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            ) : (
              <div className="text-center py-12 text-muted-foreground">
                아직 Arena 경기 기록이 없습니다
              </div>
            )}
          </CardContent>
        </Card>

        {/* AI Arena 링크 */}
        <Card className="glass-card border-primary/20">
          <CardHeader>
            <CardTitle>AI Arena 바로가기</CardTitle>
            <CardDescription>
              AI Arena 웹사이트에서 더 많은 정보를 확인하세요
            </CardDescription>
          </CardHeader>
          <CardContent>
            <a
              href="https://aiarena.net/"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 transition-colors"
            >
              <Trophy className="w-4 h-4" />
              AI Arena 방문하기
            </a>
          </CardContent>
        </Card>
      </div>
    </DashboardLayout>
  );
}
