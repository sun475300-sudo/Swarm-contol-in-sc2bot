# FastAPI 서버 시작 스크립트
# SC2 Bot Monitoring Server

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  SC2 Bot Monitoring Server Starter" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 작업 디렉토리로 이동
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir

Write-Host "Current directory: $scriptDir" -ForegroundColor Yellow
Write-Host ""

# 환경 변수 설정
$env:MONITORING_BASE_DIR = "D:\Swarm-contol-in-sc2bot\wicked_zerg_challenger"
$env:MONITORING_ALLOWED_ORIGINS = "http://localhost:8000,http://127.0.0.1:8000,http://10.0.2.2:8000"

Write-Host "Environment variables set:" -ForegroundColor Green
Write-Host "  MONITORING_BASE_DIR: $env:MONITORING_BASE_DIR"
Write-Host "  MONITORING_ALLOWED_ORIGINS: $env:MONITORING_ALLOWED_ORIGINS"
Write-Host ""

# dashboard_api.py 파일 확인
$apiFile = Join-Path $scriptDir "dashboard_api.py"
if (-not (Test-Path $apiFile)) {
    Write-Host "❌ ERROR: dashboard_api.py not found at $apiFile" -ForegroundColor Red
    Write-Host "Please check the file path." -ForegroundColor Red
    exit 1
}

Write-Host "✅ Found dashboard_api.py" -ForegroundColor Green
Write-Host ""

# 포트 8000 사용 확인
$port8000 = Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue
if ($port8000) {
    Write-Host "⚠️  WARNING: Port 8000 is already in use!" -ForegroundColor Yellow
    Write-Host "   Local Address: $($port8000.LocalAddress):$($port8000.LocalPort)"
    Write-Host "   State: $($port8000.State)"
    Write-Host ""
    $response = Read-Host "Do you want to continue anyway? (y/n)"
    if ($response -ne "y" -and $response -ne "Y") {
        Write-Host "Aborted." -ForegroundColor Yellow
        exit 0
    }
} else {
    Write-Host "✅ Port 8000 is available" -ForegroundColor Green
    Write-Host ""
}

# 서버 시작
Write-Host "Starting FastAPI server..." -ForegroundColor Cyan
Write-Host "  Host: 0.0.0.0 (all interfaces)" -ForegroundColor Yellow
Write-Host "  Port: 8000" -ForegroundColor Yellow
Write-Host ""
Write-Host "Access URLs:" -ForegroundColor Green
Write-Host "  - Local: http://localhost:8000" -ForegroundColor White
Write-Host "  - API: http://localhost:8000/api/game-state" -ForegroundColor White
Write-Host "  - UI: http://localhost:8000/ui" -ForegroundColor White
Write-Host "  - Emulator: http://10.0.2.2:8000" -ForegroundColor White
Write-Host ""
Write-Host "Press Ctrl+C to stop the server" -ForegroundColor Yellow
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# uvicorn 실행
uvicorn dashboard_api:app --host 0.0.0.0 --port 8000
