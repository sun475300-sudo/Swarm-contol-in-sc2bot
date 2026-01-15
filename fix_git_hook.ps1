#!/usr/bin/env pwsh
# Git Pre-commit Hook 완전 수정 스크립트
# 이 스크립트를 실행하면 Git Hook 문제를 자동으로 해결합니다.

Write-Host "? Git Pre-commit Hook 수정 중..." -ForegroundColor Cyan
Write-Host ""

# 현재 디렉토리가 Git 저장소인지 확인
if (-not (Test-Path ".git")) {
    Write-Host "? 현재 디렉토리가 Git 저장소가 아닙니다." -ForegroundColor Red
    exit 1
}

# .git/hooks 디렉토리 생성 (없으면)
$hooksDir = ".git\hooks"
if (-not (Test-Path $hooksDir)) {
    New-Item -ItemType Directory -Path $hooksDir -Force | Out-Null
    Write-Host "? .git/hooks 디렉토리 생성 완료" -ForegroundColor Green
}

# 1. 현재 Hook 파일 백업
if (Test-Path "$hooksDir\pre-commit") {
    $backupPath = "$hooksDir\pre-commit.backup.$(Get-Date -Format 'yyyyMMdd_HHmmss')"
    Copy-Item "$hooksDir\pre-commit" $backupPath
    Write-Host "? 기존 Hook 파일 백업 완료: $backupPath" -ForegroundColor Green
}

# 2. 새 Hook 파일 생성 (LF, UTF-8 without BOM)
$hookContent = @"
#!/bin/sh
# Git Pre-commit Hook - Security Check
# Windows Git Bash / Linux / Mac 모두 지원

cd "$(git rev-parse --show-toplevel)"

# Windows에서 PowerShell 스크립트 실행
if [ -n "$WINDIR" ] || [ -n "$MSYSTEM" ]; then
    # PowerShell Core (pwsh) 우선
    if command -v pwsh.exe >/dev/null 2>&1; then
        if [ -f "wicked_zerg_challenger/tools/pre_commit_security_check.ps1" ]; then
            pwsh.exe -File "wicked_zerg_challenger/tools/pre_commit_security_check.ps1"
            exit_code=$?
            if [ $exit_code -ne 0 ]; then
                exit 1
            fi
        elif [ -f "tools/pre_commit_security_check.ps1" ]; then
            pwsh.exe -File "tools/pre_commit_security_check.ps1"
            exit_code=$?
            if [ $exit_code -ne 0 ]; then
                exit 1
            fi
        fi
    # Windows PowerShell (powershell.exe)
    elif command -v powershell.exe >/dev/null 2>&1; then
        if [ -f "wicked_zerg_challenger/tools/pre_commit_security_check.ps1" ]; then
            powershell.exe -File "wicked_zerg_challenger/tools/pre_commit_security_check.ps1"
            exit_code=`$?
            if [ `$exit_code -ne 0 ]; then
                exit 1
            fi
        elif [ -f "tools/pre_commit_security_check.ps1" ]; then
            powershell.exe -File "tools/pre_commit_security_check.ps1"
            exit_code=`$?
            if [ `$exit_code -ne 0 ]; then
                exit 1
            fi
        fi
    fi
else
    # Linux/Mac: Bash 스크립트 실행
    if [ -f "wicked_zerg_challenger/tools/pre_commit_security_check.sh" ]; then
        chmod +x "wicked_zerg_challenger/tools/pre_commit_security_check.sh" 2>/dev/null
        ./wicked_zerg_challenger/tools/pre_commit_security_check.sh
        exit_code=`$?
        if [ `$exit_code -ne 0 ]; then
            exit 1
        fi
    elif [ -f "tools/pre_commit_security_check.sh" ]; then
        chmod +x "tools/pre_commit_security_check.sh" 2>/dev/null
        ./tools/pre_commit_security_check.sh
        exit_code=`$?
        if [ `$exit_code -ne 0 ]; then
            exit 1
        fi
    fi
fi

exit 0
"@

# 3. LF 줄바꿈으로 저장 (UTF-8 without BOM)
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
$hookContent = $hookContent -replace "`r`n", "`n" -replace "`r", "`n"
[System.IO.File]::WriteAllText("$hooksDir\pre-commit", $hookContent, $utf8NoBom)

Write-Host "? Hook 파일 생성 완료 (LF, UTF-8 without BOM)" -ForegroundColor Green

# 4. Git Bash로 테스트 (가능한 경우)
Write-Host ""
Write-Host "? Hook 테스트 중..." -ForegroundColor Yellow

$gitBashPaths = @(
    "C:\Program Files\Git\bin\bash.exe",
    "C:\Program Files (x86)\Git\bin\bash.exe",
    "$env:ProgramFiles\Git\bin\bash.exe",
    "$env:ProgramFiles(x86)\Git\bin\bash.exe"
)

$gitBashFound = $false
foreach ($path in $gitBashPaths) {
    if (Test-Path $path) {
        $gitBashPath = $path
        $gitBashFound = $true
        break
    }
}

if ($gitBashFound) {
    Write-Host "   Git Bash 발견: $gitBashPath" -ForegroundColor Gray
    $projectRoot = (Get-Location).Path
    $projectRootUnix = $projectRoot -replace "\\", "/" -replace "^([A-Z]):", "/`$1" -replace ":", ""
    
    Write-Host "   Hook 직접 실행 테스트..." -ForegroundColor Gray
    try {
        $result = & $gitBashPath -c "cd '$projectRootUnix' && .git/hooks/pre-commit" 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Host "? Hook 실행 성공" -ForegroundColor Green
        } else {
            Write-Host "??  Hook 실행 완료 (종료 코드: $LASTEXITCODE)" -ForegroundColor Yellow
            Write-Host "   출력: $result" -ForegroundColor Gray
        }
    } catch {
        Write-Host "??  Hook 테스트 중 오류 (정상일 수 있음): $_" -ForegroundColor Yellow
    }
} else {
    Write-Host "??  Git Bash를 찾을 수 없습니다. 수동으로 테스트하세요." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "? 완료!" -ForegroundColor Green
Write-Host ""
Write-Host "? 다음 단계:" -ForegroundColor Cyan
Write-Host "   1. 다음 명령으로 커밋 테스트: git commit --allow-empty -m 'Test hook'" -ForegroundColor White
Write-Host "   2. 오류가 계속되면 --no-verify 사용: git commit --no-verify -m 'Your message'" -ForegroundColor White
Write-Host "   3. 자세한 가이드는 GIT_HOOK_ERROR_COMPLETE_GUIDE.md 참조" -ForegroundColor White
Write-Host ""
