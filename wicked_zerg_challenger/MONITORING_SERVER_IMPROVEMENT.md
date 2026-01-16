# 모니터링 서버 개선 완료

**작성일**: 2026-01-16

## 개요

로컬 훈련과 아레나 전투 시 적절한 모니터링 서버를 자동으로 시작하고, 앱과 웹에서 두 서버 모두 모니터링이 가능하도록 개선했습니다.

## 주요 개선 사항

### 1. 서버 자동 관리 시스템

#### 생성된 파일
- **`monitoring/server_manager.py`**: 서버 자동 시작/중지 관리자
  - 로컬 훈련 시: 로컬 서버 (포트 8001) 자동 시작
  - 아레나 전투 시: 아레나 서버 (포트 8002) 자동 시작
  - 서버 상태 확인 및 건강 체크 기능

#### 기능
- **자동 서버 선택**: 환경에 따라 적절한 서버 자동 선택
- **백그라운드 실행**: 게임 실행에 방해되지 않도록 백그라운드 실행
- **자동 정리**: 게임 종료 시 자동으로 서버 중지
- **상태 확인**: 서버 건강 상태 자동 확인

### 2. 실행 스크립트 통합

#### `run_with_training.py` (로컬 훈련)
- **로컬 모드**: 로컬 서버 (포트 8001) 자동 시작
- **아레나 모드**: 아레나 서버 (포트 8002) 자동 시작
- **자동 정리**: 훈련 종료 시 서버 자동 중지

#### `run.py` (아레나 배포)
- **아레나 모드**: 아레나 서버 (포트 8002) 자동 시작
- **로컬 테스트**: 로컬 서버 (포트 8001) 자동 시작
- **자동 정리**: 게임 종료 시 서버 자동 중지

### 3. 통합 API 게이트웨이

#### 생성된 파일
- **`monitoring/unified_api_gateway.py`**: 통합 API 게이트웨이 (포트 8000)
  - 로컬 서버와 아레나 서버 모두 프록시
  - 앱과 웹에서 두 서버 모두 접근 가능
  - 자동 서버 선택 기능

#### 기능
- **프록시 엔드포인트**: `/api/local/*`, `/api/arena/*`
- **통합 엔드포인트**: `/api/unified/*` (자동으로 활성 서버 선택)
- **서버 상태 확인**: `/health` 엔드포인트로 두 서버 상태 확인
- **CORS 지원**: 모바일 앱과 웹에서 접근 가능

### 4. 배치 스크립트

#### 생성된 파일
- **`bat/start_unified_gateway.bat`**: 통합 게이트웨이 시작 스크립트

## 서버 구성

### 포트 할당
- **포트 8000**: 통합 API 게이트웨이 (선택적)
- **포트 8001**: 로컬 훈련 모니터링 서버
- **포트 8002**: 아레나 전투 모니터링 서버

### 자동 시작 조건

#### 로컬 서버 (포트 8001)
- `run_with_training.py` 실행 시 (로컬 모드)
- `run.py` 실행 시 (로컬 테스트 모드)
- `--LadderServer` 플래그가 **없을 때**

#### 아레나 서버 (포트 8002)
- `run_with_training.py --LadderServer` 실행 시
- `run.py --LadderServer` 실행 시
- `--LadderServer` 플래그가 **있을 때**

## 사용 방법

### 1. 로컬 훈련 (자동으로 로컬 서버 시작)

```bash
python run_with_training.py
```

**결과**:
- 로컬 서버 자동 시작 (포트 8001)
- 모니터링 URL: `http://localhost:8001`
- 앱/웹 접근: 가능

### 2. 아레나 전투 (자동으로 아레나 서버 시작)

```bash
python run.py --LadderServer
```

**결과**:
- 아레나 서버 자동 시작 (포트 8002)
- 모니터링 URL: `http://localhost:8002`
- 앱/웹 접근: 가능

### 3. 통합 게이트웨이 사용 (선택적)

```bash
bat\start_unified_gateway.bat
```

**결과**:
- 통합 게이트웨이 시작 (포트 8000)
- 로컬 서버 프록시: `http://localhost:8000/api/local/*`
- 아레나 서버 프록시: `http://localhost:8000/api/arena/*`
- 통합 API: `http://localhost:8000/api/unified/*`

## 앱/웹 설정

### 모바일 앱 설정

#### 로컬 훈련 모니터링
```javascript
const LOCAL_API_URL = "http://localhost:8001/api";
// 또는 통합 게이트웨이 사용
const LOCAL_API_URL = "http://localhost:8000/api/local";
```

#### 아레나 전투 모니터링
```javascript
const ARENA_API_URL = "http://localhost:8002/api";
// 또는 통합 게이트웨이 사용
const ARENA_API_URL = "http://localhost:8000/api/arena";
```

#### 통합 모니터링 (자동 선택)
```javascript
const UNIFIED_API_URL = "http://localhost:8000/api/unified";
// 자동으로 활성 서버 선택
```

### 웹 대시보드 설정

#### 직접 서버 접근
- 로컬: `http://localhost:8001/ui`
- 아레나: `http://localhost:8002/ui`

#### 통합 게이트웨이 사용
- 게이트웨이: `http://localhost:8000`

## API 엔드포인트

### 로컬 서버 (포트 8001)
- 게임 상태: `GET /api/game-state`
- 전투 통계: `GET /api/combat-stats`
- 학습 진행: `GET /api/learning-progress`
- 봇 설정: `GET /api/bot-config`
- 파일 브라우저: `GET /api/files/local-training`

### 아레나 서버 (포트 8002)
- 봇 정보: `GET /api/bot-info`
- 경기 기록: `GET /api/matches`
- 통계: `GET /api/stats`
- 랭킹: `GET /api/ranking`
- ELO 이력: `GET /api/elo-history`

### 통합 게이트웨이 (포트 8000)
- 통합 상태: `GET /api/unified/status`
- 통합 게임 상태: `GET /api/unified/game-state`
- 통합 통계: `GET /api/unified/stats`
- 로컬 프록시: `GET /api/local/{endpoint}`
- 아레나 프록시: `GET /api/arena/{endpoint}`

## 자동 정리

모든 실행 스크립트에서 게임 종료 시 자동으로 서버를 중지합니다:
- `KeyboardInterrupt` (Ctrl+C) 처리
- 예외 발생 시 정리
- 정상 종료 시 정리

## 다음 단계

1. ? 서버 자동 관리 시스템 구현 완료
2. ? 실행 스크립트 통합 완료
3. ? 통합 API 게이트웨이 생성 완료
4. ? 모바일 앱 설정 업데이트
5. ? 웹 대시보드 설정 업데이트

## 참고

- 서버 매니저: `monitoring/server_manager.py`
- 통합 게이트웨이: `monitoring/unified_api_gateway.py`
- 로컬 서버: `monitoring/dashboard_api.py`
- 아레나 서버: `monitoring/arena_dashboard_api.py`
