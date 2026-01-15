#!/usr/bin/env pwsh
# -*- coding: utf-8 -*-
<#
.SYNOPSIS
    커밋 전 이중 검사 스크립트
    
.DESCRIPTION
    커밋 전에 민감한 정보를 두 번 이상 검사합니다.
    1차: 스테이징된 파일 검사
    2차: 전체 프로젝트 검사 (선택적)
    
.EXAMPLE
    .\double_check_before_commit.ps1
    
.NOTES
    이 스크립트는 커밋 전에 반드시 실행해야 합니다.
#>

$ErrorActionPreference = "Stop"

Write-Host "=" * 70 -ForegroundColor Cyan
Write-Host "🔒 커밋 전 이중 검사 시스템" -ForegroundColor Cyan
Write-Host "=" * 70 -ForegroundColor Cyan
Write-Host ""

# 검사할 패턴들
$sensitivePatterns = @(
    # API 키 패턴
    "AIzaSy[A-Za-z0-9_-]{35}",  # Google API Key
    "sk-[A-Za-z0-9]{32,}",      # OpenAI API Key
    "xox[baprs]-[0-9]{10,13}-[0-9]{10,13}-[A-Za-z0-9]{24,32}",  # Slack Token
    "[0-9a-f]{32}",             # 일반적인 32자리 해시
    "[0-9a-f]{40}",             # 40자리 해시
    
    # 비밀번호/토큰 패턴
    "password\s*[:=]\s*['\""]?[^'\""\s]{8,}",
    "passwd\s*[:=]\s*['\""]?[^'\""\s]{8,}",
    "secret\s*[:=]\s*['\""]?[^'\""\s]{8,}",
    "token\s*[:=]\s*['\""]?[^'\""\s]{20,}",
    "api[_-]?key\s*[:=]\s*['\""]?[A-Za-z0-9_-]{20,}",
    "apikey\s*[:=]\s*['\""]?[A-Za-z0-9_-]{20,}",
    "api[_-]?token\s*[:=]\s*['\""]?[A-Za-z0-9_-]{20,}",
    
    # 알려진 API 키 (절대 커밋되면 안 됨)
    "AIzaSyBDdPWJyXs56AxeCPmqZpySFOVPjjSt_CM"   # 알려진 API 키
)

$fileExtensions = @("*.py", "*.kt", "*.java", "*.js", "*.ts", "*.md", "*.txt", "*.json", "*.yaml", "*.yml", "*.sh", "*.ps1", "*.bat")

$foundIssues = @()
$checkedFiles = 0

# ============================================================================
# 1차 검사: 스테이징된 파일
# ============================================================================

Write-Host "📋 1차 검사: 스테이징된 파일" -ForegroundColor Yellow
Write-Host "-" * 70 -ForegroundColor Gray
Write-Host ""

try {
    $stagedFiles = git diff --cached --name-only --diff-filter=ACM 2>$null
    
    if ($stagedFiles) {
        Write-Host "스테이징된 파일 수: $($stagedFiles.Count)" -ForegroundColor White
        Write-Host ""
        
        foreach ($filePath in $stagedFiles) {
            if (Test-Path $filePath) {
                $file = Get-Item $filePath
                $shouldCheck = $false
                
                foreach ($ext in $fileExtensions) {
                    if ($file.Name -like $ext) {
                        $shouldCheck = $true
                        break
                    }
                }
                
                if ($shouldCheck) {
                    $checkedFiles++
                    $content = Get-Content $file.FullName -Raw -ErrorAction SilentlyContinue
                    
                    if ($content) {
                        foreach ($pattern in $sensitivePatterns) {
                            if ($content -match $pattern) {
                                $lines = $content -split "`n"
                                $matchingLine = $lines | Where-Object { $_ -match $pattern } | Select-Object -First 1
                                $lineNumber = [Array]::IndexOf($lines, $matchingLine) + 1
                                
                                $foundIssues += [PSCustomObject]@{
                                    File = $file.FullName
                                    Pattern = $pattern
                                    Line = $lineNumber
                                    Preview = ($matchingLine -replace $pattern, "[REDACTED]").Substring(0, [Math]::Min(80, ($matchingLine -replace $pattern, "[REDACTED]").Length))
                                    CheckLevel = "1차 (스테이징된 파일)"
                                }
                            }
                        }
                    }
                }
            }
        }
    } else {
        Write-Host "스테이징된 파일이 없습니다." -ForegroundColor Gray
        Write-Host ""
    }
} catch {
    Write-Host "⚠️  Git 저장소가 아닙니다. 1차 검사를 건너뜁니다." -ForegroundColor Yellow
    Write-Host ""
}

Write-Host ""

# ============================================================================
# 2차 검사: 전체 프로젝트 (선택적)
# ============================================================================

Write-Host "📋 2차 검사: 전체 프로젝트 (선택적)" -ForegroundColor Yellow
Write-Host "-" * 70 -ForegroundColor Gray
Write-Host ""

$runFullCheck = Read-Host "전체 프로젝트를 검사하시겠습니까? (y/n, 기본값: n)"

if ($runFullCheck -eq "y" -or $runFullCheck -eq "Y") {
    Write-Host ""
    Write-Host "전체 프로젝트 검사 중..." -ForegroundColor Yellow
    Write-Host ""
    
    foreach ($ext in $fileExtensions) {
        $files = Get-ChildItem -Path . -Filter $ext -Recurse -ErrorAction SilentlyContinue | 
                 Where-Object { 
                     $_.FullName -notmatch '\.git|node_modules|venv|__pycache__|\.gradle|build|\.idea|\.vscode' -and
                     $_.FullName -notmatch 'tools/pre_commit_security_check|tools/double_check_before_commit'
                 }
        
        foreach ($file in $files) {
            $checkedFiles++
            $content = Get-Content $file.FullName -Raw -ErrorAction SilentlyContinue
            
            if ($content) {
                foreach ($pattern in $sensitivePatterns) {
                    if ($content -match $pattern) {
                        # 이미 1차 검사에서 발견된 파일은 제외
                        $alreadyFound = $foundIssues | Where-Object { $_.File -eq $file.FullName -and $_.Pattern -eq $pattern }
                        
                        if (-not $alreadyFound) {
                            $lines = $content -split "`n"
                            $matchingLine = $lines | Where-Object { $_ -match $pattern } | Select-Object -First 1
                            $lineNumber = [Array]::IndexOf($lines, $matchingLine) + 1
                            
                            $foundIssues += [PSCustomObject]@{
                                File = $file.FullName
                                Pattern = $pattern
                                Line = $lineNumber
                                Preview = ($matchingLine -replace $pattern, "[REDACTED]").Substring(0, [Math]::Min(80, ($matchingLine -replace $pattern, "[REDACTED]").Length))
                                CheckLevel = "2차 (전체 프로젝트)"
                            }
                        }
                    }
                }
            }
        }
    }
} else {
    Write-Host "2차 검사를 건너뜁니다." -ForegroundColor Gray
    Write-Host ""
}

Write-Host ""

# ============================================================================
# 검사 결과
# ============================================================================

Write-Host "=" * 70 -ForegroundColor Cyan
Write-Host "검사 결과" -ForegroundColor Cyan
Write-Host "=" * 70 -ForegroundColor Cyan
Write-Host ""
Write-Host "검사한 파일 수: $checkedFiles" -ForegroundColor White
Write-Host ""

if ($foundIssues.Count -gt 0) {
    Write-Host "🚨 민감한 정보가 발견되었습니다!" -ForegroundColor Red
    Write-Host ""
    
    # 검사 레벨별로 그룹화
    $level1Issues = $foundIssues | Where-Object { $_.CheckLevel -eq "1차 (스테이징된 파일)" }
    $level2Issues = $foundIssues | Where-Object { $_.CheckLevel -eq "2차 (전체 프로젝트)" }
    
    if ($level1Issues.Count -gt 0) {
        Write-Host "❌ 1차 검사 (스테이징된 파일)에서 발견:" -ForegroundColor Red
        Write-Host ""
        foreach ($issue in $level1Issues) {
            Write-Host "  파일: $($issue.File)" -ForegroundColor Yellow
            Write-Host "  패턴: $($issue.Pattern)" -ForegroundColor Yellow
            Write-Host "  라인: $($issue.Line)" -ForegroundColor Yellow
            if ($issue.Preview) {
                Write-Host "  미리보기: $($issue.Preview)" -ForegroundColor Gray
            }
            Write-Host ""
        }
    }
    
    if ($level2Issues.Count -gt 0) {
        Write-Host "⚠️  2차 검사 (전체 프로젝트)에서 발견:" -ForegroundColor Yellow
        Write-Host ""
        foreach ($issue in $level2Issues) {
            Write-Host "  파일: $($issue.File)" -ForegroundColor Yellow
            Write-Host "  패턴: $($issue.Pattern)" -ForegroundColor Yellow
            Write-Host "  라인: $($issue.Line)" -ForegroundColor Yellow
            if ($issue.Preview) {
                Write-Host "  미리보기: $($issue.Preview)" -ForegroundColor Gray
            }
            Write-Host ""
        }
    }
    
    Write-Host "=" * 70 -ForegroundColor Red
    Write-Host "❌ 커밋이 차단되었습니다!" -ForegroundColor Red
    Write-Host "=" * 70 -ForegroundColor Red
    Write-Host ""
    Write-Host "조치 사항:" -ForegroundColor Yellow
    Write-Host "  1. 위 파일들에서 민감한 정보를 제거하세요" -ForegroundColor White
    Write-Host "  2. 플레이스홀더로 대체하세요 (예: [YOUR_API_KEY])" -ForegroundColor White
    Write-Host "  3. 환경 변수나 설정 파일을 사용하세요" -ForegroundColor White
    Write-Host "  4. 다시 검사 후 커밋하세요" -ForegroundColor White
    Write-Host ""
    
    exit 1
} else {
    Write-Host "✅ 모든 검사 통과!" -ForegroundColor Green
    Write-Host ""
    Write-Host "1차 검사: ✅ 통과" -ForegroundColor Green
    if ($runFullCheck -eq "y" -or $runFullCheck -eq "Y") {
        Write-Host "2차 검사: ✅ 통과" -ForegroundColor Green
    }
    Write-Host ""
    Write-Host "안전하게 커밋할 수 있습니다." -ForegroundColor Green
    Write-Host ""
    
    exit 0
}
