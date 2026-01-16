#!/usr/bin/env pwsh
# -*- coding: utf-8 -*-
<#
.SYNOPSIS
    Git 커밋 전 민감한 정보 검사 스크립트
    
.DESCRIPTION
    커밋 전에 민감한 정보(API 키, 비밀번호 등)가 포함되지 않았는지 검사합니다.
    이 스크립트는 Git pre-commit hook로 사용하거나 수동으로 실행할 수 있습니다.
    
.EXAMPLE
    .\pre_commit_security_check.ps1
    
.NOTES
    이 스크립트는 커밋 전에 자동으로 실행되어 민감한 정보를 차단합니다.
    개선 사항:
    - 강화된 오류 처리 및 예외 관리
    - 파일 읽기 실패 시 안전한 처리
    - 패턴 매칭 실패 시 무시
    - 더 명확한 오류 메시지
#>

# 오류 처리 설정: 오류 발생 시 계속 진행하되 로깅
$ErrorActionPreference = "Continue"

# 전체 스크립트 실행을 try-catch로 감싸기
try {
    $separator = '=' * 70
    Write-Host $separator -ForegroundColor Cyan
    $title = 'Git Pre-Commit Security Check'
    Write-Host $title -ForegroundColor Cyan
    Write-Host $separator -ForegroundColor Cyan
    Write-Host ""

    # Sensitive patterns (generic patterns only, no actual key examples)
    # Using single quotes to prevent PowerShell from interpreting brackets as array indexing
    $sensitivePatterns = @(
        # API Key patterns (avoid matching package hashes in lock files)
        'AIzaSy[A-Za-z0-9_-]{35}',
        'sk-[A-Za-z0-9]{32,}',
        'xox[baprs]-[0-9]{10,13}-[0-9]{10,13}-[A-Za-z0-9]{24,32}',
        # Hash patterns only in non-lock files (handled by exclude list)
        
        # Password patterns (avoid matching variable names)
        # Match: password = "...", password: "...", but not cookieSecret = ...
        '(?<!cookie|session|jwt|auth)(?:password|passwd)\s*[:=]\s*[''"]?[^''"\s]{8,}',
        # Match: secret = "...", secret: "...", but not cookieSecret, sessionSecret
        '(?<!cookie|session|jwt|auth)secret\s*[:=]\s*[''"]?[^''"\s]{8,}',
        # Match: token = "...", token: "...", but not getUserInfoByToken, accessToken
        '(?<!by|access|refresh|session|bearer|auth)token\s*[:=]\s*[''"]?[^''"\s]{20,}'
    )

    # 검사할 파일 확장자
    $fileExtensions = @("*.py", "*.kt", "*.java", "*.js", "*.ts", "*.md", "*.txt", "*.json", "*.yaml", "*.yml", "*.sh", "*.ps1", "*.bat")

    # 검사 결과
    $foundIssues = @()
    $checkedFiles = 0
    $errorCount = 0

    $checkingMsg = 'Checking staged files...'
    Write-Host $checkingMsg -ForegroundColor Yellow
    Write-Host ""

    # Git 스테이징된 파일 가져오기 (개선된 오류 처리)
    $stagedFiles = @()
    try {
        $gitOutput = git diff --cached --name-only --diff-filter=ACM 2>&1
        if ($LASTEXITCODE -eq 0) {
            $stagedFiles = $gitOutput | Where-Object { $_ -and $_.Trim() }
        } else {
            $noStagedMsg = 'Not a Git repository or no staged files found.'
            Write-Host $noStagedMsg -ForegroundColor Yellow
            $scanAllMsg = 'Scanning all files...'
            Write-Host $scanAllMsg -ForegroundColor Yellow
        }
    } catch {
        $gitErrorMsg = 'Git command error: ' + $_
        Write-Host $gitErrorMsg -ForegroundColor Yellow
        $scanAllMsg = 'Scanning all files...'
        Write-Host $scanAllMsg -ForegroundColor Yellow
        $errorCount++
    }

    # 제외 함수 (보안 검사 스크립트 자체와 Hook 파일 제외)
    function Test-ExcludeFile {
        param([string]$filePath)
        
        if ([string]::IsNullOrWhiteSpace($filePath)) {
            return $false
        }
        
        # 경로 정규화 (Windows와 Unix 경로 모두 처리)
        $normalizedPath = $filePath -replace '\\', '/' -replace '//', '/'
        
        # 파일명 추출 (경로의 마지막 부분)
        $fileName = $normalizedPath -split '/' | Select-Object -Last 1
        
        # 제외할 파일명 목록 (간단하게)
        $excludeFileNames = @(
            "pre_commit_security_check.ps1",
            "pre_commit_security_check.sh",
            "pre-commit",
            "pre-commit.ps1"
        )
        
        # Lock 파일 제외 (패키지 해시는 민감정보가 아님)
        $lockFilePatterns = @(
            "pnpm-lock.yaml",
            "package-lock.json",
            "yarn.lock",
            "poetry.lock",
            "Pipfile.lock"
        )
        
        foreach ($pattern in $lockFilePatterns) {
            if ($normalizedPath -match ([regex]::Escape($pattern))) {
                return $true
            }
        }
        
        # 파일명 직접 매칭 (대소문자 무시)
        foreach ($excludeName in $excludeFileNames) {
            if ($fileName -ieq $excludeName) {
                return $true
            }
        }
        
        # 추가 확인: 경로 전체에 제외 파일명이 정확히 포함되어 있는지
        # 부분 문자열 매칭 방지: 경로 구분자 앞뒤로 정확히 일치해야 함
        foreach ($excludeName in $excludeFileNames) {
            # 정확한 경로 패턴 매칭 (부분 문자열 매칭 방지)
            # 예: /.git/hooks/pre-commit, /tools/pre_commit_security_check.ps1
            $escapedName = [regex]::Escape($excludeName)
            
            # 패턴: 경로 구분자(`/`) 앞에 경로 구분자가 없거나 문자열 시작이고,
            #       뒤에 경로 구분자(`/`) 또는 문자열 끝(`$`)이 오는 경우
            # 이렇게 하면 `my-pre-commit-config.ps1` 같은 파일은 매칭되지 않음
            # (경로 구분자 앞에 다른 문자가 없어야 함)
            if ($normalizedPath -match ('(?:^|/)' + $escapedName + '(?:/|$)')) {
                return $true
            }
        }
        
        return $false
    }

# 스테이징된 파일이 없으면 모든 파일 검사
if (-not $stagedFiles) {
    $scanAllMsg = 'Scanning all files...'
    Write-Host $scanAllMsg -ForegroundColor Yellow
    Write-Host ""
    
    foreach ($ext in $fileExtensions) {
        $files = Get-ChildItem -Path . -Filter $ext -Recurse -ErrorAction SilentlyContinue | 
                 Where-Object { 
                     $_.FullName -notmatch '\.git|node_modules|venv|__pycache__|\.gradle|build' -and
                     -not (Test-ExcludeFile $_.FullName) -and
                     $_.FullName -notmatch '(pnpm|package|yarn|poetry)\.lock'
                 }
        
        foreach ($file in $files) {
            try {
                $checkedFiles++
                
                # 파일 읽기 시도 (오류 처리 개선)
                $content = $null
                try {
                    $content = Get-Content $file.FullName -Raw -ErrorAction Stop
                } catch {
                    $readErrorMsg = 'File read failed (ignored): ' + $file.FullName + ' - ' + $_
                    Write-Host $readErrorMsg -ForegroundColor Gray
                    $errorCount++
                    continue
                }
                
                if ($content) {
                    foreach ($pattern in $sensitivePatterns) {
                        try {
                            if ($content -match $pattern) {
                                $lines = $content -split "`n"
                                $matchingLine = $lines | Where-Object { $_ -match $pattern } | Select-Object -First 1
                                if ($matchingLine) {
                                    $lineNumber = [Array]::IndexOf($lines, $matchingLine) + 1
                                    $foundIssues += [PSCustomObject]@{
                                        File = $file.FullName
                                        Pattern = $pattern
                                        Line = $lineNumber
                                    }
                                }
                            }
                        } catch {
                            # 패턴 매칭 실패 시 무시 (오류 로깅만)
                            $matchErrorMsg = 'Pattern match error (ignored): ' + $pattern + ' - ' + $_
                            Write-Host $matchErrorMsg -ForegroundColor Gray
                            $errorCount++
                        }
                    }
                }
            } catch {
                $processErrorMsg = 'File processing error (ignored): ' + $file.FullName + ' - ' + $_
                Write-Host $processErrorMsg -ForegroundColor Gray
                $errorCount++
                continue
            }
        }
    }
} else {
    # 스테이징된 파일만 검사
    foreach ($filePath in $stagedFiles) {
        # 검사에서 제외할 파일은 건너뛰기 (보안 검사 스크립트 자체와 Hook 파일)
        # 상대 경로와 절대 경로 모두 처리
        $normalizedPath = $filePath -replace '\\', '/' -replace '//', '/'
        
        # 제외 로직: 파일명 또는 경로에 제외 패턴이 포함되어 있는지 확인
        # 경로 정규화 후에는 포워드 슬래시만 사용하므로 백슬래시 패턴은 불필요
        if ($normalizedPath -match 'pre_commit_security_check\.(ps1|sh)$' -or
            $normalizedPath -match '/hooks/pre-commit') {
            $excludedMsg = 'File excluded: ' + $filePath
            Write-Host $excludedMsg -ForegroundColor Gray
            continue
        }
        
        # 함수를 통한 제외 확인
        if (Test-ExcludeFile $normalizedPath) {
            $excludedMsg = 'File excluded: ' + $filePath
            Write-Host $excludedMsg -ForegroundColor Gray
            continue
        }
        
        # Lock 파일 직접 제외
        if ($normalizedPath -match '(pnpm|package|yarn|poetry)\.lock|pnpm-lock\.yaml') {
            $excludedMsg = 'Lock file excluded: ' + $filePath
            Write-Host $excludedMsg -ForegroundColor Gray
            continue
        }
        
        if (Test-Path -LiteralPath $filePath) {
            $file = Get-Item $filePath
            $checkedFiles++
            
            # 특정 확장자만 검사
            $shouldCheck = $false
            foreach ($ext in $fileExtensions) {
                if ($file.Name -like $ext) {
                    $shouldCheck = $true
                    break
                }
            }
            
            if ($shouldCheck) {
                # 파일 읽기 시도 (오류 처리 개선)
                $content = $null
                try {
                    $content = Get-Content $file.FullName -Raw -ErrorAction Stop
                } catch {
                    $readErrorMsg = 'File read failed (ignored): ' + $filePath + ' - ' + $_
                    Write-Host $readErrorMsg -ForegroundColor Gray
                    $errorCount++
                    continue
                }
                
                if ($content) {
                    foreach ($pattern in $sensitivePatterns) {
                        try {
                            if ($content -match $pattern) {
                                $lines = $content -split "`n"
                                $matchingLine = $lines | Where-Object { $_ -match $pattern } | Select-Object -First 1
                                if ($matchingLine) {
                                    $lineNumber = [Array]::IndexOf($lines, $matchingLine) + 1
                                    $previewText = $matchingLine -replace $pattern, "[REDACTED]"
                                    $previewLength = [Math]::Min(80, $previewText.Length)
                                    
                                    $foundIssues += [PSCustomObject]@{
                                        File = $file.FullName
                                        Pattern = $pattern
                                        Line = $lineNumber
                                        Preview = if ($previewLength -gt 0) { $previewText.Substring(0, $previewLength) } else { "" }
                                    }
                                }
                            }
                        } catch {
                            # 패턴 매칭 실패 시 무시 (오류 로깅만)
                            $matchErrorMsg = 'Pattern match error (ignored): ' + $pattern + ' in ' + $filePath + ' - ' + $_
                            Write-Host $matchErrorMsg -ForegroundColor Gray
                            $errorCount++
                        }
                    }
                }
            }
        } catch {
            # 파일 처리 오류 무시 (로깅만)
            $processErrorMsg = 'File processing error (ignored): ' + $filePath + ' - ' + $_
            Write-Host $processErrorMsg -ForegroundColor Gray
            $errorCount++
        }
    }

    Write-Host ""
    $separator = '=' * 70
    Write-Host $separator -ForegroundColor Cyan
    $resultTitle = 'Scan Results'
    Write-Host $resultTitle -ForegroundColor Cyan
    Write-Host $separator -ForegroundColor Cyan
    Write-Host ""
    $filesMsg = 'Files checked: ' + $checkedFiles
    Write-Host $filesMsg -ForegroundColor White
    if ($errorCount -gt 0) {
        $errorMsg = 'Errors occurred: ' + $errorCount + ' (ignored)'
        Write-Host $errorMsg -ForegroundColor Yellow
    }
    Write-Host ""

    if ($foundIssues.Count -gt 0) {
        $foundMsg = 'Sensitive information found!'
        Write-Host $foundMsg -ForegroundColor Red
        Write-Host ""
        
        foreach ($issue in $foundIssues) {
            $fileMsg = '  File: ' + $issue.File
            Write-Host $fileMsg -ForegroundColor Yellow
            $patternMsg = '  Pattern: ' + $issue.Pattern
            Write-Host $patternMsg -ForegroundColor Yellow
            $lineMsg = '  Line: ' + $issue.Line
            Write-Host $lineMsg -ForegroundColor Yellow
            if ($issue.Preview) {
                $previewMsg = '  Preview: ' + $issue.Preview
                Write-Host $previewMsg -ForegroundColor Gray
            }
            Write-Host ""
        }
        
        $separator = '=' * 70
        Write-Host $separator -ForegroundColor Red
        $blockedMsg = 'Commit blocked!'
        Write-Host $blockedMsg -ForegroundColor Red
        Write-Host $separator -ForegroundColor Red
        Write-Host ""
        $actionTitle = 'Required Actions:'
        Write-Host $actionTitle -ForegroundColor Yellow
        $action1 = '  1. Remove sensitive information from the files above'
        Write-Host $action1 -ForegroundColor White
        $action2 = '  2. Replace with placeholders (e.g., YOUR_API_KEY)'
        Write-Host $action2 -ForegroundColor White
        $action3 = '  3. Use environment variables or config files'
        Write-Host $action3 -ForegroundColor White
        $action4 = '  4. Run check again before committing'
        Write-Host $action4 -ForegroundColor White
        Write-Host ""
        
        exit 1
    } else {
        $successMsg1 = 'Sensitive information not found.'
        Write-Host $successMsg1 -ForegroundColor Green
        Write-Host ""
        $successMsg2 = 'You can commit safely.'
        Write-Host $successMsg2 -ForegroundColor Green
        Write-Host ""
        
        exit 0
    }
} catch {
    # Unexpected error occurred
    Write-Host ""
    $separator = '=' * 70
    Write-Host $separator -ForegroundColor Red
    $errorTitle = 'Unexpected error occurred during script execution!'
    Write-Host $errorTitle -ForegroundColor Red
    Write-Host $separator -ForegroundColor Red
    Write-Host ""
    $errorMsg = 'Error message: ' + $_
    Write-Host $errorMsg -ForegroundColor Yellow
    $lineNum = $_.InvocationInfo.ScriptLineNumber
    $locationMsg = 'Error location: Line ' + $lineNum
    Write-Host $locationMsg -ForegroundColor Yellow
    Write-Host ""
    $skipMsg = 'To skip security check, use --no-verify option.'
    Write-Host $skipMsg -ForegroundColor Yellow
    Write-Host 'However, this is not recommended.' -ForegroundColor Yellow
    Write-Host ""
    
    # Block commit on error (security-safe default)
    exit 1
}
