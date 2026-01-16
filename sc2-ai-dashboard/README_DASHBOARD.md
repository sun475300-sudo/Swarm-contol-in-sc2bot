# StarCraft II AI 모니터링 대시보드

StarCraft II AI 에이전트의 성능을 실시간으로 모니터링하고 관리하는 웹 대시보드입니다.

## 🎮 주요 기능

### 1. 실시간 게임 모니터링
- 현재 게임 상태 실시간 표시
- 유닛 수, 자원(미네랄/가스), 인구수 모니터링
- 게임 단계별 진행 상황 추적
- 5초 자동 새로고침

### 2. 전투 분석 및 통계
- 게임별 승패 기록
- 승률 분석 (원형 차트)
- 유닛 교환 비율 시각화
- 최근 20게임 상세 기록

### 3. 학습 진행 상황 추적
- 강화학습 에피소드 관리
- 보상 함수(Reward) 추이 그래프
- 승률 개선 추이 시각화
- Loss 함수 수렴 모니터링

### 4. AI 봇 제어 패널
- 5가지 전략 설정 (공격형, 방어형, 균형형, 경제형, 러시)
- 빌드오더 커스터마이징 (JSON 형식)
- 활성 설정 전환
- 설정 저장 및 관리

### 5. AI Arena 통합
- monsterbot 경기 기록 조회
- ELO 레이팅 추적
- 상대 봇 정보 및 맵 기록
- 현재 랭킹 표시

### 6. 모바일 반응형 디자인
- 모든 기기에서 최적화된 레이아웃
- 터치 친화적 인터페이스
- 반응형 차트 및 테이블

## 🎨 디자인 특징

- **다크 테마**: 야간 사용에 최적화된 다크 모드
- **청록색 액센트**: 미래지향적이고 기술적인 느낌
- **글로우 효과**: 활성 요소 강조
- **유리형태 카드**: 모던한 glassmorphism 디자인
- **부드러운 애니메이션**: 사용자 경험 향상

## 🛠️ 기술 스택

### 프론트엔드
- **React 19**: 최신 React 프레임워크
- **TypeScript**: 타입 안전성
- **Tailwind CSS 4**: 유틸리티 기반 스타일링
- **shadcn/ui**: 고품질 UI 컴포넌트
- **Recharts**: 데이터 시각화

### 백엔드
- **Express 4**: Node.js 웹 프레임워크
- **tRPC 11**: 타입 안전한 API
- **Drizzle ORM**: 타입 안전한 데이터베이스 접근

### 데이터베이스
- **MySQL/TiDB**: 관계형 데이터베이스
- **Drizzle Kit**: 마이그레이션 관리

## 📁 프로젝트 구조

```
sc2-ai-dashboard/
├── client/                    # 프론트엔드 (React)
│   ├── src/
│   │   ├── pages/            # 페이지 컴포넌트
│   │   │   ├── Home.tsx      # 홈 페이지
│   │   │   ├── Monitor.tsx   # 실시간 모니터링
│   │   │   ├── Battles.tsx   # 전투 분석
│   │   │   ├── Training.tsx  # 학습 진행
│   │   │   ├── BotConfig.tsx # 봇 설정
│   │   │   └── Arena.tsx     # AI Arena
│   │   ├── components/       # 재사용 가능한 컴포넌트
│   │   └── lib/              # 유틸리티 및 설정
│   └── index.html
├── server/                    # 백엔드 (Express + tRPC)
│   ├── routers.ts            # tRPC 라우터
│   ├── db.ts                 # 데이터베이스 쿼리
│   └── _core/                # 핵심 인프라
├── drizzle/                  # 데이터베이스 스키마
│   └── schema.ts             # 테이블 정의
├── scripts/                  # 유틸리티 스크립트
│   ├── seed_test_data.py     # 테스트 데이터 생성 (Python)
│   └── seed-test-data-api.mjs # 테스트 데이터 생성 (Node.js)
├── TESTING.md                # 테스트 가이드
└── package.json              # 의존성 관리
```

## 🚀 빠른 시작

### 설치

```bash
# 저장소 클론
git clone https://github.com/sun475300-sudo/sc2-ai-dashboard.git
cd sc2-ai-dashboard

# 의존성 설치
pnpm install

# 데이터베이스 마이그레이션
pnpm db:push
```

### 개발 서버 실행

```bash
# 개발 서버 시작 (http://localhost:3000)
pnpm dev
```

### 빌드 및 배포

```bash
# 프로덕션 빌드
pnpm build

# 프로덕션 서버 실행
pnpm start
```

## 📊 테스트 데이터 생성

대시보드의 모든 기능을 테스트하기 위해 샘플 데이터를 생성할 수 있습니다.

### Python을 사용한 테스트 데이터 생성

```bash
# 필수 패키지 설치
pip install requests

# 로컬 대시보드에서 테스트
python3 scripts/seed_test_data.py

# 원격 대시보드에서 테스트
python3 scripts/seed_test_data.py --url https://your-domain.manus.space
```

### Node.js를 사용한 테스트 데이터 생성

```bash
# 로컬 대시보드에서 테스트
node scripts/seed-test-data-api.mjs

# 원격 대시보드에서 테스트
node scripts/seed-test-data-api.mjs --url https://your-domain.manus.space
```

### 생성되는 테스트 데이터

- **게임 세션**: 20개 (60% 승률)
- **학습 에피소드**: 50개 (성능 개선 추이)
- **봇 설정**: 5가지 전략
- **Arena 경기**: 30개 (ELO 레이팅)

자세한 내용은 [TESTING.md](./TESTING.md)를 참조하세요.

## 🔌 SC2 봇과 연동

### API 엔드포인트

대시보드는 다음 tRPC API 엔드포인트를 제공합니다:

#### 게임 세션
```
POST /api/trpc/game.createSession
POST /api/trpc/game.getCurrentSession
POST /api/trpc/game.getSessions
POST /api/trpc/game.getStats
```

#### 학습 에피소드
```
POST /api/trpc/training.createEpisode
POST /api/trpc/training.getEpisodes
POST /api/trpc/training.getStats
```

#### 봇 설정
```
POST /api/trpc/bot.createConfig
POST /api/trpc/bot.updateConfig
POST /api/trpc/bot.deleteConfig
POST /api/trpc/bot.getConfigs
POST /api/trpc/bot.getActiveConfig
```

#### AI Arena
```
POST /api/trpc/arena.createMatch
POST /api/trpc/arena.getMatches
POST /api/trpc/arena.getStats
```

### Python 예제

```python
import requests

DASHBOARD_URL = 'https://your-domain.manus.space'

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

## 📖 문서

- [TESTING.md](./TESTING.md) - 테스트 데이터 생성 가이드
- [server/routers.ts](./server/routers.ts) - API 라우터 정의
- [drizzle/schema.ts](./drizzle/schema.ts) - 데이터베이스 스키마

## 🧪 테스트

```bash
# 모든 테스트 실행
pnpm test

# 특정 파일 테스트
pnpm test server/game.test.ts
```

## 📝 라이센스

MIT

## 🤝 기여

이 프로젝트는 [sun475300-sudo/sc2AIagent](https://github.com/sun475300-sudo/sc2AIagent) 프로젝트를 기반으로 합니다.

## 📧 문의

문제가 발생하거나 기능을 제안하고 싶으신 경우 GitHub Issues를 통해 연락주세요.

---

**StarCraft II AI 모니터링 대시보드로 AI 에이전트의 성능을 한눈에 파악하세요!** 🚀
