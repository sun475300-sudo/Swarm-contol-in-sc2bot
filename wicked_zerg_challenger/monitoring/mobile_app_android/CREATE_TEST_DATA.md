# 테스트 데이터 파일 생성 가이드

**작성일**: 2026-01-15

---

## 🎯 목표

실제 게임을 실행하지 않고도 테스트 데이터를 생성하여 API가 정상적으로 작동하는지 확인합니다.

---

## ✅ 생성된 파일

### 1. 훈련 통계 파일

**위치**: `data/training_stats.json`

**내용**:
- 승/패 통계 (45승, 44패)
- 승률: 50.56%
- 에피소드 진행률: 42.8%
- 평균 보상, 손실 등

---

### 2. 게임 상태 파일

**위치**: `stats/instance_0/status.json`

**내용**:
- 현재 게임 상태
- 미네랄/가스 수량
- 공급량
- 유닛 수
- 전략 모드 등

---

## 🔍 확인 방법

### 1. 파일 확인

```powershell
# 훈련 통계 확인
Get-Content data\training_stats.json | ConvertFrom-Json

# 게임 상태 확인
Get-Content stats\instance_0\status.json | ConvertFrom-Json
```

---

### 2. API 응답 확인

**브라우저에서**:
- http://localhost:8000/api/game-state
- http://localhost:8000/api/combat-stats
- http://localhost:8000/api/learning-progress

**PowerShell에서**:
```powershell
# 게임 상태 확인
Invoke-WebRequest -Uri "http://localhost:8000/api/game-state" | ConvertFrom-Json

# 전투 통계 확인
Invoke-WebRequest -Uri "http://localhost:8000/api/combat-stats" | ConvertFrom-Json
```

**예상 결과**:
- ✅ `win_rate`가 50.56%로 표시됨 (0.0이 아님)
- ✅ `is_running: true` (게임 실행 중)
- ✅ 실제 미네랄/가스 수량 표시

---

## 📊 현재 상태

| 항목 | 상태 | 설명 |
|-----|------|------|
| 훈련 통계 파일 | ✅ 생성됨 | `data/training_stats.json` |
| 게임 상태 파일 | ✅ 생성됨 | `stats/instance_0/status.json` |
| win_rate | ✅ 50.56% | 실제 값으로 표시됨 |
| API 응답 | ✅ 정상 | 실제 데이터 반환 |

---

## 🚀 실제 게임 실행 시

실제 게임을 실행하면:

1. **기존 테스트 데이터 덮어쓰기**:
   - 게임이 실행되면 실제 데이터로 자동 업데이트됨
   - `stats/instance_0/status.json`이 실시간으로 업데이트됨

2. **훈련 통계 업데이트**:
   - 게임이 끝나면 `data/training_stats.json`이 자동 업데이트됨
   - 승/패 통계가 실제 값으로 변경됨

---

## ⚠️ 주의사항

### 테스트 데이터 vs 실제 데이터

- **테스트 데이터**: 현재 생성된 파일은 샘플 데이터입니다
- **실제 데이터**: 게임을 실행하면 자동으로 실제 값으로 업데이트됩니다

### 파일 위치

서버는 다음 경로에서 파일을 찾습니다:

1. **훈련 통계**:
   - `D:\Swarm-contol-in-sc2bot\wicked_zerg_challenger\data\training_stats.json`
   - 또는 `D:\Swarm-contol-in-sc2bot\wicked_zerg_challenger\training_stats.json`

2. **게임 상태**:
   - `D:\Swarm-contol-in-sc2bot\wicked_zerg_challenger\stats\instance_0\status.json`
   - 또는 `D:\Swarm-contol-in-sc2bot\wicked_zerg_challenger\stats\instance_*_status.json`

---

## 🎯 다음 단계

### 테스트 데이터로 확인 후:

1. **API 테스트**: 브라우저에서 http://localhost:8000/docs 열어서 테스트
2. **Android 앱 테스트**: 앱에서 실제 데이터가 표시되는지 확인
3. **실제 게임 실행**: `python run.py`로 게임 실행하여 실제 데이터 확인

---

**마지막 업데이트**: 2026-01-15  
**상태**: 테스트 데이터 파일 생성 완료
