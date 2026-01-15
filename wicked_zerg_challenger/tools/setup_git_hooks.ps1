#!/usr/bin/env pwsh
# Git Hooks 설정 스크립트
# 사용법: .\setup_git_hooks.ps1

$ErrorActionPreference = "Stop"

Write-Host "=" * 70 -ForegroundColor Cyan
Write-Host "🔧 Git Hooks 설정" -ForegroundColor Cyan
Write-Host "=" * 70 -ForegroundColor Cyan
Write-Host ""

# Git 저장소 확인
if (-not (Test-Path ".git")) {
    Write-Host "❌ 현재 디렉토리가 Git 저장소가 아닙니다." -ForegroundColor Red
    exit 1
}

# .git/hooks 디렉토리 확인 및 생성
$hooksDir = ".git/hooks"
if (-not (Test-Path $hooksDir)) {
    New-Item -ItemType Directory -Path $hooksDir -Force | Out-Null
    Write-Host "✅ .git/hooks 디렉토리 생성 완료" -ForegroundColor Green
}

# pre-commit hook 설치
$preCommitHook = Join-Path $hooksDir "pre-commit"
$hookScript = @"
#!/bin/sh
# Git Pre-commit Hook - 민감한 정보 검사

cd "`$(git rev-parse --show-toplevel)"

# PowerShell 스크립트 실행 (Windows)
if command -v pwsh >/dev/null 2>&1; then
    pwsh -File "tools/pre_commit_security_check.ps1"
    exit_code=`$?
    if [ `$exit_code -ne 0 ]; then
        exit 1
    fi
fi

# Bash 스크립트 실행 (Linux/Mac/Git Bash)
if [ -f "tools/pre_commit_security_check.sh" ]; then
    chmod +x "tools/pre_commit_security_check.sh"
    ./tools/pre_commit_security_check.sh
    exit_code=`$?
    if [ `$exit_code -ne 0 ]; then
        exit 1
    fi
fi

exit 0
"@

$hookScript | Out-File -FilePath $preCommitHook -Encoding UTF8 -NoNewline

# 실행 권한 부여 (Unix 계열)
if ($IsLinux -or $IsMacOS -or (Get-Command "chmod" -ErrorAction SilentlyContinue)) {
    try {
        & chmod +x $preCommitHook 2>$null
    } catch {
        # Windows에서는 chmod가 없을 수 있음
    }
}

Write-Host "✅ Pre-commit hook 설치 완료" -ForegroundColor Green
Write-Host "   위치: $preCommitHook" -ForegroundColor Gray
Write-Host ""

# 테스트 실행
Write-Host "🧪 Hook 테스트 실행 중..." -ForegroundColor Yellow
Write-Host ""

try {
    & pwsh -File "tools/pre_commit_security_check.ps1"
    Write-Host ""
    Write-Host "✅ Hook이 정상적으로 작동합니다." -ForegroundColor Green
} catch {
    Write-Host "⚠️  Hook 테스트 중 오류 발생 (무시 가능)" -ForegroundColor Yellow
    Write-Host "   $($_.Exception.Message)" -ForegroundColor Gray
}

Write-Host ""
Write-Host "=" * 70 -ForegroundColor Cyan
Write-Host "설정 완료" -ForegroundColor Cyan
Write-Host "=" * 70 -ForegroundColor Cyan
Write-Host ""
Write-Host "이제 Git 커밋 시 자동으로 민감한 정보를 검사합니다." -ForegroundColor Green
Write-Host ""
Write-Host "수동 검사 (권장):" -ForegroundColor Yellow
Write-Host "  .\tools\double_check_before_commit.ps1  (이중 검사 - 권장)" -ForegroundColor White
Write-Host "  .\tools\pre_commit_security_check.ps1   (기본 검사)" -ForegroundColor White
Write-Host ""

if ($gitRoot) {
    Pop-Location
}
