# Manus.im API 통합 강화 완료

**작성일**: 2026-01-16

## 개요

`dashboard_api.py`에 Manus.im API 통합을 강화하여 다음과 같은 기능을 추가했습니다:

1. **Manus API 프록시 엔드포인트**
2. **실시간 데이터 분석 및 인사이트**
3. **성능 모니터링 및 트렌드 분석**
4. **AI 기반 추천 시스템**

## 새로 추가된 API 엔드포인트

### 1. Manus API 프록시 엔드포인트

#### 게임 데이터
- `GET /api/manus/game-sessions` - 최근 게임 세션 조회
- `GET /api/manus/game-stats` - 게임 통계 조회

#### 학습 데이터
- `GET /api/manus/training-episodes` - 최근 학습 에피소드 조회
- `GET /api/manus/training-stats` - 학습 통계 조회

#### Arena 데이터
- `GET /api/manus/arena-stats` - Arena 통계 조회

#### 봇 설정
- `GET /api/manus/bot-configs` - 모든 봇 설정 조회
- `GET /api/manus/active-config` - 활성 봇 설정 조회

#### 상태 확인
- `GET /api/manus/health` - Manus API 연결 상태 확인

### 2. 분석 및 인사이트 엔드포인트

#### 성능 트렌드
- `GET /api/analytics/performance-trends?days=7` - 성능 트렌드 분석
  - 전체 승률 및 통계
  - 종족별 승률 분석
  - 평균 게임 시간 및 자원 분석

#### 학습 트렌드
- `GET /api/analytics/training-trends?limit=50` - 학습 트렌드 분석
  - 보상 트렌드 (개선/하락)
  - 승률 트렌드 (개선/하락)
  - 손실 트렌드 (감소/증가)

#### AI 인사이트
- `GET /api/analytics/insights` - AI 기반 인사이트 및 추천
  - 성능 분석 및 경고
  - 학습 진행 상황 평가
  - Arena 성적 평가
  - 개선 추천 사항

## 사용 예제

### 1. 게임 통계 조회

```bash
curl http://localhost:8001/api/manus/game-stats
```

**응답 예시:**
```json
{
  "success": true,
  "data": {
    "totalGames": 100,
    "wins": 65,
    "losses": 35,
    "winRate": 0.65
  }
}
```

### 2. 성능 트렌드 분석

```bash
curl http://localhost:8001/api/analytics/performance-trends?days=7
```

**응답 예시:**
```json
{
  "success": true,
  "data": {
    "overall": {
      "winRate": 65.5,
      "wins": 131,
      "losses": 69,
      "total": 200,
      "avgDuration": 582.3,
      "avgMinerals": 1250.5
    },
    "byRace": {
      "Terran": {
        "winRate": 70.0,
        "wins": 56,
        "losses": 24,
        "total": 80
      },
      "Protoss": {
        "winRate": 62.5,
        "wins": 50,
        "losses": 30,
        "total": 80
      }
    },
    "period": "Last 7 days",
    "sampleSize": 200
  }
}
```

### 3. AI 인사이트 및 추천

```bash
curl http://localhost:8001/api/analytics/insights
```

**응답 예시:**
```json
{
  "success": true,
  "data": {
    "insights": [
      {
        "type": "success",
        "category": "performance",
        "message": "승률이 65.5%로 우수합니다!"
      },
      {
        "type": "info",
        "category": "training",
        "message": "학습 진행이 양호합니다."
      }
    ],
    "recommendations": [
      {
        "priority": "medium",
        "category": "strategy",
        "action": "Protoss 상대 승률을 개선하기 위해 전략을 조정해보세요."
      }
    ],
    "generatedAt": "2026-01-16T12:34:56"
  }
}
```

### 4. Manus API 연결 상태 확인

```bash
curl http://localhost:8001/api/manus/health
```

**응답 예시:**
```json
{
  "available": true,
  "status": "healthy",
  "baseUrl": "https://sc2aidash-bncleqgg.manus.space",
  "enabled": true,
  "hasApiKey": true
}
```

## 환경 변수 설정

Manus.im API를 사용하려면 다음 환경 변수를 설정해야 합니다:

```bash
# PowerShell
$env:MANUS_DASHBOARD_URL = "https://sc2aidash-bncleqgg.manus.space"
$env:MANUS_DASHBOARD_API_KEY = "your_api_key_here"  # 선택적
$env:MANUS_DASHBOARD_ENABLED = "1"

# Windows CMD
set MANUS_DASHBOARD_URL=https://sc2aidash-bncleqgg.manus.space
set MANUS_DASHBOARD_API_KEY=your_api_key_here
set MANUS_DASHBOARD_ENABLED=1

# Linux/Mac
export MANUS_DASHBOARD_URL=https://sc2aidash-bncleqgg.manus.space
export MANUS_DASHBOARD_API_KEY=your_api_key_here
export MANUS_DASHBOARD_ENABLED=1
```

## 통합 기능

### 1. 자동 데이터 동기화

`manus_sync.py`를 사용하여 게임 상태를 자동으로 Manus API에 동기화할 수 있습니다:

```python
from monitoring.manus_sync import start_manus_sync

# 5초마다 동기화
start_manus_sync(sync_interval=5)
```

### 2. 실시간 분석

`dashboard_api.py`의 분석 엔드포인트를 사용하여 실시간으로 성능을 모니터링하고 인사이트를 얻을 수 있습니다.

### 3. 대시보드 통합

웹 대시보드나 모바일 앱에서 이 API 엔드포인트를 호출하여 Manus.im 데이터를 표시할 수 있습니다.

## 장점

1. **통합된 API**: 로컬 대시보드와 Manus.im API를 하나의 인터페이스로 통합
2. **실시간 분석**: 게임 및 학습 데이터를 실시간으로 분석
3. **AI 인사이트**: 자동으로 성능을 분석하고 개선 추천 제공
4. **성능 모니터링**: 트렌드를 추적하여 장기적인 성능 변화를 모니터링
5. **종족별 분석**: 상대 종족별 승률을 분석하여 약점 파악

## 다음 단계

1. ? Manus API 프록시 엔드포인트 추가 완료
2. ? 실시간 데이터 분석 기능 추가 완료
3. ? 대시보드 UI에 인사이트 표시 (추후 구현)
4. ? 자동 알림 시스템 (추후 구현)
5. ? 고급 분석 기능 (머신러닝 기반 예측 등)

## 참고 문서

- `monitoring/manus_dashboard_client.py` - Manus API 클라이언트
- `monitoring/manus_sync.py` - Manus 동기화 서비스
- `docs/MANUS_DASHBOARD_API_SPEC.md` - Manus API 스펙
