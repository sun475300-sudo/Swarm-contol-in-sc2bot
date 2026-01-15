# 서버 실행 상태 확인 및 시작 가이드

**작성일**: 2026-01-15  
**상태**: 서버 미실행 확인됨

---

## 🔍 현재 상태 확인 결과

### 포트 8000 확인
- ❌ **포트 8000**: 사용 중이 아님 (서버 미실행)
- ❌ **Python/uvicorn 프로세스**: 실행 중이 아님

---

## 🚀 서버 시작 방법

### 방법 1: FastAPI Single-Port 모드 (권장) ⭐

**위치**: `wicked_zerg_challenger/monitoring/`

**PowerShell 명령어**:
```powershell
cd d:\Swarm-contol-in-sc2bot\wicked_zerg_challenger\monitoring

# 환경 변수 설정 (선택사항)
$env:MONITORING_BASE_DIR="D:\Swarm-contol-in-sc2bot\wicked_zerg_challenger"
$env:MONITORING_ALLOWED_ORIGINS="http://localhost:8000,http://127.0.0.1:8000,http://10.0.2.2:8000"

# FastAPI 서버 시작 (포트 8000)
uvicorn dashboard_api:app --host 0.0.0.0 --port 8000
```

**중요**: `--host 0.0.0.0`을 반드시 사용해야 에뮬레이터에서 접근 가능합니다.

**성공 시 출력**:
```
INFO:     Started server process [PID]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

---

### 방법 2: Legacy Dual-Port 모드

**터미널 1** (대시보드):
```powershell
cd d:\Swarm-contol-in-sc2bot\wicked_zerg_challenger\monitoring
python dashboard.py
```

**터미널 2** (FastAPI API):
```powershell
cd d:\Swarm-contol-in-sc2bot\wicked_zerg_challenger\monitoring
uvicorn dashboard_api:app --host 0.0.0.0 --port 8001
```

---

## ✅ 서버 실행 확인 방법

### 1. 포트 확인

**PowerShell**:
```powershell
# 포트 8000이 사용 중인지 확인
netstat -ano | findstr :8000

# 또는
Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue
```

**성공 시 출력**:
```
Local Address: 0.0.0.0:8000
State: LISTENING
```

---

### 2. 브라우저에서 테스트

**로컬 PC에서**:
- http://localhost:8000/api/game-state 접속
- JSON 응답이 표시되면 정상 작동

**에뮬레이터에서**:
- 에뮬레이터의 브라우저에서 http://10.0.2.2:8000/api/game-state 접속
- JSON 응답이 표시되면 정상 작동

---

### 3. API 엔드포인트 테스트

**PowerShell**:
```powershell
# 게임 상태 확인
Invoke-WebRequest -Uri "http://localhost:8000/api/game-state" | Select-Object -ExpandProperty Content

# 전투 통계 확인
Invoke-WebRequest -Uri "http://localhost:8000/api/combat-stats" | Select-Object -ExpandProperty Content
```

---

## 🔧 문제 해결

### 문제 1: "ModuleNotFoundError: No module named 'uvicorn'"

**해결**:
```powershell
pip install uvicorn fastapi
```

---

### 문제 2: "Address already in use"

**원인**: 포트 8000이 이미 사용 중

**해결**:
```powershell
# 포트를 사용하는 프로세스 찾기
netstat -ano | findstr :8000

# 프로세스 종료 (PID 확인 후)
taskkill /PID <PID> /F

# 또는 다른 포트 사용
uvicorn dashboard_api:app --host 0.0.0.0 --port 8002
```

---

### 문제 3: "Connection refused" (에뮬레이터에서)

**원인**: 서버가 `127.0.0.1`에서만 리스닝

**해결**: `--host 0.0.0.0` 사용 확인
```powershell
# ❌ 잘못된 방법
uvicorn dashboard_api:app --host 127.0.0.1 --port 8000

# ✅ 올바른 방법
uvicorn dashboard_api:app --host 0.0.0.0 --port 8000
```

---

## 📋 빠른 시작 스크립트

### PowerShell 스크립트 생성

**파일**: `start_server.ps1`
```powershell
# 서버 시작 스크립트
$env:MONITORING_BASE_DIR="D:\Swarm-contol-in-sc2bot\wicked_zerg_challenger"
$env:MONITORING_ALLOWED_ORIGINS="http://localhost:8000,http://127.0.0.1:8000,http://10.0.2.2:8000"

cd d:\Swarm-contol-in-sc2bot\wicked_zerg_challenger\monitoring
Write-Host "Starting FastAPI server on port 8000..." -ForegroundColor Green
uvicorn dashboard_api:app --host 0.0.0.0 --port 8000
```

**실행**:
```powershell
.\start_server.ps1
```

---

## 🔍 서버 실행 확인 체크리스트

- [ ] **포트 확인**: `netstat -ano | findstr :8000` → LISTENING 상태
- [ ] **브라우저 테스트**: http://localhost:8000/api/game-state → JSON 응답
- [ ] **에뮬레이터 테스트**: http://10.0.2.2:8000/api/game-state → JSON 응답
- [ ] **방화벽 확인**: 포트 8000 허용 규칙 존재
- [ ] **서버 바인딩**: `0.0.0.0:8000`에서 리스닝 확인

---

## 📊 서버 상태 확인 명령어

### 한 번에 확인하기

```powershell
# 포트 8000 상태 확인
Write-Host "=== Port 8000 Status ===" -ForegroundColor Cyan
$port8000 = Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue
if ($port8000) {
    Write-Host "✅ Port 8000 is LISTENING" -ForegroundColor Green
    Write-Host "   Local Address: $($port8000.LocalAddress):$($port8000.LocalPort)"
    Write-Host "   State: $($port8000.State)"
} else {
    Write-Host "❌ Port 8000 is NOT in use" -ForegroundColor Red
    Write-Host "   Server is not running"
}

# Python 프로세스 확인
Write-Host "`n=== Python Processes ===" -ForegroundColor Cyan
$pythonProcs = Get-Process | Where-Object {$_.ProcessName -like "*python*"}
if ($pythonProcs) {
    Write-Host "✅ Python processes found:" -ForegroundColor Green
    $pythonProcs | Select-Object ProcessName, Id, Path | Format-Table -AutoSize
} else {
    Write-Host "❌ No Python processes running" -ForegroundColor Red
}

# API 테스트
Write-Host "`n=== API Test ===" -ForegroundColor Cyan
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8000/api/game-state" -TimeoutSec 5 -ErrorAction Stop
    Write-Host "✅ API is responding" -ForegroundColor Green
    Write-Host "   Status: $($response.StatusCode)"
} catch {
    Write-Host "❌ API is not responding" -ForegroundColor Red
    Write-Host "   Error: $($_.Exception.Message)"
}
```

---

## 🎯 다음 단계

1. **서버 시작**: 위의 명령어로 서버 시작
2. **포트 확인**: `netstat -ano | findstr :8000`로 확인
3. **브라우저 테스트**: http://localhost:8000/api/game-state 접속
4. **앱 테스트**: Android 앱에서 서버 연결 확인

---

**마지막 업데이트**: 2026-01-15  
**상태**: 서버 미실행 확인됨  
**다음 단계**: 서버 시작 필요
