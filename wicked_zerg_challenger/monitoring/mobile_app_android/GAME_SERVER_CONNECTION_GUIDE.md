# 게임과 서버 연결 가이드

**작성일**: 2026-01-15

---

## 🎯 목표

게임(봇)과 모니터링 서버를 연결하여 실시간으로 훈련 상태를 확인합니다.

---

## 📋 사전 준비

### 1. 서버 상태 확인

서버가 포트 8000에서 실행 중인지 확인:

```powershell
# 포트 확인
Get-NetTCPConnection -LocalPort 8000

# 또는 서버 시작
cd d:\Swarm-contol-in-sc2bot\wicked_zerg_challenger\monitoring
.\start_server.ps1
```

**예상 결과**: ✅ 서버가 포트 8000에서 리스닝 중

---

### 2. bot_api_connector.py 확인

`monitoring/bot_api_connector.py` 파일이 존재하는지 확인:

```powershell
cd d:\Swarm-contol-in-sc2bot\wicked_zerg_challenger
Test-Path monitoring\bot_api_connector.py
```

**예상 결과**: ✅ 파일 존재

---

## 🚀 게임 실행 및 연결

### 방법 1: 간단한 게임 실행 (권장)

```powershell
cd d:\Swarm-contol-in-sc2bot\wicked_zerg_challenger
python run.py
```

**특징**:
- SC2 경로 자동 탐지
- 봇 인스턴스 자동 생성
- 서버와 자동 연결 (bot_api_connector 사용)

---

### 방법 2: 통합 학습 실행

```powershell
cd d:\Swarm-contol-in-sc2bot\wicked_zerg_challenger\local_training
python main_integrated.py
```

**특징**:
- 전체 학습 파이프라인 실행
- 실시간 훈련 데이터 생성
- 서버와 자동 연결

---

### 방법 3: 배치 파일 사용

```powershell
cd d:\Swarm-contol-in-sc2bot\wicked_zerg_challenger
.\bat\start_game_training.bat
```

---

## 🔗 연결 확인

### 1. API 엔드포인트 확인

브라우저 또는 curl로 확인:

```powershell
# 게임 상태 확인
Invoke-WebRequest -Uri "http://localhost:8000/api/game-state" | Select-Object -ExpandProperty Content

# 건강 상태 확인
Invoke-WebRequest -Uri "http://localhost:8000/health" | Select-Object -ExpandProperty Content
```

**예상 응답**:
```json
{
  "current_frame": 12345,
  "game_status": "IN_PROGRESS",
  "is_running": true,
  "minerals": 500,
  "vespene": 200,
  ...
}
```

---

### 2. 데이터 파일 확인

게임이 실행되면 자동으로 데이터 파일이 생성됩니다:

```powershell
# 훈련 통계 확인
Get-Content data\training_stats.json

# 게임 상태 확인
Get-Content stats\instance_0\status.json
```

---

### 3. Android 앱에서 확인

1. Android Studio에서 앱 실행
2. Monitor 탭으로 이동
3. 실시간 게임 데이터 확인

**예상 표시**:
- 미네랄/가스 수량
- 공급량 (Supply)
- 유닛 수
- 승률 (win_rate)

---

## 🔍 문제 해결

### 문제 1: 서버 연결 실패

**증상**: `bot_connector`가 `None`이거나 업데이트가 안 됨

**해결**:
1. 서버가 실행 중인지 확인
2. `MONITORING_API_URL` 환경 변수 확인
3. 방화벽 설정 확인

```powershell
# 환경 변수 설정
$env:MONITORING_API_URL = "http://localhost:8000"
```

---

### 문제 2: 데이터 파일이 생성되지 않음

**증상**: `data/training_stats.json` 또는 `stats/instance_*_status.json` 파일이 없음

**해결**:
1. 게임이 실제로 실행 중인지 확인
2. 봇이 정상적으로 작동하는지 확인
3. 디렉토리 권한 확인

```powershell
# 디렉토리 생성
New-Item -ItemType Directory -Path "data" -Force
New-Item -ItemType Directory -Path "stats" -Force
```

---

### 문제 3: API 응답이 기본 캐시 데이터만 반환

**증상**: `win_rate: 0.0`, `is_running: false` 등 기본값만 표시

**원인**: 
- 게임이 실행되지 않았거나
- 데이터 파일이 생성되지 않았음

**해결**:
1. 게임을 실행하여 실제 데이터 생성
2. 데이터 파일이 생성되는지 확인
3. 서버가 파일을 읽을 수 있는지 확인

---

## 📊 연결 상태 확인 체크리스트

- [ ] 서버가 포트 8000에서 실행 중
- [ ] `bot_api_connector.py` 파일 존재
- [ ] 게임이 실행 중
- [ ] API 엔드포인트가 실제 데이터 반환
- [ ] `data/training_stats.json` 파일 생성됨
- [ ] `stats/instance_*_status.json` 파일 생성됨
- [ ] Android 앱에서 실시간 데이터 표시

---

## 🎯 다음 단계

연결이 성공하면:

1. **실시간 모니터링**: Android 앱에서 게임 상태 실시간 확인
2. **훈련 통계**: 승률, 에피소드 진행률 등 확인
3. **게임 제어**: (향후) 앱에서 봇 전략 변경 가능

---

**마지막 업데이트**: 2026-01-15  
**상태**: 연결 가이드 준비 완료
