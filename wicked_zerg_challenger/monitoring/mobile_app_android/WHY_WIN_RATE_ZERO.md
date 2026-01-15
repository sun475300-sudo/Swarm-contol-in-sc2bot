# win_rate가 0.0인 이유

**작성일**: 2026-01-15

---

## 🔍 문제 분석

### 현재 API 응답:
```json
{
  "win_rate": 0.0,
  "winRate": 0.0,
  "is_running": false,
  "current_frame": 0,
  ...
}
```

---

## ❓ 왜 0.0인가?

### 원인: 데이터 파일이 없음

서버는 `win_rate`를 계산하기 위해 다음 파일을 찾습니다:

**필요한 파일**: `data/training_stats.json`

**파일 위치**:
- `D:\Swarm-contol-in-sc2bot\wicked_zerg_challenger\data\training_stats.json`
- 또는 `D:\Swarm-contol-in-sc2bot\wicked_zerg_challenger\training_stats.json`

**현재 상태**: ❌ 파일이 없음

---

## 📊 서버의 데이터 읽기 로직

### `dashboard_api.py`의 `_get_win_rate()` 함수:

```python
def _get_win_rate(base_dir: Path) -> float:
    """Get win rate from training stats"""
    try:
        stats_file = base_dir / "data" / "training_stats.json"
        if stats_file.exists():
            with open(stats_file, 'r', encoding='utf-8') as f:
                stats = json.load(f)
                wins = stats.get("wins", 0)
                total = stats.get("total_games", 0)
                if total > 0:
                    return (wins / total) * 100.0
    except Exception:
        pass
    return 0.0  # ← 파일이 없으면 0.0 반환
```

**결과**: 파일이 없으면 `0.0`을 반환합니다.

---

## ✅ 해결 방법

### 방법 1: 봇 실행 (자동 생성)

봇을 실행하면 자동으로 데이터 파일이 생성됩니다:

```powershell
cd d:\Swarm-contol-in-sc2bot\wicked_zerg_challenger
python local_training/main_integrated.py
```

**생성되는 파일**:
- `stats/instance_0/status.json` - 게임 상태
- `data/training_stats.json` - 훈련 통계

---

### 방법 2: 테스트 데이터 파일 생성

**파일**: `data/training_stats.json`

```json
{
  "wins": 45,
  "losses": 44,
  "total_games": 89,
  "win_rate": 50.56,
  "episode": 428,
  "total_episodes": 1000,
  "average_reward": 187.5,
  "loss": 0.0342,
  "training_hours": 48.5
}
```

**위치**: `D:\Swarm-contol-in-sc2bot\wicked_zerg_challenger\data\training_stats.json`

**생성 후**: 서버가 자동으로 읽어서 `win_rate`가 계산됩니다.

---

### 방법 3: 게임 상태 파일 생성

**파일**: `stats/instance_0/status.json`

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

## 📋 현재 상태 요약

| 항목 | 상태 | 설명 |
|-----|------|------|
| 서버 실행 | ✅ 정상 | 포트 8000에서 리스닝 중 |
| API 응답 | ✅ 정상 | 기본 캐시 데이터 반환 |
| 훈련 통계 파일 | ❌ 없음 | `data/training_stats.json` 없음 |
| 게임 상태 파일 | ❌ 없음 | `stats/instance_*_status.json` 없음 |
| win_rate | 0.0 | 파일이 없어서 계산 불가 |

---

## 🎯 결론

**현재 응답은 정상입니다.**

- 서버는 정상 작동 중 ✅
- 실제 게임 데이터 파일이 없어서 기본 캐시를 반환 중 ✅
- `win_rate: 0.0`은 데이터 파일이 없어서 나타나는 정상적인 동작 ✅

**실제 데이터를 보려면**:
1. 봇을 실행하여 게임 데이터 파일 생성
2. 또는 위의 예시대로 테스트 데이터 파일 수동 생성

---

**마지막 업데이트**: 2026-01-15
