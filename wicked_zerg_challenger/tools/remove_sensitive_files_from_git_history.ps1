#!/usr/bin/env pwsh
# -*- coding: utf-8 -*-
<#
.SYNOPSIS
    Git 히스토리에서 민감한 정보가 포함된 파일 완전 제거
    
.DESCRIPTION
    이미 Git 히스토리에 올라간 민감한 정보가 포함된 파일을 히스토리에서 완전히 제거합니다.
    BFG Repo-Cleaner 또는 git filter-branch를 사용합니다.
    
.EXAMPLE
    .\remove_sensitive_files_from_git_history.ps1
    
.NOTES
    ⚠️ 경고: 이 스크립트는 Git 히스토리를 다시 작성합니다!
    - 이미 푸시된 커밋을 수정하면 force push가 필요합니다
    - 다른 사람과 공유하는 저장소라면 문제가 될 수 있습니다
    - 작업 전 반드시 백업을 생성하세요
#>

$ErrorActionPreference = "Stop"

Write-Host "=" * 70 -ForegroundColor Red
Write-Host "⚠️  Git 히스토리에서 민감한 파일 제거" -ForegroundColor Red
Write-Host "=" * 70 -ForegroundColor Red
Write-Host ""
Write-Host "이 작업은 Git 히스토리를 다시 작성합니다!" -ForegroundColor Yellow
Write-Host "작업 전 반드시 백업을 생성하세요!" -ForegroundColor Yellow
Write-Host ""

# Git 저장소 확인
if (-not (Test-Path ".git")) {
    Write-Host "❌ 현재 디렉토리가 Git 저장소가 아닙니다." -ForegroundColor Red
    exit 1
}

# 현재 브랜치 확인
$currentBranch = git rev-parse --abbrev-ref HEAD
Write-Host "현재 브랜치: $currentBranch" -ForegroundColor Cyan
Write-Host ""

# 경고 및 확인
Write-Host "⚠️  경고 사항:" -ForegroundColor Yellow
Write-Host "  1. 이 작업은 Git 히스토리를 다시 작성합니다" -ForegroundColor White
Write-Host "  2. 이미 푸시된 커밋을 수정하면 force push가 필요합니다" -ForegroundColor White
Write-Host "  3. 다른 사람과 공유하는 저장소라면 문제가 될 수 있습니다" -ForegroundColor White
Write-Host "  4. 작업 전 반드시 백업 브랜치를 생성합니다" -ForegroundColor White
Write-Host ""

$confirm = Read-Host "계속하시겠습니까? (yes 입력 필요)"
if ($confirm -ne "yes") {
    Write-Host "작업이 취소되었습니다." -ForegroundColor Yellow
    exit 0
}

Write-Host ""
Write-Host "=" * 70 -ForegroundColor Cyan
Write-Host "1단계: Git 히스토리에서 민감한 파일 검색" -ForegroundColor Cyan
Write-Host "=" * 70 -ForegroundColor Cyan
Write-Host ""

# 민감한 파일 패턴
$sensitivePatterns = @(
    # API 키 관련
    "**/API_KEY_*.md",
    "**/API_KEYS_*.md",
    "**/*API_KEY*.md",
    "**/GEMINI_API_KEY*.md",
    "**/MANUS_API_KEY*.md",
    "**/NEW_API_KEY_SETUP.md",
    "**/REMOVE_API_KEY_FROM_GIT_HISTORY.md",
    
    # 보안 관련 문서
    "**/SECRET*.md",
    "**/PASSWORD*.md",
    "**/TOKEN*.md",
    "**/CREDENTIALS*.md",
    "**/SECURITY*.md",
    
    # 스크립트
    "**/remove_api_key_from_git_history.sh",
    "**/remove_api_key_from_git_history.ps1",
    
    # 설정 파일
    "**/local.properties",
    "**/api_keys/**",
    "**/secrets/**",
    "**/monitoring/api_keys/**",
    "**/monitoring/secrets/**",
    
    # 민감한 정보가 포함된 파일
    "**/*_api_key.txt",
    "**/api_key*.txt",
    "**/manus_api_key.txt"
)

# Git 히스토리에서 민감한 파일 검색
Write-Host "Git 히스토리에서 민감한 파일 검색 중..." -ForegroundColor Yellow
Write-Host ""

$foundFiles = @()
foreach ($pattern in $sensitivePatterns) {
    # Git 히스토리에서 파일 검색
    $files = git log --all --full-history --pretty=format: --name-only -- "$pattern" | 
             Where-Object { $_ -ne "" } | 
             Sort-Object -Unique
    
    foreach ($file in $files) {
        if ($file -and -not ($foundFiles -contains $file)) {
            $foundFiles += $file
            
            # 파일이 실제로 히스토리에 있는지 확인
            $exists = git log --all --full-history -- "$file" --oneline | Select-Object -First 1
            if ($exists) {
                Write-Host "  발견: $file" -ForegroundColor Yellow
            }
        }
    }
}

# 추가로 API 키 패턴이 포함된 파일 검색
Write-Host ""
Write-Host "API 키 패턴이 포함된 파일 검색 중..." -ForegroundColor Yellow
Write-Host ""

$apiKeyPatterns = @(
    "AIzaSy[A-Za-z0-9_-]{35}",
    "AIzaSyBDdPWJyXs56AxeCPmqZpySFOVPjjSt_CM",
    "sk-[A-Za-z0-9]{32,}"
)

foreach ($pattern in $apiKeyPatterns) {
    $commits = git log --all -S "$pattern" --oneline --name-only
    if ($commits) {
        Write-Host "  API 키 패턴 발견: $pattern" -ForegroundColor Red
        $commits | ForEach-Object {
            if ($_ -match "^\s+[^\s]") {
                $foundFiles += $_.Trim()
            }
        }
    }
}

$foundFiles = $foundFiles | Where-Object { $_ -ne "" } | Sort-Object -Unique

Write-Host ""
Write-Host "=" * 70 -ForegroundColor Cyan
Write-Host "검색 결과" -ForegroundColor Cyan
Write-Host "=" * 70 -ForegroundColor Cyan
Write-Host ""

if ($foundFiles.Count -eq 0) {
    Write-Host "✅ Git 히스토리에서 민감한 파일이 발견되지 않았습니다." -ForegroundColor Green
    Write-Host ""
    exit 0
}

Write-Host "발견된 파일 수: $($foundFiles.Count)" -ForegroundColor Yellow
Write-Host ""
Write-Host "제거할 파일 목록:" -ForegroundColor Yellow
foreach ($file in $foundFiles) {
    Write-Host "  - $file" -ForegroundColor White
}

Write-Host ""
$confirmRemove = Read-Host "위 파일들을 Git 히스토리에서 제거하시겠습니까? (yes 입력 필요)"
if ($confirmRemove -ne "yes") {
    Write-Host "작업이 취소되었습니다." -ForegroundColor Yellow
    exit 0
}

Write-Host ""
Write-Host "=" * 70 -ForegroundColor Cyan
Write-Host "2단계: 백업 브랜치 생성" -ForegroundColor Cyan
Write-Host "=" * 70 -ForegroundColor Cyan
Write-Host ""

# 백업 브랜치 생성
$backupBranch = "backup-before-sensitive-removal-$(Get-Date -Format 'yyyyMMdd-HHmmss')"
git branch $backupBranch
Write-Host "✅ 백업 브랜치 생성: $backupBranch" -ForegroundColor Green
Write-Host ""

Write-Host "=" * 70 -ForegroundColor Cyan
Write-Host "3단계: Git 히스토리에서 파일 제거" -ForegroundColor Cyan
Write-Host "=" * 70 -ForegroundColor Cyan
Write-Host ""

# 방법 선택: BFG Repo-Cleaner 또는 git filter-branch
Write-Host "제거 방법 선택:" -ForegroundColor Yellow
Write-Host "  1. git filter-branch (기본, 모든 Git에서 사용 가능)" -ForegroundColor White
Write-Host "  2. BFG Repo-Cleaner (더 빠름, 별도 설치 필요)" -ForegroundColor White
Write-Host ""

$method = Read-Host "방법 선택 (1 또는 2, 기본값: 1)"
if (-not $method) {
    $method = "1"
}

if ($method -eq "2") {
    # BFG Repo-Cleaner 사용
    Write-Host ""
    Write-Host "BFG Repo-Cleaner 사용..." -ForegroundColor Yellow
    
    # BFG 설치 확인
    $bfgInstalled = Get-Command "bfg" -ErrorAction SilentlyContinue
    if (-not $bfgInstalled) {
        Write-Host "❌ BFG Repo-Cleaner가 설치되어 있지 않습니다." -ForegroundColor Red
        Write-Host "   설치 방법: https://rtyley.github.io/bfg-repo-cleaner/" -ForegroundColor Yellow
        Write-Host "   또는 방법 1 (git filter-branch)을 사용하세요." -ForegroundColor Yellow
        exit 1
    }
    
    # 제거할 파일 목록을 파일로 저장
    $fileList = "sensitive_files_to_remove.txt"
    $foundFiles | Out-File -FilePath $fileList -Encoding UTF8
    
    Write-Host "BFG Repo-Cleaner로 파일 제거 중..." -ForegroundColor Yellow
    bfg --delete-files $fileList
    
    # 임시 파일 삭제
    Remove-Item $fileList -ErrorAction SilentlyContinue
    
} else {
    # git filter-branch 사용
    Write-Host ""
    Write-Host "git filter-branch 사용..." -ForegroundColor Yellow
    Write-Host "이 작업은 시간이 걸릴 수 있습니다..." -ForegroundColor Yellow
    Write-Host ""
    
    # 각 파일에 대해 filter-branch 실행
    $fileListForFilter = $foundFiles -join ' '
    git filter-branch --force --index-filter `
        "git rm --cached --ignore-unmatch $fileListForFilter" `
        --prune-empty --tag-name-filter cat -- --all
    
    Write-Host ""
    Write-Host "Git 히스토리 정리 중..." -ForegroundColor Yellow
    
    # 정리
    git reflog expire --expire=now --all
    git gc --prune=now --aggressive
}

Write-Host ""
Write-Host "=" * 70 -ForegroundColor Green
Write-Host "작업 완료" -ForegroundColor Green
Write-Host "=" * 70 -ForegroundColor Green
Write-Host ""

Write-Host "✅ Git 히스토리에서 민감한 파일이 제거되었습니다." -ForegroundColor Green
Write-Host ""
Write-Host "백업 브랜치: $backupBranch" -ForegroundColor Cyan
Write-Host ""

Write-Host "다음 단계:" -ForegroundColor Yellow
Write-Host "  1. 히스토리 확인: git log --all --oneline | Select-Object -First 20" -ForegroundColor White
Write-Host "  2. 파일이 제거되었는지 확인: git log --all -- `"$($foundFiles[0])`"" -ForegroundColor White
Write-Host "  3. 문제가 없으면 푸시:" -ForegroundColor White
Write-Host "     git push --force --all" -ForegroundColor White
Write-Host "     git push --force --tags" -ForegroundColor White
Write-Host ""
Write-Host "문제가 발생하면 다음 명령어로 복구:" -ForegroundColor Yellow
Write-Host "  git reset --hard $backupBranch" -ForegroundColor White
Write-Host ""
