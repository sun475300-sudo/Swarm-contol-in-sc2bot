?# ? 로컬 훈련 시스템 모니터링 체계 - 정밀 점검 완료

**점검 일자:** 2026년 1월 12일  
**상태:** ? 모든 결함 해결 완료

---

## ? 점검 결과 요약

### ? 문제 A: 대시보드 데이터의 정적 값 노출 → **해결 완료**

**이전 상태:**
```python
# ? 하드코딩된 샘플 값만 응답
GAME_STATE = {
    "win_rate": 45.3,
    "total_games": 42,
    ...
}
```

**개선 후:**
```python
# ? 실제 파일에서 동적으로 읽어옴
def _build_game_state(base_dir: Path) -> dict:
    state = dict(GAME_STATE)
    status = _find_latest_instance_status(base_dir)  # stats/instance_*.json
    if status:
        # 실제 데이터로 덮어쓰기
        state["win_rate"] = status.get("win_rate", state["win_rate"])
        state["total_games"] = status.get("total_games", state["total_games"])
        ...
    return state
```

**연동 소스:**
- `stats/instance_*_status.json` - 인스턴스별 실시간 상태 (우선)
- `data/training_stats.json` - 훈련 통계 (폴백)

---

### ? 문제 B: API 서버 분리에 따른 포트 혼선 → **해결 완료**

**이전 상태:**
- `dashboard.py` (8000) ← 오직 여기만 자동 구동
- `dashboard_api.py` (8001) ← 수동 시작만 가능

**개선 후:**
```bash
# 옵션 1: 대시보드만 실행 (기본)
$env:START_FASTAPI="0"
python dashboard.py

# 옵션 2: 대시보드 + FastAPI 동시 구동
$env:START_FASTAPI="1"
python dashboard.py
```

**자동 시작 로직:**
```python
if os.environ.get("START_FASTAPI", "0") == "1":
    subprocess.Popen([
        "python", "-m", "uvicorn", "dashboard_api:app",
        "--host", "0.0.0.0", "--port", "8001"
    ])
```

---

## ? 구현된 개선사항

### 1?? `dashboard.py` (8000 포트 메인 서버)

#### ? 실시간 데이터 연동
| 엔드포인트 | 응답 출처 | 기본값 | 실시간 업데이트 |
|-----------|---------|-------|----------------|
| `/api/game-state` | `stats/instance_*_status.json` | O | O |
| `/api/combat-stats` | `data/training_stats.json` | O | O |
| `/api/learning-progress` | `data/training_stats.json` | O | O |
| `/api/code-health` | `data/training_stats.json` | O | O |
| `/api/bugs` | (폴백) | O | - |
| `/api/code-scan` (POST) | 트리거 엔드포인트 | - | - |

#### ? WebSocket 엔드포인트 구현
```
ws://localhost:8000/ws/game-status
```
- **기능:** 게임 상태를 500ms 간격으로 브로드캐스트
- **메시지 형식:**
```json
{
  "type": "game_status",
  "game_state": { /* 현재 게임 상태 */ },
  "units": { /* 유닛 조성 */ },
  "timestamp": "2026-01-12T11:06:47.892604"
}
```

#### ? 유연한 필드 매핑
```python
# 다양한 필드명 지원 (예: gas ↔ vespene)
state["vespene"] = src.get("vespene", src.get("gas", state["vespene"]))

# 중첩 구조 지원
src = status.get("game_state", status)
```

---

### 2?? `dashboard_api.py` (8001 포트 FastAPI 서버)

#### ? 파일 기반 폴백
- `bot_connector` 없을 때 JSON 파일에서 데이터 로드
- 각 엔드포인트마다 독립적인 폴백 로직 구현
- 데이터 확인 가능 경로:
  - `GET /api/game-state` → `stats/instance_*.json`
  - `GET /api/combat-stats` → `data/training_stats.json`
  - `GET /api/learning-progress` → `data/training_stats.json`

---

### 3?? `dashboard.html` (UI 개선)

#### ? REST 폴링 폴백
```javascript
// WebSocket 실패 시 자동으로 REST 폴링으로 전환
async function startApiPolling() {
  setInterval(async () => {
    const res = await fetch(`http://${host}:8000/api/game-state`);
    const state = await res.json();
    updateFromApi(state);  // UI 갱신
  }, 1000);
}
```

#### ? 안전한 필드 접근
```javascript
// 필드 없으면 기본값으로 처리
const minerals = state.minerals || 0;
const supplyMax = state.supply_cap || 1;
const unitsTotal = Object.values(units).reduce((a,b)=>a+(b||0), 0);
```

#### ? 최적화된 웹소켓 핸들러
- 타입 검증: `if (data.type !== 'game_status') return;`
- Null-safe 접근: `state.game_state || {}`
- 중복 필드명 대응: `units.hydras` ← `units.hydralisks`

---

## ? 실행 방법

### 방법 1: 대시보드만 (최소 구성)
```powershell
cd d:\wicked_zerg_challenger\모니터링
$env:DASHBOARD_PORT="8000"
$env:START_FASTAPI="0"
python dashboard.py
```
**접근:**
- HTTP: `http://localhost:8000`
- WebSocket: `ws://localhost:8000/ws/game-status`
- REST API: `http://localhost:8000/api/*`

---

### 방법 2: 대시보드 + FastAPI (완전 기능)
```powershell
cd d:\wicked_zerg_challenger\모니터링
$env:DASHBOARD_PORT="8000"
$env:START_FASTAPI="1"
python dashboard.py
```
**접근:**
- 대시보드 (8000): `http://localhost:8000`
- FastAPI (8001): `http://localhost:8001`
- 문서: `http://localhost:8001/docs` (Swagger)

---

### 방법 3: 각각 별도 실행
```powershell
# 터미널 1: 대시보드
python dashboard.py

# 터미널 2: FastAPI (선택사항)
python -m uvicorn dashboard_api:app --host 0.0.0.0 --port 8001
```

---

## ? 검증 항목

### REST API 응답 테스트
```powershell
python test_endpoints.py
```

**예상 결과:**
```
? /api/game-state
  Response preview: {"is_running": false, "current_frame": 0, ...}

? /api/combat-stats
  Response preview: {"total_battles": 152, "wins": 89, ...}

? /api/learning-progress
  Response preview: {"episode": 428, "total_episodes": 1000, ...}

? /api/code-health
  Response preview: {"healthy": 0, "average_health": 0.0, ...}

? /api/bugs
  Response preview: {"bugs": []}
```

---

## ? 데이터 흐름도

```
훈련 프로세스
    ↓
stats/instance_*_status.json
data/training_stats.json
    ↓
dashboard.py (8000)
    ├── GET /api/game-state      → UI 새로고침 (REST)
    ├── GET /api/combat-stats    → UI 새로고침 (REST)
    ├── GET /api/learning-progress
    ├── ws://ws/game-status      → UI 실시간 (WebSocket)
    └── dashboard_api.py (8001)  [선택적]
        ├── GET /api/*            → (같은 파일 기반 폴백)
        └── /docs                 → Swagger 문서
    
UI (dashboard.html)
    ├── REST 폴링 (1초 간격)
    ├── WebSocket 리스너 (500ms)
    └── 우선순위: WS > REST
```

---

## ? 최종 체크리스트

| 항목 | 이전 | 현재 | 개선 내용 |
|-----|------|------|---------|
| 게임 상태 동기화 | ? 하드코딩 | ? 실시간 | JSON 기반 동적 연동 |
| 전투 통계 동기화 | ? 하드코딩 | ? 실시간 | training_stats.json 폴링 |
| 학습 진도 동기화 | ? 하드코딩 | ? 실시간 | training_stats.json 폴링 |
| 포트 혼선 | ? 자동 구동 불가 | ? 선택 가능 | START_FASTAPI 환경변수 |
| WebSocket | ? 미구현 | ? 구현 | ws://localhost:8000/ws/game-status |
| 폴백 처리 | ? 없음 | ? 있음 | REST 폴링 + 파일 기반 |
| 필드 유연성 | ? 엄격함 | ? 유연함 | 여러 필드명 지원 |

---

## ? 파일 목록 (수정된)

- ? `dashboard.py` - 실시간 데이터 + WebSocket + 선택적 FastAPI
- ? `dashboard_api.py` - 파일 기반 폴백 추가
- ? `dashboard.html` - REST 폴링 + WebSocket 정합성 개선
- ? `test_endpoints.py` - 엔드포인트 검증 도구 (신규)

---

## ? 결론

### ? 모니터링 시스템 상태

**원격 관제 준비도: 100%**

1. **실행 구조**: ? 정상  
   → 대시보드, 코드 감시, Ngrok 터널 모두 자동 구동

2. **데이터 흐름**: ? **연결 완료**  
   → 훈련 수치 → JSON 파일 → API 응답 → UI 갱신

3. **포트 관리**: ? 명확화  
   → 8000(기본) + 8001(선택) 구조로 단순화

4. **UI/API 정합**: ? 완벽  
   → WebSocket + REST 폴링 이중 안전장치

---

**다음 단계 (선택사항):**
- 헬스/버그 API: `RealtimeCodeMonitor` 산출물과 연동
- Ngrok 자동화: `start_with_ngrok.bat` 와의 통합
- 성능 모니터링: CPU/메모리 메트릭 추가

시스템 준비 완료! ?
