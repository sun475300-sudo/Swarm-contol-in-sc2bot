import { useEffect, useState } from 'react';
import {
  GitBranch,
  GitCommit,
  GitPullRequest,
  Tag,
  AlertCircle,
  Star,
  Eye,
  GitFork,
  RefreshCw,
  ExternalLink,
  CheckCircle,
  XCircle,
  Clock,
} from 'lucide-react';
import {
  getRepositoryStats,
  checkForUpdates,
  getLastCheckedTime,
  saveLastCheckedTime,
  getRepositoryConfig,
  saveRepositoryConfig,
  formatRelativeTime,
  GitHubCommit,
  GitHubPullRequest,
  GitHubRelease,
  GitHubIssue,
  GitHubRepository,
} from '@/lib/github';
import { showNotification } from '@/lib/notifications';

type TabType = 'overview' | 'commits' | 'prs' | 'releases' | 'issues';

export default function GitHub() {
  const [activeTab, setActiveTab] = useState<TabType>('overview');
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [repository, setRepository] = useState<GitHubRepository | null>(null);
  const [commits, setCommits] = useState<GitHubCommit[]>([]);
  const [pullRequests, setPullRequests] = useState<GitHubPullRequest[]>([]);
  const [releases, setReleases] = useState<GitHubRelease[]>([]);
  const [issues, setIssues] = useState<GitHubIssue[]>([]);
  const [newUpdates, setNewUpdates] = useState<{
    commits: number;
    prs: number;
    releases: number;
    issues: number;
  }>({ commits: 0, prs: 0, releases: 0, issues: 0 });

  const [repoConfig, setRepoConfig] = useState(getRepositoryConfig());
  const [showSettings, setShowSettings] = useState(false);

  const fetchData = async (showRefreshing = false) => {
    if (showRefreshing) setRefreshing(true);
    else setLoading(true);

    try {
      const stats = await getRepositoryStats(repoConfig.owner, repoConfig.repo);
      setRepository(stats.repository);
      setCommits(stats.recentCommits);
      setPullRequests(stats.openPullRequests);
      setReleases(stats.recentReleases);
      setIssues(stats.openIssues);

      // 새로운 업데이트 확인
      const lastChecked = getLastCheckedTime();
      const updates = await checkForUpdates(lastChecked, repoConfig.owner, repoConfig.repo);
      
      const newUpdateCounts = {
        commits: updates.newCommits.length,
        prs: updates.newPullRequests.length,
        releases: updates.newReleases.length,
        issues: updates.newIssues.length,
      };
      setNewUpdates(newUpdateCounts);

      // 새로운 업데이트가 있으면 알림
      if (updates.newCommits.length > 0) {
        showNotification({
          title: '🔄 새로운 커밋',
          body: `${updates.newCommits.length}개의 새로운 커밋이 있습니다.`,
        });
      }
      if (updates.newReleases.length > 0) {
        showNotification({
          title: '🎉 새로운 릴리즈',
          body: `${updates.newReleases[0].name || updates.newReleases[0].tag_name}가 출시되었습니다!`,
        });
      }

      saveLastCheckedTime();
    } catch (error) {
      console.error('Failed to fetch GitHub data:', error);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(() => fetchData(true), 60000); // 1분마다 새로고침
    return () => clearInterval(interval);
  }, [repoConfig]);

  const handleSaveSettings = () => {
    saveRepositoryConfig(repoConfig.owner, repoConfig.repo);
    setShowSettings(false);
    fetchData();
  };

  const tabs = [
    { id: 'overview' as TabType, label: '개요', count: null },
    { id: 'commits' as TabType, label: '커밋', count: newUpdates.commits },
    { id: 'prs' as TabType, label: 'PR', count: newUpdates.prs },
    { id: 'releases' as TabType, label: '릴리즈', count: newUpdates.releases },
    { id: 'issues' as TabType, label: '이슈', count: newUpdates.issues },
  ];

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="text-center">
          <div className="mb-4 h-8 w-8 animate-spin rounded-full border-4 border-border border-t-accent mx-auto" />
          <p className="text-muted-foreground">GitHub 데이터 로드 중...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* 헤더 */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold">GitHub 모니터링</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            {repoConfig.owner}/{repoConfig.repo}
          </p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => setShowSettings(!showSettings)}
            className="rounded-lg bg-secondary px-3 py-2 text-sm font-medium text-muted-foreground hover:bg-secondary/80"
          >
            설정
          </button>
          <button
            onClick={() => fetchData(true)}
            disabled={refreshing}
            className="rounded-lg bg-accent px-3 py-2 text-sm font-medium text-accent-foreground hover:bg-accent/90 disabled:opacity-50"
          >
            <RefreshCw className={`h-4 w-4 ${refreshing ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* 설정 패널 */}
      {showSettings && (
        <div className="glass rounded-lg border border-white/10 bg-white/5 p-4 backdrop-blur-md">
          <h3 className="mb-4 font-semibold">저장소 설정</h3>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium">소유자</label>
              <input
                type="text"
                value={repoConfig.owner}
                onChange={(e) => setRepoConfig({ ...repoConfig, owner: e.target.value })}
                className="mt-1 w-full rounded-lg border border-border bg-white/5 px-3 py-2 text-sm"
              />
            </div>
            <div>
              <label className="block text-sm font-medium">저장소</label>
              <input
                type="text"
                value={repoConfig.repo}
                onChange={(e) => setRepoConfig({ ...repoConfig, repo: e.target.value })}
                className="mt-1 w-full rounded-lg border border-border bg-white/5 px-3 py-2 text-sm"
              />
            </div>
            <button
              onClick={handleSaveSettings}
              className="w-full rounded-lg bg-accent px-4 py-2 text-sm font-medium text-accent-foreground hover:bg-accent/90"
            >
              저장
            </button>
          </div>
        </div>
      )}

      {/* 저장소 정보 */}
      {repository && (
        <div className="glass rounded-lg border border-white/10 bg-white/5 p-6 backdrop-blur-md">
          <div className="flex items-start justify-between">
            <div className="flex-1">
              <h3 className="text-lg font-bold">{repository.name}</h3>
              <p className="mt-1 text-sm text-muted-foreground">
                {repository.description || '설명 없음'}
              </p>
              {repository.language && (
                <span className="mt-2 inline-block rounded-full bg-accent/20 px-3 py-1 text-xs font-medium text-accent">
                  {repository.language}
                </span>
              )}
            </div>
            <a
              href={repository.html_url}
              target="_blank"
              rel="noopener noreferrer"
              className="rounded-lg bg-secondary p-2 hover:bg-secondary/80"
            >
              <ExternalLink className="h-4 w-4" />
            </a>
          </div>
          <div className="mt-4 grid grid-cols-3 gap-4">
            <div className="flex items-center gap-2">
              <Star className="h-4 w-4 text-yellow-400" />
              <span className="text-sm font-semibold">{repository.stargazers_count}</span>
            </div>
            <div className="flex items-center gap-2">
              <Eye className="h-4 w-4 text-blue-400" />
              <span className="text-sm font-semibold">{repository.watchers_count}</span>
            </div>
            <div className="flex items-center gap-2">
              <GitFork className="h-4 w-4 text-green-400" />
              <span className="text-sm font-semibold">{repository.forks_count}</span>
            </div>
          </div>
          <p className="mt-4 text-xs text-muted-foreground">
            마지막 푸시: {formatRelativeTime(repository.pushed_at)}
          </p>
        </div>
      )}

      {/* 탭 네비게이션 */}
      <div className="flex gap-2 overflow-x-auto pb-2">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`relative flex-shrink-0 rounded-lg px-4 py-2 text-sm font-medium transition-colors ${
              activeTab === tab.id
                ? 'bg-accent text-accent-foreground'
                : 'bg-secondary text-muted-foreground hover:bg-secondary/80'
            }`}
          >
            {tab.label}
            {tab.count !== null && tab.count > 0 && (
              <span className="absolute -right-1 -top-1 flex h-5 w-5 items-center justify-center rounded-full bg-red-500 text-xs text-white">
                {tab.count}
              </span>
            )}
          </button>
        ))}
      </div>

      {/* 탭 콘텐츠 */}
      {activeTab === 'overview' && (
        <div className="space-y-4">
          {/* 최근 커밋 */}
          <div className="glass rounded-lg border border-white/10 bg-white/5 p-4 backdrop-blur-md">
            <h4 className="mb-3 flex items-center gap-2 font-semibold">
              <GitCommit className="h-4 w-4 text-cyan-400" />
              최근 커밋
            </h4>
            <div className="space-y-2">
              {commits.slice(0, 3).map((commit) => (
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

          {/* 열린 PR */}
          {pullRequests.length > 0 && (
            <div className="glass rounded-lg border border-white/10 bg-white/5 p-4 backdrop-blur-md">
              <h4 className="mb-3 flex items-center gap-2 font-semibold">
                <GitPullRequest className="h-4 w-4 text-purple-400" />
                열린 PR ({pullRequests.length})
              </h4>
              <div className="space-y-2">
                {pullRequests.slice(0, 3).map((pr) => (
                  <a
                    key={pr.id}
                    href={pr.html_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="block rounded-lg bg-white/5 p-3 hover:bg-white/10"
                  >
                    <p className="text-sm font-medium line-clamp-1">#{pr.number} {pr.title}</p>
                    <p className="mt-1 text-xs text-muted-foreground">
                      {pr.user.login} • {formatRelativeTime(pr.created_at)}
                    </p>
                  </a>
                ))}
              </div>
            </div>
          )}

          {/* 최신 릴리즈 */}
          {releases.length > 0 && (
            <div className="glass rounded-lg border border-white/10 bg-white/5 p-4 backdrop-blur-md">
              <h4 className="mb-3 flex items-center gap-2 font-semibold">
                <Tag className="h-4 w-4 text-green-400" />
                최신 릴리즈
              </h4>
              <a
                href={releases[0].html_url}
                target="_blank"
                rel="noopener noreferrer"
                className="block rounded-lg bg-white/5 p-3 hover:bg-white/10"
              >
                <p className="text-sm font-bold text-green-400">
                  {releases[0].name || releases[0].tag_name}
                </p>
                <p className="mt-1 text-xs text-muted-foreground">
                  {formatRelativeTime(releases[0].published_at)}
                </p>
              </a>
            </div>
          )}
        </div>
      )}

      {activeTab === 'commits' && (
        <div className="space-y-2">
          {commits.map((commit) => (
            <a
              key={commit.sha}
              href={commit.html_url}
              target="_blank"
              rel="noopener noreferrer"
              className="glass block rounded-lg border border-white/10 bg-white/5 p-4 backdrop-blur-md hover:bg-white/10"
            >
              <div className="flex items-start gap-3">
                {commit.author.avatar_url && (
                  <img
                    src={commit.author.avatar_url}
                    alt={commit.author.name}
                    className="h-8 w-8 rounded-full"
                  />
                )}
                <div className="flex-1 min-w-0">
                  <p className="font-medium line-clamp-2">{commit.message}</p>
                  <p className="mt-1 text-xs text-muted-foreground">
                    {commit.author.name} • {formatRelativeTime(commit.author.date)}
                  </p>
                  <p className="mt-1 text-xs font-mono text-cyan-400">
                    {commit.sha.substring(0, 7)}
                  </p>
                </div>
              </div>
            </a>
          ))}
        </div>
      )}

      {activeTab === 'prs' && (
        <div className="space-y-2">
          {pullRequests.length === 0 ? (
            <div className="glass rounded-lg border border-white/10 bg-white/5 p-8 text-center backdrop-blur-md">
              <GitPullRequest className="mx-auto h-12 w-12 text-muted-foreground opacity-50" />
              <p className="mt-4 text-muted-foreground">열린 PR이 없습니다</p>
            </div>
          ) : (
            pullRequests.map((pr) => (
              <a
                key={pr.id}
                href={pr.html_url}
                target="_blank"
                rel="noopener noreferrer"
                className="glass block rounded-lg border border-white/10 bg-white/5 p-4 backdrop-blur-md hover:bg-white/10"
              >
                <div className="flex items-start gap-3">
                  <img
                    src={pr.user.avatar_url}
                    alt={pr.user.login}
                    className="h-8 w-8 rounded-full"
                  />
                  <div className="flex-1 min-w-0">
                    <p className="font-medium">
                      <span className="text-muted-foreground">#{pr.number}</span> {pr.title}
                    </p>
                    <p className="mt-1 text-xs text-muted-foreground">
                      {pr.user.login} • {formatRelativeTime(pr.created_at)}
                    </p>
                    <div className="mt-2 flex gap-3 text-xs">
                      <span className="text-green-400">+{pr.additions}</span>
                      <span className="text-red-400">-{pr.deletions}</span>
                      <span className="text-muted-foreground">{pr.changed_files} files</span>
                    </div>
                  </div>
                </div>
              </a>
            ))
          )}
        </div>
      )}

      {activeTab === 'releases' && (
        <div className="space-y-2">
          {releases.length === 0 ? (
            <div className="glass rounded-lg border border-white/10 bg-white/5 p-8 text-center backdrop-blur-md">
              <Tag className="mx-auto h-12 w-12 text-muted-foreground opacity-50" />
              <p className="mt-4 text-muted-foreground">릴리즈가 없습니다</p>
            </div>
          ) : (
            releases.map((release) => (
              <a
                key={release.id}
                href={release.html_url}
                target="_blank"
                rel="noopener noreferrer"
                className="glass block rounded-lg border border-white/10 bg-white/5 p-4 backdrop-blur-md hover:bg-white/10"
              >
                <div className="flex items-start justify-between">
                  <div>
                    <p className="font-bold text-green-400">
                      {release.name || release.tag_name}
                    </p>
                    <p className="mt-1 text-xs text-muted-foreground">
                      {release.author.login} • {formatRelativeTime(release.published_at)}
                    </p>
                    {release.prerelease && (
                      <span className="mt-2 inline-block rounded-full bg-yellow-500/20 px-2 py-0.5 text-xs text-yellow-400">
                        Pre-release
                      </span>
                    )}
                  </div>
                  <Tag className="h-5 w-5 text-green-400" />
                </div>
                {release.body && (
                  <p className="mt-2 text-sm text-muted-foreground line-clamp-2">
                    {release.body}
                  </p>
                )}
              </a>
            ))
          )}
        </div>
      )}

      {activeTab === 'issues' && (
        <div className="space-y-2">
          {issues.length === 0 ? (
            <div className="glass rounded-lg border border-white/10 bg-white/5 p-8 text-center backdrop-blur-md">
              <AlertCircle className="mx-auto h-12 w-12 text-muted-foreground opacity-50" />
              <p className="mt-4 text-muted-foreground">열린 이슈가 없습니다</p>
            </div>
          ) : (
            issues.map((issue) => (
              <a
                key={issue.id}
                href={issue.html_url}
                target="_blank"
                rel="noopener noreferrer"
                className="glass block rounded-lg border border-white/10 bg-white/5 p-4 backdrop-blur-md hover:bg-white/10"
              >
                <div className="flex items-start gap-3">
                  <img
                    src={issue.user.avatar_url}
                    alt={issue.user.login}
                    className="h-8 w-8 rounded-full"
                  />
                  <div className="flex-1 min-w-0">
                    <p className="font-medium">
                      <span className="text-muted-foreground">#{issue.number}</span> {issue.title}
                    </p>
                    <p className="mt-1 text-xs text-muted-foreground">
                      {issue.user.login} • {formatRelativeTime(issue.created_at)}
                    </p>
                    {issue.labels.length > 0 && (
                      <div className="mt-2 flex flex-wrap gap-1">
                        {issue.labels.map((label) => (
                          <span
                            key={label.name}
                            className="rounded-full px-2 py-0.5 text-xs"
                            style={{ backgroundColor: `#${label.color}20`, color: `#${label.color}` }}
                          >
                            {label.name}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              </a>
            ))
          )}
        </div>
      )}
    </div>
  );
}
