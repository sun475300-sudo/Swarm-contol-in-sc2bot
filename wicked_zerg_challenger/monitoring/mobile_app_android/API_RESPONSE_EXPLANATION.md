# API 응답 데이터 설명

**작성일**: 2026-01-15

---

## 🔍 현재 API 응답 분석

### 받은 응답:
```json
{
  "current_frame": 0,
  "game_status": "READY",
  "is_running": false,
  "minerals": 50,
  "vespene": 0,
  "supply_used": 12,
  "supply_cap": 15,
  "units": {
    "zerglings": 0,
    "roaches": 0,
    "hydralisks": 0,
    "queens": 2
  },
  "threat_level": "NONE",
  "strategy_mode": "OPENING",
  "map_name": "AbyssalReefLE",
  "last_update": "2026-01-15T09:06:12.552486",
  "win_rate": 0.0,
  "winRate": 0.0
}
```

---

## ❓ 왜 이런 값이 나오는가?

### 1. 기본 캐시 데이터 (Fallback)

**원인**: 서버가 실제 게임 데이터 파일을 찾지 못해 기본 캐시 데이터를 반환하고 있습니다.

**확인 사항**:
- ❌ `data/training_stats.json` 파일이 없음
- ❌ `stats/instance_*_status.json` 파일이 없음
- ✅ 서버는 기본 캐시(`game_state_cache`)를 반환

**결과**: 
- `win_rate: 0.0` - 훈련 통계 파일이 없어 승률을 계산할 수 없음
- `is_running: false` - 실제 게임이 실행 중이 아님
- `current_frame: 0` - 게임 프레임 데이터 없음

---

## 📊 데이터 소스 우선순위

서버는 다음 순서로 데이터를 찾습니다:

### 1순위: `bot_connector` (실시간 연결)
- 봇이 실행 중이고 `bot_api_connector`가 연결되어 있으면 실시간 데이터 사용
- 현재: ❌ 연결되지 않음

### 2순위: JSON 파일 (파일 기반)
- `stats/instance_*_status.json` - 최신 게임 상태
- `data/training_stats.json` - 훈련 통계 (승률 계산용)
- 현재: ❌ 파일이 없음

### 3순위: 기본 캐시 (Fallback)
- `game_state_cache` - 하드코딩된 기본값
- 현재: ✅ 이 데이터를 반환 중

---

## ✅ 실제 데이터를 보려면

### 방법 1: 게임 실행

봇을 실행하면 자동으로 데이터 파일이 생성됩니다:

```powershell
# 봇 실행 (예시)
python local_training/main_integrated.py
```

**생성되는 파일**:
- `stats/instance_0/status.json` - 게임 상태
- `data/training_stats.json` - 훈련 통계 (승률 포함)

---

### 방법 2: 훈련 통계 파일 생성

`data/training_stats.json` 파일을 수동으로 생성:

```json
{
  "wins": 45,
  "losses": 44,
  "total_games": 89,
  "win_rate": 50.56,
  "episode": 428,
  "total_episodes": 1000,
  "average_reward": 187.5
}
```

**위치**: `D:\Swarm-contol-in-sc2bot\wicked_zerg_challenger\data\training_stats.json`

---

### 방법 3: 게임 상태 파일 생성

`stats/instance_0/status.json` 파일 생성:

```json
{
  "game_state": {
    "current_frame": 12345,
    "game_status": "IN_PROGRESS",
    "is_running": true,
    "minerals": 500,
    "vespene": 200,
    "supply_used": 45,
    "supply_cap": 50,
    "units": {
      "zerglings": 20,
      "roaches": 5,
      "hydralisks": 3,
      "queens": 2
    },
    "threat_level": "MEDIUM",
    "strategy_mode": "MID_GAME",
    "map_name": "AbyssalReefLE"
  }
}
```

**위치**: `D:\Swarm-contol-in-sc2bot\wicked_zerg_challenger\stats\instance_0\status.json`

---

## 🔍 현재 상태 확인

### 서버가 찾는 파일 위치:

1. **훈련 통계**:
   - `D:\Swarm-contol-in-sc2bot\wicked_zerg_challenger\data\training_stats.json`
   - 또는 `D:\Swarm-contol-in-sc2bot\wicked_zerg_challenger\training_stats.json`

2. **게임 상태**:
   - `D:\Swarm-contol-in-sc2bot\wicked_zerg_challenger\stats\instance_*_status.json`
   - 또는 `D:\Swarm-contol-in-sc2bot\wicked_zerg_challenger\instance_*_status.json`

### 현재 상태:
- ❌ 훈련 통계 파일 없음 → `win_rate: 0.0`
- ❌ 게임 상태 파일 없음 → 기본 캐시 사용
- ✅ 서버는 정상 작동 중 (기본 데이터 반환)

---

## 📝 정리

### 현재 응답이 나타내는 것:

1. **서버는 정상 작동 중** ✅
   - API 엔드포인트가 정상적으로 응답
   - 기본 캐시 데이터를 반환

2. **실제 게임 데이터는 없음** ⚠️
   - 게임이 실행되지 않았거나
   - 데이터 파일이 생성되지 않았음

3. **`win_rate: 0.0`의 의미**:
   - `data/training_stats.json` 파일이 없어서 승률을 계산할 수 없음
   - 파일이 있으면 실제 승률이 표시됨

---

## 🎯 다음 단계

### 실제 데이터를 보려면:

1. **봇 실행**: 게임을 실행하면 자동으로 데이터 파일 생성
2. **파일 생성**: 위의 예시대로 JSON 파일 수동 생성
3. **서버 재시작**: 파일 생성 후 서버가 자동으로 읽음 (재시작 불필요)

---

**마지막 업데이트**: 2026-01-15  
**상태**: 서버 정상 작동, 데이터 파일 없음 (기본 캐시 반환)
