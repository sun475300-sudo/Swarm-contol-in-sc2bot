# 서버 중복 실행 문제 해결

**작성일**: 2026-01-15

---

## 🔍 문제 분석

서버가 두 개 실행되는 이유:

### 가능한 원인

1. **`dashboard.py`와 `dashboard_api.py` 동시 실행**
   - `dashboard.py`는 포트 8000에서 HTTP 서버 실행
   - `dashboard_api.py`는 포트 8000 또는 8001에서 FastAPI 실행
   - 두 개가 동시에 실행되면 충돌 가능

2. **`start_server.ps1`이 여러 번 실행됨**
   - 스크립트가 여러 번 실행되면 서버가 중복 실행됨

3. **`dashboard.py`의 자동 FastAPI 시작**
   - `START_FASTAPI=1` 환경 변수가 설정되면
   - `dashboard.py`가 포트 8000에서 실행되고
   - 자동으로 포트 8001에서 FastAPI도 시작됨

---

## ✅ 해결 방법

### 방법 1: 기존 서버 종료 후 재시작 (권장)

```powershell
# 1. 모든 서버 프로세스 종료
Get-Process python -ErrorAction SilentlyContinue | Where-Object { 
    (Get-WmiObject Win32_Process -Filter "ProcessId = $($_.Id)").CommandLine -like "*uvicorn*" -or
    (Get-WmiObject Win32_Process -Filter "ProcessId = $($_.Id)").CommandLine -like "*dashboard*"
} | Stop-Process -Force

# 2. 포트 확인
Get-NetTCPConnection -LocalPort 8000,8001 -ErrorAction SilentlyContinue

# 3. 서버 재시작 (하나만)
cd d:\Swarm-contol-in-sc2bot\wicked_zerg_challenger\monitoring
.\start_server.ps1
```

---

### 방법 2: 하나의 서버만 사용

**권장: FastAPI만 사용** (포트 8000)

```powershell
cd d:\Swarm-contol-in-sc2bot\wicked_zerg_challenger\monitoring
uvicorn dashboard_api:app --host 0.0.0.0 --port 8000
```

**또는: dashboard.py만 사용** (포트 8000)

```powershell
cd d:\Swarm-contol-in-sc2bot\wicked_zerg_challenger\monitoring
$env:START_FASTAPI = "0"  # FastAPI 자동 시작 비활성화
python dashboard.py
```

---

### 방법 3: 서버 프로세스 확인 및 정리

```powershell
# 모든 서버 관련 프로세스 확인
Get-Process python -ErrorAction SilentlyContinue | ForEach-Object {
    $cmdLine = (Get-WmiObject Win32_Process -Filter "ProcessId = $($_.Id)").CommandLine
    if ($cmdLine -like "*uvicorn*" -or $cmdLine -like "*dashboard*") {
        Write-Host "PID: $($_.Id) - $($cmdLine.Substring(0, [Math]::Min(100, $cmdLine.Length)))"
    }
}

# 특정 프로세스 종료
Stop-Process -Id <PID> -Force
```

---

## 📊 현재 서버 구조

### Single-Port 모드 (권장)

**하나의 FastAPI 서버만 사용**:
- 포트: 8000
- 서버: `dashboard_api.py`
- 기능: API + UI + WebSocket 모두 제공

**실행 방법**:
```powershell
cd monitoring
uvicorn dashboard_api:app --host 0.0.0.0 --port 8000
```

---

### Dual-Port 모드 (레거시)

**두 개의 서버 사용**:
- 포트 8000: `dashboard.py` (HTTP 서버 + UI)
- 포트 8001: `dashboard_api.py` (FastAPI)

**실행 방법**:
```powershell
# 터미널 1
cd monitoring
python dashboard.py

# 터미널 2
cd monitoring
uvicorn dashboard_api:app --host 0.0.0.0 --port 8001
```

---

## 🔍 서버 중복 확인 방법

### PowerShell로 확인

```powershell
# 포트 8000 사용 프로세스
Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue | 
    Select-Object OwningProcess | 
    ForEach-Object { Get-Process -Id $_.OwningProcess }

# 포트 8001 사용 프로세스
Get-NetTCPConnection -LocalPort 8001 -ErrorAction SilentlyContinue | 
    Select-Object OwningProcess | 
    ForEach-Object { Get-Process -Id $_.OwningProcess }
```

---

## ⚠️ 주의사항

### 서버 중복 실행 시 문제점

1. **포트 충돌**: 같은 포트를 사용하면 오류 발생
2. **리소스 낭비**: 불필요한 프로세스가 메모리 사용
3. **데이터 불일치**: 서로 다른 서버가 다른 데이터를 반환할 수 있음

---

## ✅ 권장 설정

### 하나의 서버만 사용 (Single-Port)

**`start_server.ps1` 사용**:
- 포트 8000에서 FastAPI만 실행
- 모든 기능 제공 (API + UI + WebSocket)
- 중복 없음

**실행**:
```powershell
cd d:\Swarm-contol-in-sc2bot\wicked_zerg_challenger\monitoring
.\start_server.ps1
```

---

## 🎯 정리

**서버가 두 개 실행되는 이유**:
- `dashboard.py`와 `dashboard_api.py`가 동시에 실행됨
- 또는 `start_server.ps1`이 여러 번 실행됨

**해결 방법**:
1. 기존 서버 모두 종료
2. 하나의 서버만 실행 (`start_server.ps1` 권장)

---

**마지막 업데이트**: 2026-01-15  
**상태**: 서버 중복 실행 문제 해결 가이드
