import { useState, useEffect } from 'react';
import { Menu, X, Home, Activity, BarChart3, Bell, Settings, Gamepad2, Github, Play } from 'lucide-react';
import Dashboard from './pages/Dashboard';
import Monitor from './pages/Monitor';
import Analytics from './pages/Analytics';
import Notifications from './pages/Notifications';
import SettingsPage from './pages/Settings';
import BotControl from './pages/BotControl';
import GitHub from './pages/GitHub';
import Replays from './pages/Replays';

type Page = 'dashboard' | 'monitor' | 'analytics' | 'notifications' | 'settings' | 'botcontrol' | 'github' | 'replays';

export default function App() {
  const [currentPage, setCurrentPage] = useState<Page>('dashboard');
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [isOnline, setIsOnline] = useState(navigator.onLine);

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

  const navigationItems = [
    { id: 'dashboard' as Page, label: '대시보드', icon: Home },
    { id: 'monitor' as Page, label: '실시간 모니터링', icon: Activity },
    { id: 'analytics' as Page, label: '분석', icon: BarChart3 },
    { id: 'botcontrol' as Page, label: '봇 제어', icon: Gamepad2 },
    { id: 'github' as Page, label: 'GitHub', icon: Github },
    { id: 'replays' as Page, label: '리플레이', icon: Play },
    { id: 'notifications' as Page, label: '알림', icon: Bell },
    { id: 'settings' as Page, label: '설정', icon: Settings },
  ];

  const renderPage = () => {
    switch (currentPage) {
      case 'dashboard':
        return <Dashboard />;
      case 'monitor':
        return <Monitor />;
      case 'analytics':
        return <Analytics />;
      case 'botcontrol':
        return <BotControl />;
      case 'github':
        return <GitHub />;
      case 'replays':
        return <Replays />;
      case 'notifications':
        return <Notifications />;
      case 'settings':
        return <SettingsPage />;
      default:
        return <Dashboard />;
    }
  };

  return (
    <div className="flex h-screen bg-background text-foreground">
      {/* 사이드바 */}
      <aside
        className={`fixed inset-y-0 left-0 z-50 w-64 bg-card transition-transform duration-300 ease-in-out md:relative md:translate-x-0 ${
          sidebarOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        <div className="flex h-full flex-col">
          {/* 로고 */}
          <div className="border-b border-border px-6 py-4">
            <h1 className="text-xl font-bold text-gradient">SC2 Monitor</h1>
            <p className="text-xs text-muted-foreground">AI 봇 모니터링</p>
          </div>

          {/* 네비게이션 */}
          <nav className="flex-1 space-y-2 px-4 py-6">
            {navigationItems.map((item) => {
              const Icon = item.icon;
              const isActive = currentPage === item.id;
              return (
            <button
              key={item.id}
              onClick={() => {
                setCurrentPage(item.id);
                setSidebarOpen(false);
              }}
              className={`w-full flex items-center gap-3 rounded-lg px-4 py-3 transition-colors text-left ${
                isActive
                  ? 'bg-accent text-accent-foreground'
                  : 'text-muted-foreground hover:bg-secondary hover:text-foreground'
              }`}
            >
              <Icon className="h-5 w-5" />
              <span className="text-sm font-medium">{item.label}</span>
            </button>
              );
            })}
          </nav>

          {/* 상태 표시 */}
          <div className="border-t border-border px-4 py-4">
            <div className="flex items-center gap-2 rounded-lg bg-secondary p-3">
              <div
                className={`h-2 w-2 rounded-full ${
                  isOnline ? 'bg-green-500' : 'bg-red-500'
                }`}
              />
              <span className="text-xs font-medium">
                {isOnline ? '온라인' : '오프라인'}
              </span>
            </div>
          </div>
        </div>
      </aside>

      {/* 메인 콘텐츠 */}
      <div className="flex flex-1 flex-col overflow-hidden">
        {/* 헤더 */}
        <header className="border-b border-border bg-card px-4 py-4 md:px-6">
          <div className="flex items-center justify-between">
            <button
              onClick={() => setSidebarOpen(!sidebarOpen)}
              className="md:hidden"
            >
              {sidebarOpen ? (
                <X className="h-6 w-6" />
              ) : (
                <Menu className="h-6 w-6" />
              )}
            </button>
            <h2 className="text-lg font-semibold">
              {navigationItems.find((item) => item.id === currentPage)?.label}
            </h2>
            <div className="w-6" />
          </div>
        </header>

        {/* 콘텐츠 */}
        <main className="flex-1 overflow-auto">
          <div className="container py-4 md:py-6">
            {renderPage()}
          </div>
        </main>
      </div>

      {/* 모바일 오버레이 */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/50 md:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}
    </div>
  );
}
