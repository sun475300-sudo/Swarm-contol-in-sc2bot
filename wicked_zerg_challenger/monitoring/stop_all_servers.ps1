# 모든 서버 프로세스 종료 스크립트
# Stop All Server Processes Script

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Stopping All Server Processes" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 포트 8000과 8001을 사용하는 모든 프로세스 찾기
Write-Host "1. Finding processes using ports 8000 and 8001..." -ForegroundColor Yellow

$ports = @(8000, 8001)
$processesToStop = @()

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
                        $processesToStop += @{
                            PID = $processId
                            Name = $proc.ProcessName
                            Command = $cmdLine
                            Port = $port
                        }
                    }
                }
            }
        }
    }
}

# Python 프로세스 중 서버 관련 프로세스 찾기
Write-Host "2. Finding Python server processes..." -ForegroundColor Yellow
$pythonProcs = Get-Process python -ErrorAction SilentlyContinue
foreach ($proc in $pythonProcs) {
    $cmdLine = (Get-WmiObject Win32_Process -Filter "ProcessId = $($proc.Id)").CommandLine
    if ($cmdLine -and ($cmdLine -like "*uvicorn*" -or $cmdLine -like "*dashboard*" -or $cmdLine -like "*start_server*")) {
        $exists = $false
        foreach ($existing in $processesToStop) {
            if ($existing.PID -eq $proc.Id) {
                $exists = $true
                break
            }
        }
        if (-not $exists) {
            $processesToStop += @{
                PID = $proc.Id
                Name = $proc.ProcessName
                Command = $cmdLine
                Port = "Unknown"
            }
        }
    }
}

# 프로세스 종료
if ($processesToStop.Count -eq 0) {
    Write-Host "   ✅ No server processes found" -ForegroundColor Green
} else {
    Write-Host "   Found $($processesToStop.Count) server process(es) to stop:" -ForegroundColor Yellow
    Write-Host ""
    
    foreach ($proc in $processesToStop) {
        Write-Host "   Stopping PID: $($proc.PID) (Port: $($proc.Port))" -ForegroundColor White
        Write-Host "      Command: $($proc.Command.Substring(0, [Math]::Min(100, $proc.Command.Length)))" -ForegroundColor Gray
        try {
            Stop-Process -Id $proc.PID -Force -ErrorAction Stop
            Write-Host "      ✅ Stopped" -ForegroundColor Green
        } catch {
            Write-Host "      ❌ Failed to stop: $($_.Exception.Message)" -ForegroundColor Red
        }
        Write-Host ""
    }
    
    Start-Sleep -Seconds 2
}

# 포트 확인
Write-Host "3. Verifying ports are free..." -ForegroundColor Yellow
$port8000 = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue
$port8001 = Get-NetTCPConnection -LocalPort 8001 -State Listen -ErrorAction SilentlyContinue

if (-not $port8000 -and -not $port8001) {
    Write-Host "   ✅ All ports are now free" -ForegroundColor Green
} else {
    Write-Host "   ⚠️  Some ports are still in use:" -ForegroundColor Yellow
    if ($port8000) {
        Write-Host "      Port 8000: Still in use" -ForegroundColor Yellow
    }
    if ($port8001) {
        Write-Host "      Port 8001: Still in use" -ForegroundColor Yellow
    }
    Write-Host ""
    Write-Host "   You may need to manually stop these processes or restart your computer." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  All Server Processes Stopped" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "To start a single server:" -ForegroundColor Yellow
Write-Host "  cd monitoring" -ForegroundColor White
Write-Host "  .\start_server.ps1" -ForegroundColor White
Write-Host ""
