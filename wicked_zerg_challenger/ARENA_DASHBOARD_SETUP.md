# SC2 AI Arena 대시보드 설정 가이드

**작성일**: 2026-01-16

## 개요

SC2 AI Arena에 배포된 봇을 위한 전용 대시보드가 생성되었습니다. Arena 봇의 랭킹, ELO, 경기 결과 등을 실시간으로 모니터링할 수 있습니다.

## 주요 기능

### 1. 봇 정보 모니터링
- 현재 ELO 레이팅
- 봇 상태 (활성화/비활성화)
- 랭킹 순위

### 2. 경기 결과 분석
- 최근 경기 기록
- 승/패/무 통계
- 승률 추이
- 상대 봇별 성적

### 3. ELO 히스토리
- ELO 레이팅 변화 추이
- 최고 ELO 기록
- 최근 경기별 ELO 변화

### 4. 실시간 업데이트
- WebSocket을 통한 실시간 데이터 스트리밍
- 자동 캐시 업데이트 (5분마다)

## 설치 및 실행

### 1. 대시보드 서버 시작

```bash
cd wicked_zerg_challenger/monitoring
python arena_dashboard_api.py
```

또는 uvicorn으로 실행:

```bash
uvicorn arena_dashboard_api:app --host 0.0.0.0 --port 8002
```

### 2. 환경 변수 설정

#### PowerShell
```powershell
$env:ARENA_API_URL = "https://aiarena.net/api/v2"
$env:ARENA_BOT_NAME = "WickedZerg"
$env:ARENA_BOT_ID = "your-bot-id"  # 선택적
$env:ARENA_DASHBOARD_ENABLED = "1"
```

#### Windows CMD
```cmd
set ARENA_API_URL=https://aiarena.net/api/v2
set ARENA_BOT_NAME=WickedZerg
set ARENA_BOT_ID=your-bot-id
set ARENA_DASHBOARD_ENABLED=1
```

#### Linux/Mac
```bash
export ARENA_API_URL=https://aiarena.net/api/v2
export ARENA_BOT_NAME=WickedZerg
export ARENA_BOT_ID=your-bot-id
export ARENA_DASHBOARD_ENABLED=1
```

## API 엔드포인트

### 1. 봇 정보

```bash
GET http://localhost:8002/api/arena/bot-info
```

**응답 예시:**
```json
{
  "success": true,
  "data": {
    "id": 123,
    "name": "WickedZerg",
    "elo": 1650,
    "status": "Active",
    ...
  }
}
```

### 2. 통계

```bash
GET http://localhost:8002/api/arena/stats
```

**응답 예시:**
```json
{
  "success": true,
  "data": {
    "total_matches": 150,
    "wins": 95,
    "losses": 50,
    "ties": 5,
    "win_rate": 63.33,
    "current_elo": 1650,
    "peak_elo": 1720,
    "elo_change": 120
  }
}
```

### 3. 경기 기록

```bash
GET http://localhost:8002/api/arena/matches?limit=50&offset=0
```

**응답 예시:**
```json
{
  "success": true,
  "data": [...],
  "pagination": {
    "total": 150,
    "limit": 50,
    "offset": 0,
    "has_more": true
  }
}
```

### 4. 랭킹 정보

```bash
GET http://localhost:8002/api/arena/ranking
```

### 5. ELO 히스토리

```bash
GET http://localhost:8002/api/arena/elo-history?limit=50
```

**응답 예시:**
```json
{
  "success": true,
  "data": [
    {
      "elo": 1650,
      "date": "2026-01-16T12:34:56",
      "result": "Win",
      "opponent": "MonsterBot"
    },
    ...
  ]
}
```

### 6. 상대 봇별 성적

```bash
GET http://localhost:8002/api/arena/opponents
```

**응답 예시:**
```json
{
  "success": true,
  "data": [
    {
      "opponent_name": "TerranBot",
      "wins": 12,
      "losses": 3,
      "ties": 0,
      "total": 15,
      "win_rate": 80.0
    },
    ...
  ],
  "total_opponents": 25
}
```

### 7. 최근 성적

```bash
GET http://localhost:8002/api/arena/recent-performance?days=7
```

### 8. 데이터 새로고침

```bash
POST http://localhost:8002/api/arena/refresh
```

## WebSocket 실시간 업데이트

```javascript
const ws = new WebSocket('ws://localhost:8002/ws/arena-updates');

ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    console.log('Arena 업데이트:', data);
    // 데이터 처리...
};
```

## 클라이언트 사용

### Python 클라이언트

```python
from monitoring.arena_dashboard_client import create_client_from_env

# 클라이언트 생성
client = create_client_from_env()

# Arena 데이터 가져오기
bot_info = client.fetch_arena_data()
matches = client.fetch_arena_matches(limit=10)

# 대시보드 동기화
client.sync_to_dashboard()
```

### 수동 동기화

```bash
cd wicked_zerg_challenger/monitoring
python arena_dashboard_client.py
```

## 대시보드 웹 UI (추후 구현)

대시보드 웹 인터페이스를 만들려면:

1. **Frontend 프레임워크**: React, Vue, 또는 순수 HTML/JavaScript
2. **API 연동**: 위의 API 엔드포인트 사용
3. **실시간 업데이트**: WebSocket 연결
4. **차트 라이브러리**: Chart.js, D3.js 등

### 기본 HTML 예제

```html
<!DOCTYPE html>
<html>
<head>
    <title>SC2 AI Arena Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
</head>
<body>
    <h1>SC2 AI Arena Dashboard</h1>
    <div id="stats"></div>
    <div id="matches"></div>
    <div id="elo-chart"></div>
    
    <script>
        const API_URL = 'http://localhost:8002';
        
        async function loadStats() {
            const response = await fetch(`${API_URL}/api/arena/stats`);
            const data = await response.json();
            // UI 업데이트...
        }
        
        // WebSocket 연결
        const ws = new WebSocket(`ws://localhost:8002/ws/arena-updates`);
        ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            // 실시간 업데이트...
        };
        
        // 주기적으로 새로고침
        setInterval(loadStats, 60000); // 1분마다
    </script>
</body>
</html>
```

## 포트 구성

- **Arena 대시보드**: `8002` (기본)
- **일반 대시보드**: `8001` (기존)
- **Manus 대시보드**: `8000` (기존)

## 보안

- CORS는 공개적으로 설정되어 있음 (Arena 데이터는 공개 정보)
- 인증이 필요한 경우 Basic Auth 추가 가능

## 문제 해결

### Arena API 연결 실패

1. **봇 이름 확인**:
   ```bash
   curl https://aiarena.net/api/v2/bots/WickedZerg/
   ```

2. **환경 변수 확인**:
   ```bash
   echo $ARENA_BOT_NAME
   ```

3. **대시보드 새로고침**:
   ```bash
   curl -X POST http://localhost:8002/api/arena/refresh
   ```

### 데이터가 업데이트되지 않는 경우

- 대시보드는 5분마다 자동 업데이트
- 수동 새로고침: `POST /api/arena/refresh`

## 다음 단계

1. ? Arena 대시보드 API 생성 완료
2. ? 웹 UI 프론트엔드 개발 (추후 구현)
3. ? 차트 및 시각화 추가 (추후 구현)
4. ? 알림 시스템 추가 (추후 구현)

## 참고

- Arena API 문서: https://aiarena.net/api/docs/
- 대시보드 API: `monitoring/arena_dashboard_api.py`
- 클라이언트: `monitoring/arena_dashboard_client.py`
