import DashboardLayout from "@/components/DashboardLayout";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { trpc } from "@/lib/trpc";
import { Activity, Coins, Droplet, Shield, Swords, Users } from "lucide-react";
import { useEffect } from "react";

export default function Monitor() {
  const { data: currentSession, refetch } = trpc.game.getCurrentSession.useQuery();

  // 5초마다 자동 새로고침
  useEffect(() => {
    const interval = setInterval(() => {
      refetch();
    }, 5000);
    return () => clearInterval(interval);
  }, [refetch]);

  if (!currentSession) {
    return (
      <DashboardLayout>
        <div className="space-y-8">
          <div className="space-y-2">
            <h1 className="text-4xl font-bold tracking-tight glow-text">
              실시간 모니터링
            </h1>
            <p className="text-muted-foreground text-lg">
              현재 진행 중인 게임이 없습니다
            </p>
          </div>

          <Card className="glass-card">
            <CardHeader>
              <CardTitle>게임 시작 대기 중</CardTitle>
              <CardDescription>
                새로운 게임이 시작되면 여기에 실시간 정보가 표시됩니다
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="flex items-center justify-center py-12">
                <div className="text-center space-y-4">
                  <Activity className="w-16 h-16 text-muted-foreground mx-auto animate-pulse" />
                  <p className="text-muted-foreground">
                    게임 세션을 시작하면 실시간 모니터링이 활성화됩니다
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </DashboardLayout>
    );
  }

  const supplyPercent = currentSession.finalSupply
    ? (currentSession.finalSupply / 200) * 100
    : 0;

  const resourceCards = [
    {
      title: "미네랄",
      value: currentSession.finalMinerals || 0,
      icon: Coins,
      color: "text-blue-400",
      bgColor: "bg-blue-400/10",
    },
    {
      title: "가스",
      value: currentSession.finalGas || 0,
      icon: Droplet,
      color: "text-green-400",
      bgColor: "bg-green-400/10",
    },
    {
      title: "인구수",
      value: `${currentSession.finalSupply || 0}/200`,
      icon: Users,
      color: "text-purple-400",
      bgColor: "bg-purple-400/10",
    },
  ];

  const combatStats = [
    {
      title: "처치한 유닛",
      value: currentSession.unitsKilled || 0,
      icon: Swords,
      color: "text-chart-1",
    },
    {
      title: "잃은 유닛",
      value: currentSession.unitsLost || 0,
      icon: Shield,
      color: "text-chart-2",
    },
  ];

  return (
    <DashboardLayout>
      <div className="space-y-8 animate-slide-up">
        {/* 헤더 */}
        <div className="space-y-2">
          <div className="flex items-center gap-3">
            <h1 className="text-4xl font-bold tracking-tight glow-text">
              실시간 모니터링
            </h1>
            <div className="flex items-center gap-2 px-3 py-1 rounded-full bg-primary/20 border border-primary/30">
              <div className="w-2 h-2 rounded-full bg-primary animate-pulse" />
              <span className="text-sm font-medium text-primary">LIVE</span>
            </div>
          </div>
          <p className="text-muted-foreground text-lg">
            현재 게임 상태를 실시간으로 모니터링합니다
          </p>
        </div>

        {/* 게임 정보 */}
        <Card className="glass-card border-primary/20 animate-pulse-glow">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Activity className="w-5 h-5 text-primary" />
              게임 정보
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
              <div>
                <p className="text-sm text-muted-foreground mb-1">맵</p>
                <p className="font-semibold text-lg">{currentSession.mapName}</p>
              </div>
              <div>
                <p className="text-sm text-muted-foreground mb-1">상대 종족</p>
                <p className="font-semibold text-lg">{currentSession.enemyRace}</p>
              </div>
              <div>
                <p className="text-sm text-muted-foreground mb-1">난이도</p>
                <p className="font-semibold text-lg">{currentSession.difficulty}</p>
              </div>
              <div>
                <p className="text-sm text-muted-foreground mb-1">게임 단계</p>
                <p className="font-semibold text-lg text-primary">
                  {currentSession.gamePhase || "진행 중"}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* 자원 현황 */}
        <div>
          <h2 className="text-2xl font-bold mb-4">자원 현황</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {resourceCards.map((resource, index) => {
              const Icon = resource.icon;
              return (
                <Card key={index} className="glass-card hover:glow-effect transition-all">
                  <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                    <CardTitle className="text-sm font-medium">
                      {resource.title}
                    </CardTitle>
                    <div className={`p-2 rounded-lg ${resource.bgColor}`}>
                      <Icon className={`w-4 h-4 ${resource.color}`} />
                    </div>
                  </CardHeader>
                  <CardContent>
                    <div className={`text-3xl font-bold ${resource.color}`}>
                      {resource.value}
                    </div>
                  </CardContent>
                </Card>
              );
            })}
          </div>
        </div>

        {/* 인구수 게이지 */}
        <Card className="glass-card">
          <CardHeader>
            <CardTitle>인구수 사용률</CardTitle>
            <CardDescription>
              현재 {currentSession.finalSupply || 0} / 200 (
              {supplyPercent.toFixed(0)}%)
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Progress value={supplyPercent} className="h-4" />
          </CardContent>
        </Card>

        {/* 전투 통계 */}
        <div>
          <h2 className="text-2xl font-bold mb-4">전투 통계</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {combatStats.map((stat, index) => {
              const Icon = stat.icon;
              return (
                <Card key={index} className="glass-card">
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <Icon className={`w-5 h-5 ${stat.color}`} />
                      {stat.title}
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className={`text-4xl font-bold ${stat.color}`}>
                      {stat.value}
                    </div>
                  </CardContent>
                </Card>
              );
            })}
          </div>
        </div>

        {/* 게임 시간 */}
        {currentSession.duration && (
          <Card className="glass-card">
            <CardHeader>
              <CardTitle>게임 시간</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold text-primary">
                {Math.floor(currentSession.duration / 60)}분{" "}
                {currentSession.duration % 60}초
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </DashboardLayout>
  );
}
