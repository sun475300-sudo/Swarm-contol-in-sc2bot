# 게임과 서버를 함께 시작하는 스크립트
# Start Game and Server Together Script

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Game + Server Starter" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 작업 디렉토리로 이동
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir

Write-Host "Current directory: $scriptDir" -ForegroundColor Yellow
Write-Host ""

# ============================================================================
# 1. 기존 서버 프로세스 종료
# ============================================================================
Write-Host "1. Stopping existing servers..." -ForegroundColor Yellow

$serverProcesses = @()

# 포트 8000과 8001을 사용하는 프로세스 찾기
$ports = @(8000, 8001)
foreach ($port in $ports) {
    $connections = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue
    if ($connections) {
        $uniquePids = $connections | Select-Object -Unique OwningProcess
        foreach ($conn in $uniquePids) {
            $processId = $conn.OwningProcess
            if ($processId -gt 0) {
                $proc = Get-Process -Id $processId -ErrorAction SilentlyContinue
                if ($proc) {
                    $cmdLine = (Get-WmiObject Win32_Process -Filter "ProcessId = $processId").CommandLine
                    if ($cmdLine -and ($cmdLine -like "*uvicorn*" -or $cmdLine -like "*dashboard*" -or $cmdLine -like "*python*")) {
                        $serverProcesses += $processId
                    }
                }
            }
        }
    }
}

# Python 프로세스 중 서버 관련 프로세스 찾기
$pythonProcs = Get-Process python -ErrorAction SilentlyContinue
foreach ($proc in $pythonProcs) {
    $cmdLine = (Get-WmiObject Win32_Process -Filter "ProcessId = $($proc.Id)").CommandLine
    if ($cmdLine -and ($cmdLine -like "*uvicorn*" -or $cmdLine -like "*dashboard*" -or $cmdLine -like "*start_server*")) {
        if ($serverProcesses -notcontains $proc.Id) {
            $serverProcesses += $proc.Id
        }
    }
}

# 서버 프로세스 종료
if ($serverProcesses.Count -gt 0) {
    Write-Host "   Found $($serverProcesses.Count) server process(es) to stop" -ForegroundColor Yellow
    foreach ($processId in $serverProcesses) {
        try {
            $proc = Get-Process -Id $processId -ErrorAction SilentlyContinue
            if ($proc) {
                Stop-Process -Id $processId -Force -ErrorAction Stop
                Write-Host "   ✅ Stopped PID: $processId" -ForegroundColor Green
            }
        } catch {
            Write-Host "   ⚠️  Could not stop PID: $processId" -ForegroundColor Yellow
        }
    }
    Start-Sleep -Seconds 2
} else {
    Write-Host "   ✅ No existing servers found" -ForegroundColor Green
}

# ============================================================================
# 2. 서버 시작
# ============================================================================
Write-Host ""
Write-Host "2. Starting server..." -ForegroundColor Yellow

# 환경 변수 설정
$env:MONITORING_BASE_DIR = "D:\Swarm-contol-in-sc2bot\wicked_zerg_challenger"
$env:MONITORING_ALLOWED_ORIGINS = "http://localhost:8000,http://127.0.0.1:8000,http://10.0.2.2:8000"

Write-Host "   Environment variables set" -ForegroundColor Green
Write-Host ""

# 서버 시작 (백그라운드)
$monitoringDir = Join-Path $scriptDir "monitoring"
$serverScript = Join-Path $monitoringDir "start_server.ps1"

if (Test-Path $serverScript) {
    Write-Host "   Starting server in background..." -ForegroundColor Yellow
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$monitoringDir'; .\start_server.ps1" -WindowStyle Minimized
    Start-Sleep -Seconds 3
    Write-Host "   ✅ Server started" -ForegroundColor Green
} else {
    Write-Host "   ❌ Server script not found: $serverScript" -ForegroundColor Red
}

# ============================================================================
# 3. 게임 시작
# ============================================================================
Write-Host ""
Write-Host "3. Starting game..." -ForegroundColor Yellow

# 데이터 디렉토리 확인
if (-not (Test-Path "data")) {
    New-Item -ItemType Directory -Path "data" -Force | Out-Null
    Write-Host "   ✅ Created data/ directory" -ForegroundColor Green
}
if (-not (Test-Path "stats")) {
    New-Item -ItemType Directory -Path "stats" -Force | Out-Null
    Write-Host "   ✅ Created stats/ directory" -ForegroundColor Green
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Starting StarCraft II Game" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "The game window will open shortly..." -ForegroundColor Yellow
Write-Host "You can watch the bot play in real-time!" -ForegroundColor Green
Write-Host ""
Write-Host "Monitor the game:" -ForegroundColor Yellow
Write-Host "  - Game Window: StarCraft II will open" -ForegroundColor White
Write-Host "  - Browser: http://localhost:8000/docs" -ForegroundColor White
Write-Host "  - API: http://localhost:8000/api/game-state" -ForegroundColor White
Write-Host ""
Write-Host "Press Ctrl+C to stop the game" -ForegroundColor Yellow
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 게임 시작 (포그라운드)
python run.py
