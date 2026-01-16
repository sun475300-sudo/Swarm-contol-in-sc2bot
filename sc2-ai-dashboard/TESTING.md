# SC2 AI 대시보드 테스트 데이터 생성 가이드

대시보드의 모든 기능을 테스트하기 위해 샘플 데이터를 생성하는 방법을 설명합니다.

## 📋 개요

이 가이드에서는 다음 데이터를 생성합니다:

- **게임 세션**: 20개 (승률 60%)
- **학습 에피소드**: 50개 (성능 개선 추이 포함)
- **봇 설정**: 5개 (다양한 전략)
- **AI Arena 경기**: 30개 (ELO 레이팅 포함)

## 🚀 빠른 시작

### 방법 1: Python 스크립트 (권장)

#### 1단계: 필수 패키지 설치

```bash
pip install requests
```

#### 2단계: 로컬 대시보드에서 테스트

```bash
python3 scripts/seed_test_data.py
```

#### 3단계: 원격 대시보드에서 테스트

```bash
python3 scripts/seed_test_data.py --url https://sc2aidash-bncleqgg.manus.space
```

### 방법 2: Node.js 스크립트

#### 1단계: 로컬 대시보드에서 테스트

```bash
node scripts/seed-test-data-api.mjs
```

#### 2단계: 원격 대시보드에서 테스트

```bash
node scripts/seed-test-data-api.mjs --url https://sc2aidash-bncleqgg.manus.space
```

## 📊 생성되는 데이터 상세

### 게임 세션

각 게임 세션은 다음 정보를 포함합니다:

```json
{
  "mapName": "Automaton LE",
  "enemyRace": "Protoss",
  "difficulty": "Hard",
  "gamePhase": "Finished",
  "result": "Victory",
  "finalMinerals": 1250,
  "finalGas": 850,
  "finalSupply": 150,
  "unitsKilled": 120,
  "unitsLost": 35,
  "duration": 1800
}
```

**특징:**
- 60% 승률로 현실적인 게임 결과 생성
- 승리 게임은 더 많은 유닛 처치, 적은 손실
- 게임 시간: 10분 ~ 60분

### 학습 에피소드

각 에피소드는 다음 정보를 포함합니다:

```json
{
  "episodeNumber": 1,
  "totalReward": 245.67,
  "averageReward": 12.28,
  "winRate": 0.65,
  "gamesPlayed": 20,
  "loss": 1.234,
  "notes": "에피소드 1 완료 - 성능 개선됨"
}
```

**특징:**
- 에피소드가 진행될수록 보상 증가 (학습 진행)
- Loss 함수 감소 (모델 수렴)
- 승률 점진적 개선

### 봇 설정

5가지 전략의 봇 설정이 생성됩니다:

1. **공격형 저글링 러시** (Aggressive)
   - 초반 저글링 러시로 상대 압박
   - 빌드오더: Drone → Overlord → Zergling

2. **방어형 뮤탈리스크** (Defensive)
   - 안정적인 경제 운영
   - 빌드오더: Drone → Hatchery → Mutalisk

3. **균형형 하이브** (Balanced)
   - 경제와 군사력 균형
   - 빌드오더: Drone → Hatchery → Hydralisk → Ultralisk

4. **경제형 확장** (Economic)
   - 다중 해처리로 경제 극대화
   - 빌드오더: Drone → Hatchery → Hatchery

5. **초반 러시 (6풀)** (Rush)
   - 극공격형 초반 전략
   - 빌드오더: Drone → Spawning Pool → Zergling

### AI Arena 경기

각 경기는 다음 정보를 포함합니다:

```json
{
  "matchId": "match-1234567890-0",
  "opponentName": "Bot-5678",
  "opponentRace": "Terran",
  "mapName": "Catalyst LE",
  "result": "Win",
  "elo": 1625
}
```

**특징:**
- 55% 승률로 현실적인 경기 결과
- ELO 레이팅 동적 변화 (승리: +10~30, 패배: -30~-10)
- 30경기 후 최종 ELO: ~1600~1700

## 🔍 생성된 데이터 확인

### 1. 홈 페이지 (/)

메인 대시보드에서 생성된 통계를 확인할 수 있습니다:
- 총 게임 수
- 승률
- 학습 메트릭
- Arena ELO

### 2. 실시간 모니터링 (/monitor)

현재 게임 상태를 표시합니다 (테스트 데이터에서는 "게임 시작 대기 중" 표시).

### 3. 전투 분석 (/battles)

생성된 게임 세션의 통계를 확인:
- 승률 분석
- 최근 게임 결과 차트
- 유닛 교환 비율

### 4. 학습 진행 (/training)

생성된 에피소드의 학습 진행을 확인:
- 보상 함수 추이
- 승률 개선 추이
- Loss 함수 변화

### 5. 봇 설정 (/bot-config)

생성된 5가지 봇 설정을 확인:
- 전략별 설정 조회
- 활성 설정 변경 가능

### 6. AI Arena (/arena)

생성된 경기 기록과 랭킹을 확인:
- 총 경기 수와 승률
- 현재 ELO 레이팅
- 최근 경기 기록

## 🔄 데이터 재생성

기존 데이터를 삭제하고 새로 생성하려면:

```bash
# 데이터베이스에서 직접 삭제 (SQL)
DELETE FROM arena_matches;
DELETE FROM training_episodes;
DELETE FROM bot_configs;
DELETE FROM game_sessions;

# 그 후 스크립트 재실행
python3 scripts/seed_test_data.py
```

## 🐛 문제 해결

### 스크립트 실행 오류

**"ModuleNotFoundError: No module named 'requests'"**

```bash
pip install requests
```

**"Connection refused" 또는 "대시보드에 연결할 수 없습니다"**

- 대시보드가 실행 중인지 확인
- URL이 올바른지 확인 (기본값: http://localhost:3000)
- 방화벽 설정 확인

### 데이터가 표시되지 않음

1. 브라우저 캐시 삭제 (Ctrl+Shift+Delete)
2. 페이지 새로고침 (Ctrl+R)
3. 개발자 도구 (F12) → Console 탭에서 에러 확인

## 📝 실제 데이터 연동

테스트 데이터 생성 후, 실제 SC2 봇과 연동하려면:

### Python 클라이언트 라이브러리 사용

```python
from sc2_dashboard import DashboardClient

# 클라이언트 초기화
client = DashboardClient(url='https://sc2aidash-bncleqgg.manus.space')

# 게임 종료 후 데이터 전송
client.send_game_session(
    map_name='Automaton LE',
    enemy_race='Protoss',
    difficulty='Hard',
    result='Victory',
    final_minerals=1250,
    final_gas=850,
    final_supply=150,
    units_killed=120,
    units_lost=35,
    duration=1800
)

# 학습 에피소드 전송
client.send_training_episode(
    episode_number=1,
    total_reward=245.67,
    average_reward=12.28,
    win_rate=0.65,
    games_played=20,
    loss=1.234
)
```

### 직접 API 호출

```python
import requests

DASHBOARD_URL = 'https://sc2aidash-bncleqgg.manus.space'

# 게임 세션 생성
response = requests.post(
    f'{DASHBOARD_URL}/api/trpc/game.createSession',
    json={
        'json': {
            'mapName': 'Automaton LE',
            'enemyRace': 'Protoss',
            'difficulty': 'Hard',
            'result': 'Victory',
            'finalMinerals': 1250,
            'finalGas': 850,
            'finalSupply': 150,
            'unitsKilled': 120,
            'unitsLost': 35,
            'duration': 1800,
        }
    }
)

print(response.json())
```

## 📚 추가 리소스

- [대시보드 README](./README.md)
- [API 문서](./server/routers.ts)
- [데이터베이스 스키마](./drizzle/schema.ts)

## 💡 팁

1. **성능 최적화**: 대량의 데이터를 생성할 때는 스크립트를 여러 번 실행하지 말고, 한 번에 생성하세요.

2. **데이터 검증**: 생성 후 각 페이지에서 데이터가 올바르게 표시되는지 확인하세요.

3. **실시간 업데이트**: 게임 모니터링 페이지는 5초마다 자동 새로고침됩니다.

4. **차트 상호작용**: 모든 차트는 마우스 호버 시 상세 정보를 표시합니다.

---

**문제가 발생하면 개발자 도구 (F12) → Console 탭에서 에러 메시지를 확인하세요.**
