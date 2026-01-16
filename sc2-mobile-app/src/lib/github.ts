/**
 * GitHub API 클라이언트
 * 저장소 업데이트 모니터링 및 알림
 */

import axios from 'axios';

const GITHUB_API_URL = 'https://api.github.com';

// 기본 저장소 설정
const DEFAULT_REPO = {
  owner: 'sun475300-sudo',
  repo: 'Swarm-control-in-sc2bot',
};

const api = axios.create({
  baseURL: GITHUB_API_URL,
  timeout: 10000,
  headers: {
    Accept: 'application/vnd.github.v3+json',
  },
});

/**
 * GitHub 커밋 타입
 */
export interface GitHubCommit {
  sha: string;
  message: string;
  author: {
    name: string;
    email: string;
    date: string;
    avatar_url?: string;
  };
  committer: {
    name: string;
    email: string;
    date: string;
  };
  url: string;
  html_url: string;
}

/**
 * GitHub PR 타입
 */
export interface GitHubPullRequest {
  id: number;
  number: number;
  title: string;
  body: string;
  state: 'open' | 'closed';
  user: {
    login: string;
    avatar_url: string;
  };
  created_at: string;
  updated_at: string;
  merged_at: string | null;
  html_url: string;
  additions: number;
  deletions: number;
  changed_files: number;
}

/**
 * GitHub 릴리즈 타입
 */
export interface GitHubRelease {
  id: number;
  tag_name: string;
  name: string;
  body: string;
  draft: boolean;
  prerelease: boolean;
  created_at: string;
  published_at: string;
  author: {
    login: string;
    avatar_url: string;
  };
  html_url: string;
  assets: Array<{
    name: string;
    size: number;
    download_count: number;
    browser_download_url: string;
  }>;
}

/**
 * GitHub 이슈 타입
 */
export interface GitHubIssue {
  id: number;
  number: number;
  title: string;
  body: string;
  state: 'open' | 'closed';
  user: {
    login: string;
    avatar_url: string;
  };
  labels: Array<{
    name: string;
    color: string;
  }>;
  created_at: string;
  updated_at: string;
  html_url: string;
  comments: number;
}

/**
 * GitHub 저장소 정보 타입
 */
export interface GitHubRepository {
  id: number;
  name: string;
  full_name: string;
  description: string;
  html_url: string;
  stargazers_count: number;
  watchers_count: number;
  forks_count: number;
  open_issues_count: number;
  default_branch: string;
  created_at: string;
  updated_at: string;
  pushed_at: string;
  language: string;
  topics: string[];
}

/**
 * GitHub 브랜치 타입
 */
export interface GitHubBranch {
  name: string;
  commit: {
    sha: string;
    url: string;
  };
  protected: boolean;
}

/**
 * GitHub 워크플로우 실행 타입
 */
export interface GitHubWorkflowRun {
  id: number;
  name: string;
  status: 'queued' | 'in_progress' | 'completed';
  conclusion: 'success' | 'failure' | 'cancelled' | 'skipped' | null;
  workflow_id: number;
  html_url: string;
  created_at: string;
  updated_at: string;
  run_number: number;
  event: string;
  head_branch: string;
  head_sha: string;
}

/**
 * 저장소 정보 가져오기
 */
export async function getRepository(
  owner: string = DEFAULT_REPO.owner,
  repo: string = DEFAULT_REPO.repo
): Promise<GitHubRepository | null> {
  try {
    const response = await api.get<GitHubRepository>(`/repos/${owner}/${repo}`);
    return response.data;
  } catch (error) {
    console.error('Failed to fetch repository:', error);
    return null;
  }
}

/**
 * 최근 커밋 목록 가져오기
 */
export async function getCommits(
  owner: string = DEFAULT_REPO.owner,
  repo: string = DEFAULT_REPO.repo,
  limit: number = 10,
  branch?: string
): Promise<GitHubCommit[]> {
  try {
    const params: Record<string, any> = { per_page: limit };
    if (branch) params.sha = branch;

    const response = await api.get(`/repos/${owner}/${repo}/commits`, { params });
    return response.data.map((item: any) => ({
      sha: item.sha,
      message: item.commit.message,
      author: {
        name: item.commit.author.name,
        email: item.commit.author.email,
        date: item.commit.author.date,
        avatar_url: item.author?.avatar_url,
      },
      committer: item.commit.committer,
      url: item.url,
      html_url: item.html_url,
    }));
  } catch (error) {
    console.error('Failed to fetch commits:', error);
    return [];
  }
}

/**
 * PR 목록 가져오기
 */
export async function getPullRequests(
  owner: string = DEFAULT_REPO.owner,
  repo: string = DEFAULT_REPO.repo,
  state: 'open' | 'closed' | 'all' = 'all',
  limit: number = 10
): Promise<GitHubPullRequest[]> {
  try {
    const response = await api.get(`/repos/${owner}/${repo}/pulls`, {
      params: { state, per_page: limit, sort: 'updated', direction: 'desc' },
    });
    return response.data;
  } catch (error) {
    console.error('Failed to fetch pull requests:', error);
    return [];
  }
}

/**
 * 릴리즈 목록 가져오기
 */
export async function getReleases(
  owner: string = DEFAULT_REPO.owner,
  repo: string = DEFAULT_REPO.repo,
  limit: number = 10
): Promise<GitHubRelease[]> {
  try {
    const response = await api.get(`/repos/${owner}/${repo}/releases`, {
      params: { per_page: limit },
    });
    return response.data;
  } catch (error) {
    console.error('Failed to fetch releases:', error);
    return [];
  }
}

/**
 * 최신 릴리즈 가져오기
 */
export async function getLatestRelease(
  owner: string = DEFAULT_REPO.owner,
  repo: string = DEFAULT_REPO.repo
): Promise<GitHubRelease | null> {
  try {
    const response = await api.get(`/repos/${owner}/${repo}/releases/latest`);
    return response.data;
  } catch (error) {
    console.error('Failed to fetch latest release:', error);
    return null;
  }
}

/**
 * 이슈 목록 가져오기
 */
export async function getIssues(
  owner: string = DEFAULT_REPO.owner,
  repo: string = DEFAULT_REPO.repo,
  state: 'open' | 'closed' | 'all' = 'open',
  limit: number = 10
): Promise<GitHubIssue[]> {
  try {
    const response = await api.get(`/repos/${owner}/${repo}/issues`, {
      params: { state, per_page: limit, sort: 'updated', direction: 'desc' },
    });
    // PR은 이슈로도 반환되므로 필터링
    return response.data.filter((item: any) => !item.pull_request);
  } catch (error) {
    console.error('Failed to fetch issues:', error);
    return [];
  }
}

/**
 * 브랜치 목록 가져오기
 */
export async function getBranches(
  owner: string = DEFAULT_REPO.owner,
  repo: string = DEFAULT_REPO.repo
): Promise<GitHubBranch[]> {
  try {
    const response = await api.get(`/repos/${owner}/${repo}/branches`);
    return response.data;
  } catch (error) {
    console.error('Failed to fetch branches:', error);
    return [];
  }
}

/**
 * 워크플로우 실행 목록 가져오기
 */
export async function getWorkflowRuns(
  owner: string = DEFAULT_REPO.owner,
  repo: string = DEFAULT_REPO.repo,
  limit: number = 10
): Promise<GitHubWorkflowRun[]> {
  try {
    const response = await api.get(`/repos/${owner}/${repo}/actions/runs`, {
      params: { per_page: limit },
    });
    return response.data.workflow_runs || [];
  } catch (error) {
    console.error('Failed to fetch workflow runs:', error);
    return [];
  }
}

/**
 * 저장소 통계 가져오기
 */
export async function getRepositoryStats(
  owner: string = DEFAULT_REPO.owner,
  repo: string = DEFAULT_REPO.repo
) {
  const [repository, commits, prs, releases, issues] = await Promise.all([
    getRepository(owner, repo),
    getCommits(owner, repo, 5),
    getPullRequests(owner, repo, 'open', 5),
    getReleases(owner, repo, 3),
    getIssues(owner, repo, 'open', 5),
  ]);

  return {
    repository,
    recentCommits: commits,
    openPullRequests: prs,
    recentReleases: releases,
    openIssues: issues,
  };
}

/**
 * 마지막 확인 이후 새로운 업데이트 확인
 */
export async function checkForUpdates(
  lastCheckedAt: Date,
  owner: string = DEFAULT_REPO.owner,
  repo: string = DEFAULT_REPO.repo
): Promise<{
  newCommits: GitHubCommit[];
  newPullRequests: GitHubPullRequest[];
  newReleases: GitHubRelease[];
  newIssues: GitHubIssue[];
}> {
  const [commits, prs, releases, issues] = await Promise.all([
    getCommits(owner, repo, 20),
    getPullRequests(owner, repo, 'all', 20),
    getReleases(owner, repo, 10),
    getIssues(owner, repo, 'all', 20),
  ]);

  const lastCheckedTime = lastCheckedAt.getTime();

  return {
    newCommits: commits.filter(
      (c) => new Date(c.author.date).getTime() > lastCheckedTime
    ),
    newPullRequests: prs.filter(
      (pr) => new Date(pr.created_at).getTime() > lastCheckedTime
    ),
    newReleases: releases.filter(
      (r) => new Date(r.published_at).getTime() > lastCheckedTime
    ),
    newIssues: issues.filter(
      (i) => new Date(i.created_at).getTime() > lastCheckedTime
    ),
  };
}

/**
 * 저장소 설정 저장
 */
export function saveRepositoryConfig(owner: string, repo: string): void {
  localStorage.setItem('github_owner', owner);
  localStorage.setItem('github_repo', repo);
}

/**
 * 저장소 설정 가져오기
 */
export function getRepositoryConfig(): { owner: string; repo: string } {
  return {
    owner: localStorage.getItem('github_owner') || DEFAULT_REPO.owner,
    repo: localStorage.getItem('github_repo') || DEFAULT_REPO.repo,
  };
}

/**
 * 마지막 확인 시간 저장
 */
export function saveLastCheckedTime(): void {
  localStorage.setItem('github_last_checked', new Date().toISOString());
}

/**
 * 마지막 확인 시간 가져오기
 */
export function getLastCheckedTime(): Date {
  const stored = localStorage.getItem('github_last_checked');
  return stored ? new Date(stored) : new Date(0);
}

/**
 * 상대 시간 포맷팅
 */
export function formatRelativeTime(dateString: string): string {
  const date = new Date(dateString);
  const now = new Date();
  const diff = now.getTime() - date.getTime();

  const minutes = Math.floor(diff / 60000);
  const hours = Math.floor(diff / 3600000);
  const days = Math.floor(diff / 86400000);

  if (minutes < 1) return '방금 전';
  if (minutes < 60) return `${minutes}분 전`;
  if (hours < 24) return `${hours}시간 전`;
  if (days < 7) return `${days}일 전`;
  if (days < 30) return `${Math.floor(days / 7)}주 전`;
  if (days < 365) return `${Math.floor(days / 30)}개월 전`;
  return `${Math.floor(days / 365)}년 전`;
}
