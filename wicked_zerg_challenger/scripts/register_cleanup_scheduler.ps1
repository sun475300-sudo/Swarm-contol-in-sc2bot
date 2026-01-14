# ===================================================
# 프로젝트 자동 정리 작업 스케줄러 등록
# ===================================================
# 관리자 권한으로 실행하세요

param(
    [string]$TaskName = "WickedZergProjectCleanup",
    [string]$TaskTime = "03:00",
    [switch]$Remove,
    [switch]$Test
)

$ErrorActionPreference = "Stop"

# 프로젝트 경로
$ProjectRoot = "D:\wicked_zerg_challenger"
$CleanupScript = Join-Path $ProjectRoot "tools\cleanup_and_organize.py"
$ClassifyScript = Join-Path $ProjectRoot "tools\auto_classify_drive.py"
$LogDir = Join-Path $ProjectRoot "logs"

Write-Host "=====================================================" -ForegroundColor Cyan
Write-Host "  프로젝트 자동 정리 작업 스케줄러 등록" -ForegroundColor Cyan
Write-Host "=====================================================" -ForegroundColor Cyan
Write-Host ""

# Python 경로 감지
if (Test-Path (Join-Path $ProjectRoot ".venv\Scripts\python.exe")) {
    $PythonExe = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
    Write-Host "? 가상환경 Python 사용" -ForegroundColor Green
} else {
    $PythonExe = "python"
    Write-Host "? 시스템 Python 사용" -ForegroundColor Green
}

Write-Host "  Python: $PythonExe" -ForegroundColor Gray
Write-Host "  작업명: $TaskName" -ForegroundColor Gray
Write-Host ""

# 기존 작업 제거
if ($Remove) {
    Write-Host "기존 작업 제거 중..." -ForegroundColor Yellow
    try {
        Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
        Write-Host "? 작업 제거 완료" -ForegroundColor Green
    }
    catch {
        Write-Host "??  작업이 존재하지 않습니다" -ForegroundColor Yellow
    }
    exit 0
}

# 테스트 실행
if ($Test) {
    Write-Host "테스트 실행 중 (dry-run)..." -ForegroundColor Yellow
    Write-Host ""
    
    & $PythonExe $CleanupScript --dry-run
    
    Write-Host ""
    Write-Host "? 테스트 완료" -ForegroundColor Green
    exit 0
}

# 스크립트 존재 확인
if (-not (Test-Path $CleanupScript)) {
    Write-Host "? 정리 스크립트를 찾을 수 없습니다: $CleanupScript" -ForegroundColor Red
    exit 1
}

# 작업 액션: 2단계 실행 (프로젝트 정리 + 드라이브 분류)
$Action1 = New-ScheduledTaskAction `
    -Execute $PythonExe `
    -Argument "-u `"$CleanupScript`" --keep-logs 2" `
    -WorkingDirectory $ProjectRoot

# 트리거: 매일 지정 시간
$Trigger = New-ScheduledTaskTrigger -Daily -At $TaskTime

# 설정
$Settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -ExecutionTimeLimit (New-TimeSpan -Hours 2) `
    -MultipleInstances IgnoreNew

# 실행 주체
$Principal = New-ScheduledTaskPrincipal `
    -UserId $env:USERNAME `
    -LogonType S4U `
    -RunLevel Limited

# 작업 등록
Write-Host "작업 등록 중..." -ForegroundColor Cyan
Write-Host "  실행 시간: 매일 $TaskTime" -ForegroundColor Gray
Write-Host "  작업 내용:" -ForegroundColor Gray
Write-Host "    1) 데이터 파일 통합" -ForegroundColor Gray
Write-Host "    2) 로그 정리 (최신 2개 유지)" -ForegroundColor Gray
Write-Host "    3) 중복 폴더 제거" -ForegroundColor Gray
Write-Host "    4) 빈 폴더 제거" -ForegroundColor Gray
Write-Host ""

try {
    # 기존 작업 제거
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
    
    # 새 작업 등록
    Register-ScheduledTask `
        -TaskName $TaskName `
        -Action $Action1 `
        -Trigger $Trigger `
        -Settings $Settings `
        -Principal $Principal `
        -Description "Wicked Zerg 프로젝트 자동 정리 (데이터 통합, 로그 다이어트, 폴더 정리)" | Out-Null
    
    Write-Host "? 작업 등록 완료!" -ForegroundColor Green
    Write-Host ""
    
    # 등록된 작업 정보 표시
    $Task = Get-ScheduledTask -TaskName $TaskName
    $TaskInfo = Get-ScheduledTaskInfo $Task
    
    Write-Host "? 등록된 작업 정보:" -ForegroundColor Cyan
    Write-Host "  상태: $($Task.State)" -ForegroundColor White
    Write-Host "  다음 실행: $($TaskInfo.NextRunTime)" -ForegroundColor White
    Write-Host "  마지막 실행: $($TaskInfo.LastRunTime)" -ForegroundColor White
    Write-Host ""
    
    Write-Host "? 유용한 명령어:" -ForegroundColor Yellow
    Write-Host "  작업 즉시 실행:   Start-ScheduledTask -TaskName '$TaskName'" -ForegroundColor Gray
    Write-Host "  작업 중지:       Stop-ScheduledTask -TaskName '$TaskName'" -ForegroundColor Gray
    Write-Host "  작업 비활성화:    Disable-ScheduledTask -TaskName '$TaskName'" -ForegroundColor Gray
    Write-Host "  작업 제거:       .\register_cleanup_scheduler.ps1 -Remove" -ForegroundColor Gray
    Write-Host "  테스트 실행:     .\register_cleanup_scheduler.ps1 -Test" -ForegroundColor Gray
    Write-Host ""
    
}
catch {
    Write-Host "? 작업 등록 실패: $_" -ForegroundColor Red
    Write-Host ""
    Write-Host "관리자 권한으로 실행해보세요:" -ForegroundColor Yellow
    Write-Host "  Start-Process powershell -Verb RunAs -ArgumentList '-File ""$PSCommandPath""'" -ForegroundColor Gray
    exit 1
}

Write-Host "=====================================================" -ForegroundColor Green
Write-Host "  설정 완료!" -ForegroundColor Green
Write-Host "=====================================================" -ForegroundColor Green
