# 게임 실행 및 훈련 시작 가이드

**작성일**: 2026-01-15

---

## 🎯 목표

게임을 실행하여 서버와 연결하고 훈련이 정상적으로 진행되는지 확인합니다.

---

## 📋 사전 준비 체크리스트

- [ ] 서버가 포트 8000에서 실행 중
- [ ] `monitoring/bot_api_connector.py` 파일 존재
- [ ] StarCraft II가 설치되어 있음
- [ ] Python 환경이 준비되어 있음

---

## 🚀 실행 방법

### 방법 1: 간단한 게임 실행 (권장)

**가장 빠르고 간단한 방법**:

```powershell
cd d:\Swarm-contol-in-sc2bot\wicked_zerg_challenger
python run.py
```

**실행 내용**:
- SC2 경로 자동 탐지
- 로컬 게임 시작 (Terran VeryHard vs Zerg Bot)
- 서버와 자동 연결
- 실시간 데이터 생성

---

### 방법 2: 통합 학습 실행

**전체 학습 파이프라인**:

```powershell
cd d:\Swarm-contol-in-sc2bot\wicked_zerg_challenger\local_training
python main_integrated.py
```

**실행 내용**:
- Reinforcement Learning 실행
- Neural Network 학습
- 실시간 훈련 데이터 생성
- 서버와 자동 연결

---

### 방법 3: 배치 파일 사용

```powershell
cd d:\Swarm-contol-in-sc2bot\wicked_zerg_challenger
.\bat\start_game_training.bat
```

---

## 🔍 연결 확인

### 1. 서버 연결 확인

게임이 실행되면 자동으로 서버에 연결됩니다. 확인 방법:

```powershell
# API 엔드포인트 확인
Invoke-WebRequest -Uri "http://localhost:8000/api/game-state" | ConvertFrom-Json | Format-List
```

**예상 응답**:
```
current_frame  : 12345
game_status    : IN_PROGRESS
is_running     : True
minerals       : 500
vespene        : 200
supply_used    : 45
supply_cap     : 50
...
```

---

### 2. 데이터 파일 확인

게임이 실행되면 자동으로 데이터 파일이 생성됩니다:

```powershell
# 훈련 통계 확인
Get-Content data\training_stats.json | ConvertFrom-Json | Format-List

# 게임 상태 확인
Get-Content stats\instance_0\status.json | ConvertFrom-Json | Format-List
```

---

### 3. Android 앱에서 확인

1. Android Studio에서 앱 실행
2. Monitor 탭으로 이동
3. 실시간 게임 데이터 확인

**확인 사항**:
- ✅ 미네랄/가스 수량이 실시간으로 업데이트됨
- ✅ 공급량 (Supply)이 변경됨
- ✅ 유닛 수가 표시됨
- ✅ 승률 (win_rate)이 계산됨

---

## 📊 훈련 상태 확인

### 실시간 모니터링

**터미널 출력**:
```
[GAME #001] TIME: 05:23 | MIN:  450 | SUPPLY: 45/50 | UNITS:  23 | LAST: Victory
```

**API 응답**:
```json
{
  "current_frame": 12345,
  "game_status": "IN_PROGRESS",
  "is_running": true,
  "minerals": 450,
  "vespene": 200,
  "supply_used": 45,
  "supply_cap": 50,
  "units": {
    "zerglings": 10,
    "roaches": 5,
    "hydralisks": 8
  },
  "win_rate": 45.3,
  "winRate": 45.3
}
```

---

## ⚠️ 문제 해결

### 문제 1: 게임이 시작되지 않음

**증상**: SC2가 실행되지 않거나 오류 발생

**해결**:
1. SC2 설치 경로 확인
2. 환경 변수 `SC2PATH` 설정
3. SC2가 최신 버전인지 확인

```powershell
# SC2 경로 확인
$env:SC2PATH = "C:\Program Files (x86)\StarCraft II"
```

---

### 문제 2: 서버 연결 실패

**증상**: `bot_connector`가 `None`이거나 업데이트가 안 됨

**해결**:
1. 서버가 실행 중인지 확인
2. `monitoring/bot_api_connector.py` 파일 존재 확인
3. Python 경로에 `monitoring` 디렉토리 추가 확인

```powershell
# 서버 시작
cd d:\Swarm-contol-in-sc2bot\wicked_zerg_challenger\monitoring
.\start_server.ps1
```

---

### 문제 3: 데이터 파일이 생성되지 않음

**증상**: `data/training_stats.json` 또는 `stats/instance_*_status.json` 파일이 없음

**해결**:
1. 게임이 실제로 실행 중인지 확인
2. 디렉토리 권한 확인
3. 봇이 정상적으로 작동하는지 확인

```powershell
# 디렉토리 생성
New-Item -ItemType Directory -Path "data" -Force
New-Item -ItemType Directory -Path "stats" -Force
```

---

## 🎯 성공 기준

훈련이 정상적으로 진행되고 있다면:

- ✅ 게임이 실행되고 있음
- ✅ API가 실제 게임 데이터를 반환함
- ✅ `data/training_stats.json` 파일이 생성되고 업데이트됨
- ✅ `stats/instance_*_status.json` 파일이 생성되고 업데이트됨
- ✅ Android 앱에서 실시간 데이터를 볼 수 있음
- ✅ `win_rate`가 0.0이 아닌 실제 값으로 표시됨

---

## 📝 다음 단계

훈련이 정상적으로 진행되면:

1. **장기 훈련**: 여러 게임을 실행하여 승률 개선 확인
2. **데이터 분석**: 훈련 통계를 분석하여 개선점 파악
3. **앱 기능 확장**: 추가 모니터링 기능 구현

---

**마지막 업데이트**: 2026-01-15  
**상태**: 실행 가이드 준비 완료
