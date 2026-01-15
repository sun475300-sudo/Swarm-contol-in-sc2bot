#!/usr/bin/env pwsh
# -*- coding: utf-8 -*-
<#
.SYNOPSIS
    Git 히스토리에서 민감한 정보 검색
    
.DESCRIPTION
    Git 히스토리 전체를 검색하여 민감한 정보(API 키, 비밀번호 등)가 포함된 파일과 커밋을 찾습니다.
    
.EXAMPLE
    .\scan_git_history_for_sensitive_info.ps1
#>

$ErrorActionPreference = "Stop"

Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host "Git 히스토리에서 민감한 정보 검색" -ForegroundColor Cyan
Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host ""

# Git 저장소 확인
if (-not (Test-Path ".git")) {
    Write-Host "현재 디렉토리가 Git 저장소가 아닙니다." -ForegroundColor Red
    exit 1
}

# 검색할 API 키 패턴 (단순화)
$apiKeyPatterns = @(
    "AIzaSyBDdPWJyXs56AxeCPmqZpySFOVPjjSt_CM",
    "AIzaSy",
)

# 민감한 파일 패턴
$sensitiveFilePatterns = @(
    "API_KEY",
    "API_KEYS",
    "GEMINI_API_KEY",
    "MANUS_API_KEY",
    "NEW_API_KEY_SETUP",
    "REMOVE_API_KEY",
    "SECRET",
    "PASSWORD",
    "TOKEN",
    "local.properties",
    "api_keys",
    "secrets"
)

Write-Host "1. 민감한 파일 패턴 검색 중..." -ForegroundColor Yellow
Write-Host ""

$foundFiles = @()
foreach ($filePattern in $sensitiveFilePatterns) {
    $files = git log --all --full-history --pretty=format: --name-only -- "*$filePattern*" 2>$null | 
             Where-Object { $_ -ne "" } | 
             Sort-Object -Unique
    
    foreach ($file in $files) {
        if ($file -and -not ($foundFiles -contains $file)) {
            $foundFiles += $file
        }
    }
}

if ($foundFiles.Count -gt 0) {
    Write-Host "발견된 민감한 파일 패턴:" -ForegroundColor Red
    foreach ($file in $foundFiles) {
        Write-Host "  - $file" -ForegroundColor Yellow
    }
    Write-Host ""
} else {
    Write-Host "민감한 파일 패턴이 발견되지 않았습니다." -ForegroundColor Green
    Write-Host ""
}

Write-Host "2. API 키 패턴 검색 중..." -ForegroundColor Yellow
Write-Host ""

$foundCommits = @()
foreach ($pattern in $apiKeyPatterns) {
    Write-Host "  검색 중: $pattern" -ForegroundColor Gray
    
    # Git 히스토리에서 패턴 검색
    $commits = git log --all -S "$pattern" --oneline --name-only 2>$null
    
    if ($commits) {
        Write-Host "    발견: $pattern" -ForegroundColor Red
        
        $commitHash = ""
        foreach ($line in $commits) {
            if ($line -match '^[a-f0-9]{7,}') {
                $commitHash = $line
                if (-not ($foundCommits | Where-Object { $_.Commit -eq $commitHash })) {
                    $foundCommits += [PSCustomObject]@{
                        Commit = $commitHash
                        Pattern = $pattern
                    }
                }
            } elseif ($line -match '^\s+[^\s]') {
                $file = $line.Trim()
                if ($file -and -not ($foundFiles -contains $file)) {
                    $foundFiles += $file
                }
            }
        }
    } else {
        Write-Host "    없음" -ForegroundColor Green
    }
}

Write-Host ""
Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host "검색 결과 요약" -ForegroundColor Cyan
Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host ""

if ($foundFiles.Count -eq 0 -and $foundCommits.Count -eq 0) {
    Write-Host "Git 히스토리에서 민감한 정보가 발견되지 않았습니다." -ForegroundColor Green
    Write-Host ""
    exit 0
}

if ($foundFiles.Count -gt 0) {
    Write-Host "발견된 민감한 파일: $($foundFiles.Count)개" -ForegroundColor Red
    Write-Host ""
    foreach ($file in $foundFiles) {
        Write-Host "  - $file" -ForegroundColor Yellow
    }
    Write-Host ""
}

if ($foundCommits.Count -gt 0) {
    Write-Host "민감한 정보가 포함된 커밋: $($foundCommits.Count)개" -ForegroundColor Red
    Write-Host ""
    foreach ($commit in $foundCommits) {
        Write-Host "  커밋: $($commit.Commit)" -ForegroundColor Yellow
        Write-Host "    패턴: $($commit.Pattern)" -ForegroundColor Gray
        Write-Host ""
    }
}

Write-Host ""
Write-Host "======================================================================" -ForegroundColor Yellow
Write-Host "권장 조치" -ForegroundColor Yellow
Write-Host "======================================================================" -ForegroundColor Yellow
Write-Host ""

if ($foundFiles.Count -gt 0 -or $foundCommits.Count -gt 0) {
    Write-Host "민감한 정보가 Git 히스토리에 발견되었습니다." -ForegroundColor Red
    Write-Host ""
    Write-Host "제거 방법:" -ForegroundColor Yellow
    Write-Host "  1. .\tools\remove_sensitive_files_from_git_history.ps1 실행" -ForegroundColor White
    Write-Host "  2. 또는 수동으로 git filter-branch 사용" -ForegroundColor White
    Write-Host ""
    Write-Host "주의: 히스토리 제거 후 force push가 필요합니다!" -ForegroundColor Yellow
    Write-Host ""
} else {
    Write-Host "추가 조치가 필요하지 않습니다." -ForegroundColor Green
    Write-Host ""
}
