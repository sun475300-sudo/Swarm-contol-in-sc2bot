import DashboardLayout from "@/components/DashboardLayout";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { trpc } from "@/lib/trpc";
import { Activity, BarChart3, Bot, Brain, Trophy, TrendingUp } from "lucide-react";
import { Link } from "wouter";

export default function Home() {
  const { data: gameStats } = trpc.game.getStats.useQuery();
  const { data: trainingStats } = trpc.training.getStats.useQuery();
  const { data: arenaStats } = trpc.arena.getStats.useQuery();
  const { data: currentSession } = trpc.game.getCurrentSession.useQuery();

  const stats = [
    {
      title: "총 게임 수",
      value: gameStats?.totalGames || 0,
      icon: Activity,
      color: "text-chart-1",
      bgColor: "bg-chart-1/10",
    },
    {
      title: "승률",
      value: gameStats?.totalGames
        ? `${((Number(gameStats.wins) / Number(gameStats.totalGames)) * 100).toFixed(1)}%`
        : "0%",
      icon: TrendingUp,
      color: "text-chart-2",
      bgColor: "bg-chart-2/10",
    },
    {
      title: "학습 에피소드",
      value: trainingStats?.totalEpisodes || 0,
      icon: Brain,
      color: "text-chart-3",
      bgColor: "bg-chart-3/10",
    },
    {
      title: "Arena ELO",
      value: arenaStats?.currentElo || "-",
      icon: Trophy,
      color: "text-chart-4",
      bgColor: "bg-chart-4/10",
    },
  ];

  const quickLinks = [
    {
      title: "실시간 모니터링",
      description: "현재 게임 상태를 실시간으로 확인하세요",
      icon: Activity,
      href: "/monitor",
      color: "from-chart-1/20 to-chart-1/5",
    },
    {
      title: "전투 분석",
      description: "전투 통계와 승률을 분석하세요",
      icon: BarChart3,
      href: "/battles",
      color: "from-chart-2/20 to-chart-2/5",
    },
    {
      title: "학습 진행",
      description: "AI 학습 진행 상황을 추적하세요",
      icon: Brain,
      href: "/training",
      color: "from-chart-3/20 to-chart-3/5",
    },
    {
      title: "봇 설정",
      description: "AI 봇의 전략과 설정을 관리하세요",
      icon: Bot,
      href: "/bot-config",
      color: "from-chart-4/20 to-chart-4/5",
    },
  ];

  return (
    <DashboardLayout>
      <div className="space-y-8 animate-slide-up">
        {/* 헤더 */}
        <div className="space-y-2">
          <h1 className="text-4xl font-bold tracking-tight glow-text">
            SC2 AI Dashboard
          </h1>
          <p className="text-muted-foreground text-lg">
            StarCraft II AI 모니터링 및 제어 시스템
          </p>
        </div>

        {/* 현재 게임 상태 */}
        {currentSession && (
          <Card className="glass-card border-primary/20 animate-pulse-glow">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Activity className="w-5 h-5 text-primary" />
                진행 중인 게임
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div>
                  <p className="text-sm text-muted-foreground">맵</p>
                  <p className="font-semibold">{currentSession.mapName}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">상대 종족</p>
                  <p className="font-semibold">{currentSession.enemyRace}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">난이도</p>
                  <p className="font-semibold">{currentSession.difficulty}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">게임 단계</p>
                  <p className="font-semibold">{currentSession.gamePhase || "진행 중"}</p>
                </div>
              </div>
            </CardContent>
          </Card>
        )}

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
                  <div className={`p-2 rounded-lg ${stat.bgColor}`}>
                    <Icon className={`w-4 h-4 ${stat.color}`} />
                  </div>
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

        {/* 빠른 링크 */}
        <div>
          <h2 className="text-2xl font-bold mb-6">빠른 액세스</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {quickLinks.map((link, index) => {
              const Icon = link.icon;
              return (
                <Link key={index} href={link.href}>
                  <a>
                    <Card className={`glass-card hover:glow-effect transition-all cursor-pointer bg-gradient-to-br ${link.color}`}>
                      <CardHeader>
                        <div className="flex items-center gap-3">
                          <div className="p-3 rounded-lg bg-primary/20">
                            <Icon className="w-6 h-6 text-primary" />
                          </div>
                          <div>
                            <CardTitle>{link.title}</CardTitle>
                            <CardDescription className="mt-1">
                              {link.description}
                            </CardDescription>
                          </div>
                        </div>
                      </CardHeader>
                    </Card>
                  </a>
                </Link>
              );
            })}
          </div>
        </div>

        {/* 최근 활동 */}
        <Card className="glass-card">
          <CardHeader>
            <CardTitle>시스템 상태</CardTitle>
            <CardDescription>AI 시스템의 전반적인 상태</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-sm">게임 엔진</span>
                <span className="text-sm font-medium text-primary">정상</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm">학습 시스템</span>
                <span className="text-sm font-medium text-primary">활성</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm">데이터베이스</span>
                <span className="text-sm font-medium text-primary">연결됨</span>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </DashboardLayout>
  );
}
