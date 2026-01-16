import DashboardLayout from "@/components/DashboardLayout";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { trpc } from "@/lib/trpc";
import { Bot, Check, Pencil, Plus, Trash2 } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";

export default function BotConfig() {
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingConfig, setEditingConfig] = useState<number | null>(null);
  const [formData, setFormData] = useState({
    name: "",
    strategy: "Balanced" as "Aggressive" | "Defensive" | "Balanced" | "Economic" | "Rush",
    buildOrder: "",
    description: "",
  });

  const { data: configs, refetch } = trpc.bot.getConfigs.useQuery();
  const { data: activeConfig } = trpc.bot.getActiveConfig.useQuery();
  const utils = trpc.useUtils();

  const createMutation = trpc.bot.createConfig.useMutation({
    onSuccess: () => {
      toast.success("봇 설정이 생성되었습니다");
      setDialogOpen(false);
      resetForm();
      refetch();
    },
    onError: (error) => {
      toast.error(`오류: ${error.message}`);
    },
  });

  const updateMutation = trpc.bot.updateConfig.useMutation({
    onSuccess: () => {
      toast.success("봇 설정이 업데이트되었습니다");
      setDialogOpen(false);
      resetForm();
      refetch();
    },
    onError: (error) => {
      toast.error(`오류: ${error.message}`);
    },
  });

  const deleteMutation = trpc.bot.deleteConfig.useMutation({
    onSuccess: () => {
      toast.success("봇 설정이 삭제되었습니다");
      refetch();
    },
    onError: (error) => {
      toast.error(`오류: ${error.message}`);
    },
  });

  const activateMutation = trpc.bot.updateConfig.useMutation({
    onSuccess: () => {
      toast.success("봇 설정이 활성화되었습니다");
      utils.bot.getActiveConfig.invalidate();
      refetch();
    },
    onError: (error) => {
      toast.error(`오류: ${error.message}`);
    },
  });

  const resetForm = () => {
    setFormData({
      name: "",
      strategy: "Balanced",
      buildOrder: "",
      description: "",
    });
    setEditingConfig(null);
  };

  const handleSubmit = () => {
    if (!formData.name) {
      toast.error("설정 이름을 입력해주세요");
      return;
    }

    if (editingConfig) {
      updateMutation.mutate({
        id: editingConfig,
        ...formData,
      });
    } else {
      createMutation.mutate(formData);
    }
  };

  const handleEdit = (config: any) => {
    setEditingConfig(config.id);
    setFormData({
      name: config.name,
      strategy: config.strategy,
      buildOrder: config.buildOrder || "",
      description: config.description || "",
    });
    setDialogOpen(true);
  };

  const handleDelete = (id: number) => {
    if (confirm("정말로 이 설정을 삭제하시겠습니까?")) {
      deleteMutation.mutate({ id });
    }
  };

  const handleActivate = (id: number) => {
    activateMutation.mutate({ id, isActive: true });
  };

  const strategyColors = {
    Aggressive: "text-red-400 bg-red-400/10",
    Defensive: "text-blue-400 bg-blue-400/10",
    Balanced: "text-green-400 bg-green-400/10",
    Economic: "text-yellow-400 bg-yellow-400/10",
    Rush: "text-purple-400 bg-purple-400/10",
  };

  const strategyDescriptions = {
    Aggressive: "공격적인 플레이 스타일",
    Defensive: "방어적인 플레이 스타일",
    Balanced: "균형잡힌 플레이 스타일",
    Economic: "경제 중심 플레이 스타일",
    Rush: "초반 러시 전략",
  };

  return (
    <DashboardLayout>
      <div className="space-y-8 animate-slide-up">
        {/* 헤더 */}
        <div className="flex items-center justify-between">
          <div className="space-y-2">
            <h1 className="text-4xl font-bold tracking-tight glow-text">
              봇 설정
            </h1>
            <p className="text-muted-foreground text-lg">
              AI 봇의 전략과 빌드오더를 관리합니다
            </p>
          </div>
          <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
            <DialogTrigger asChild>
              <Button onClick={resetForm} className="gap-2">
                <Plus className="w-4 h-4" />
                새 설정 만들기
              </Button>
            </DialogTrigger>
            <DialogContent className="sm:max-w-[500px]">
              <DialogHeader>
                <DialogTitle>
                  {editingConfig ? "설정 수정" : "새 봇 설정"}
                </DialogTitle>
                <DialogDescription>
                  봇의 전략과 빌드오더를 설정하세요
                </DialogDescription>
              </DialogHeader>
              <div className="space-y-4 py-4">
                <div className="space-y-2">
                  <Label htmlFor="name">설정 이름</Label>
                  <Input
                    id="name"
                    value={formData.name}
                    onChange={(e) =>
                      setFormData({ ...formData, name: e.target.value })
                    }
                    placeholder="예: 공격형 저글링 러시"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="strategy">전략</Label>
                  <Select
                    value={formData.strategy}
                    onValueChange={(value: any) =>
                      setFormData({ ...formData, strategy: value })
                    }
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="Aggressive">공격형 (Aggressive)</SelectItem>
                      <SelectItem value="Defensive">방어형 (Defensive)</SelectItem>
                      <SelectItem value="Balanced">균형형 (Balanced)</SelectItem>
                      <SelectItem value="Economic">경제형 (Economic)</SelectItem>
                      <SelectItem value="Rush">러시 (Rush)</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="buildOrder">빌드오더 (JSON)</Label>
                  <Textarea
                    id="buildOrder"
                    value={formData.buildOrder}
                    onChange={(e) =>
                      setFormData({ ...formData, buildOrder: e.target.value })
                    }
                    placeholder='{"units": ["Drone", "Overlord", "Zergling"]}'
                    rows={4}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="description">설명</Label>
                  <Textarea
                    id="description"
                    value={formData.description}
                    onChange={(e) =>
                      setFormData({ ...formData, description: e.target.value })
                    }
                    placeholder="이 설정에 대한 설명을 입력하세요"
                    rows={3}
                  />
                </div>
              </div>
              <DialogFooter>
                <Button variant="outline" onClick={() => setDialogOpen(false)}>
                  취소
                </Button>
                <Button onClick={handleSubmit}>
                  {editingConfig ? "수정" : "생성"}
                </Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        </div>

        {/* 활성 설정 */}
        {activeConfig && (
          <Card className="glass-card border-primary/20 animate-pulse-glow">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Check className="w-5 h-5 text-primary" />
                현재 활성 설정
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div>
                  <h3 className="text-2xl font-bold">{activeConfig.name}</h3>
                  <span
                    className={`inline-block mt-2 px-3 py-1 rounded-full text-sm font-semibold ${
                      strategyColors[activeConfig.strategy]
                    }`}
                  >
                    {activeConfig.strategy}
                  </span>
                </div>
                {activeConfig.description && (
                  <p className="text-muted-foreground">{activeConfig.description}</p>
                )}
              </div>
            </CardContent>
          </Card>
        )}

        {/* 설정 목록 */}
        <div>
          <h2 className="text-2xl font-bold mb-4">모든 설정</h2>
          {configs && configs.length > 0 ? (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {configs.map((config) => (
                <Card
                  key={config.id}
                  className={`glass-card ${
                    config.isActive
                      ? "border-primary/30 glow-effect"
                      : "hover:border-primary/20"
                  } transition-all`}
                >
                  <CardHeader>
                    <div className="flex items-start justify-between">
                      <div className="space-y-2 flex-1">
                        <CardTitle className="flex items-center gap-2">
                          <Bot className="w-5 h-5" />
                          {config.name}
                          {config.isActive && (
                            <span className="text-xs px-2 py-1 rounded-full bg-primary/20 text-primary">
                              활성
                            </span>
                          )}
                        </CardTitle>
                        <CardDescription>
                          <span
                            className={`inline-block px-2 py-1 rounded-full text-xs font-semibold ${
                              strategyColors[config.strategy]
                            }`}
                          >
                            {strategyDescriptions[config.strategy]}
                          </span>
                        </CardDescription>
                      </div>
                      <div className="flex gap-2">
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => handleEdit(config)}
                        >
                          <Pencil className="w-4 h-4" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => handleDelete(config.id)}
                        >
                          <Trash2 className="w-4 h-4" />
                        </Button>
                      </div>
                    </div>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-4">
                      {config.description && (
                        <p className="text-sm text-muted-foreground">
                          {config.description}
                        </p>
                      )}
                      {!config.isActive && (
                        <Button
                          onClick={() => handleActivate(config.id)}
                          className="w-full"
                          variant="outline"
                        >
                          이 설정 활성화
                        </Button>
                      )}
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          ) : (
            <Card className="glass-card">
              <CardContent className="py-12">
                <div className="text-center space-y-4">
                  <Bot className="w-16 h-16 text-muted-foreground mx-auto" />
                  <p className="text-muted-foreground">
                    아직 봇 설정이 없습니다. 새 설정을 만들어보세요!
                  </p>
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </DashboardLayout>
  );
}
