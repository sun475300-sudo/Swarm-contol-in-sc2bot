# StarCraft II AI 모바일 모니터링 앱

StarCraft II AI 봇을 외부에서 실시간으로 모니터링할 수 있는 반응형 모바일 웹 앱입니다.

## 🎯 주요 기능

### 📊 대시보드
- 게임 승률, 학습 보상, Arena ELO 한눈에 보기
- 최근 활동 요약
- 실시간 통계 업데이트

### 🎮 실시간 모니터링
- 현재 게임 상태 실시간 추적
- 자원(미네랄/가스) 모니터링
- 유닛 교환 비율 시각화
- 게임 진행 상황 바

### 📈 분석
- 게임 결과 분포 (승패 비율)
- 최근 게임 유닛 통계
- 학습 진행 그래프
- 상세 게임 기록 목록

### 🔔 알림
- 게임 종료 알림
- 학습 완료 알림
- Arena 경기 결과 알림
- 읽음/삭제 관리

### ⚙️ 설정
- 대시보드 URL 설정
- 자동 새로고침 간격 조정
- 알림 선호도 설정
- 테마 설정

## 🛠️ 기술 스택

- **React 19** - UI 프레임워크
- **TypeScript** - 타입 안전성
- **Tailwind CSS 4** - 반응형 스타일링
- **Vite** - 빌드 도구
- **Recharts** - 데이터 시각화
- **Axios** - HTTP 클라이언트
- **PWA** - 오프라인 지원

## 📱 반응형 디자인

- **모바일 우선** - 스마트폰 최적화
- **태블릿 지원** - 중간 화면 크기 최적화
- **데스크톱** - 대형 화면 지원
- **터치 친화적** - 모바일 터치 인터페이스

## 🚀 빠른 시작

### 설치

```bash
# 의존성 설치
npm install
# 또는
pnpm install
```

### 개발 서버 실행

```bash
npm run dev
# 또는
pnpm dev
```

브라우저에서 `http://localhost:5173`을 열어주세요.

### 프로덕션 빌드

```bash
npm run build
# 또는
pnpm build
```

빌드된 파일은 `dist/` 디렉토리에 생성됩니다.

## 🔧 설정

### 환경 변수

`.env` 파일을 생성하고 다음을 설정하세요:

```env
VITE_DASHBOARD_URL=https://sc2aidash-bncleqgg.manus.space
```

또는 앱의 설정 페이지에서 대시보드 URL을 변경할 수 있습니다.

## 📡 API 연동

이 앱은 다음 API 엔드포인트를 사용합니다:

### 게임 데이터
- `GET /api/trpc/game.getCurrentSession` - 현재 게임 조회
- `GET /api/trpc/game.getSessions` - 게임 목록 조회
- `GET /api/trpc/game.getStats` - 게임 통계 조회

### 학습 데이터
- `GET /api/trpc/training.getEpisodes` - 에피소드 목록 조회
- `GET /api/trpc/training.getStats` - 학습 통계 조회

### Arena 데이터
- `GET /api/trpc/arena.getMatches` - 경기 목록 조회
- `GET /api/trpc/arena.getStats` - Arena 통계 조회

### 봇 설정
- `GET /api/trpc/bot.getConfigs` - 봇 설정 목록
- `GET /api/trpc/bot.getActiveConfig` - 활성 설정 조회

## 📦 PWA 지원

이 앱은 PWA(Progressive Web App)로 설치 가능합니다:

1. 브라우저 주소창의 설치 버튼 클릭
2. 또는 "설치" 메뉴 선택
3. 홈 화면에 앱 아이콘 추가

**오프라인 지원:**
- 서비스 워커가 기본 페이지 캐싱
- 인터넷 연결 상태 표시

## 🎨 디자인 특징

- **다크 테마** - 야간 사용에 최적화
- **청록색 액센트** - 미래지향적 느낌
- **글로우 효과** - 활성 요소 강조
- **부드러운 애니메이션** - 사용자 경험 향상

## 📊 데이터 새로고침

- **대시보드**: 30초마다 자동 새로고침
- **실시간 모니터링**: 5초마다 자동 새로고침 (토글 가능)
- **분석**: 페이지 로드 시 한 번만 로드
- **알림**: 실시간 업데이트

## 🔐 보안

- HTTPS 통신 (SSL/TLS)
- CORS 정책 준수
- 로컬 스토리지에 민감한 정보 미저장

## 📝 로컬 스토리지

앱은 다음 정보를 로컬 스토리지에 저장합니다:

- `dashboardUrl` - 대시보드 URL
- `autoRefreshInterval` - 새로고침 간격
- `enableNotifications` - 알림 활성화 여부
- `notifyOnGameEnd` - 게임 종료 알림
- `notifyOnTrainingComplete` - 학습 완료 알림
- `notifyOnArenaWin` - Arena 승리 알림
- `darkMode` - 다크 모드 활성화 여부
- `soundEnabled` - 알림 소리 활성화 여부

## 🐛 문제 해결

### "대시보드에 연결할 수 없습니다"
- 대시보드 URL이 올바른지 확인
- 대시보드 서버가 실행 중인지 확인
- 네트워크 연결 상태 확인

### 데이터가 표시되지 않음
- 브라우저 캐시 삭제 (Ctrl+Shift+Delete)
- 페이지 새로고침 (Ctrl+R)
- 개발자 도구 (F12) → Console 탭에서 에러 확인

### 알림이 작동하지 않음
- 설정에서 알림 활성화 확인
- 브라우저 알림 권한 확인

## 📚 참고 자료

- [웹 대시보드](../sc2-ai-dashboard)
- [API 문서](../sc2-ai-dashboard/server/routers.ts)
- [데이터베이스 스키마](../sc2-ai-dashboard/drizzle/schema.ts)

## 📄 라이센스

MIT

## 🤝 기여

이 프로젝트는 [sun475300-sudo/sc2AIagent](https://github.com/sun475300-sudo/sc2AIagent) 프로젝트를 기반으로 합니다.

---

**StarCraft II AI 봇을 어디서나 모니터링하세요!** 📱✨
