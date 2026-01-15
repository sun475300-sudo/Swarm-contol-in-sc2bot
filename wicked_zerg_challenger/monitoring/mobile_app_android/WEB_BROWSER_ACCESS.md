# 웹 브라우저 접속 가이드

**작성일**: 2026-01-15

---

## 🌐 로컬 웹 브라우저 접속 링크

서버가 포트 8000에서 실행 중일 때 다음 링크로 접속할 수 있습니다:

---

## 📋 주요 접속 링크

### 1. API 문서 (Swagger UI) - **권장** ⭐

**링크**: http://localhost:8000/docs

**기능**:
- ✅ 대화형 API 문서
- ✅ 모든 엔드포인트 테스트 가능
- ✅ 실시간 데이터 확인
- ✅ 요청/응답 예시 확인

**사용 방법**:
1. 브라우저에서 `http://localhost:8000/docs` 열기
2. 원하는 엔드포인트 클릭 (예: `/api/game-state`)
3. "Try it out" 버튼 클릭
4. "Execute" 버튼 클릭하여 실제 데이터 확인

---

### 2. API 문서 (ReDoc)

**링크**: http://localhost:8000/redoc

**기능**:
- ✅ 읽기 쉬운 API 문서
- ✅ 엔드포인트 상세 설명
- ✅ 데이터 구조 확인

---

### 3. API 루트

**링크**: http://localhost:8000/

**기능**:
- ✅ API 기본 정보
- ✅ 사용 가능한 엔드포인트 목록
- ✅ JSON 형식 응답

**예상 응답**:
```json
{
  "message": "SC2 AI Dashboard API",
  "version": "1.0.0",
  "docs": "/docs",
  "endpoints": {
    "game_state": "/api/game-state",
    "combat_stats": "/api/combat-stats",
    "learning_progress": "/api/learning-progress",
    "bot_config": "/api/bot-config",
    "control": "/api/control",
    "health": "/health"
  }
}
```

---

### 4. 게임 상태 API

**링크**: http://localhost:8000/api/game-state

**기능**:
- ✅ 현재 게임 상태 확인
- ✅ 실시간 데이터 조회
- ✅ JSON 형식 응답

**예상 응답**:
```json
{
  "current_frame": 12345,
  "game_status": "IN_PROGRESS",
  "is_running": true,
  "minerals": 500,
  "vespene": 200,
  "supply_used": 45,
  "supply_cap": 50,
  "units": {
    "zerglings": 10,
    "roaches": 5,
    "hydralisks": 8
  },
  "win_rate": 45.3,
  "winRate": 45.3
}
```

---

### 5. 전투 통계 API

**링크**: http://localhost:8000/api/combat-stats

**기능**:
- ✅ 승/패 통계
- ✅ 승률 확인
- ✅ KDA 비율 등

---

### 6. 학습 진행도 API

**링크**: http://localhost:8000/api/learning-progress

**기능**:
- ✅ 에피소드 진행률
- ✅ 평균 보상
- ✅ 훈련 시간 등

---

### 7. 헬스 체크

**링크**: http://localhost:8000/health

**기능**:
- ✅ 서버 상태 확인
- ✅ 연결 테스트

**예상 응답**:
```json
{
  "status": "healthy",
  "timestamp": "2026-01-15T09:06:12.552486"
}
```

---

## 🚀 빠른 시작

### 방법 1: 브라우저에서 직접 열기

1. **Windows**:
   ```
   시작 메뉴 → 실행 → http://localhost:8000/docs 입력
   ```

2. **PowerShell**:
   ```powershell
   Start-Process "http://localhost:8000/docs"
   ```

3. **명령 프롬프트**:
   ```cmd
   start http://localhost:8000/docs
   ```

---

### 방법 2: 브라우저 주소창에 직접 입력

브라우저 주소창에 다음 중 하나를 입력:

- `http://localhost:8000/docs` (Swagger UI - 권장)
- `http://localhost:8000/redoc` (ReDoc)
- `http://localhost:8000/api/game-state` (게임 상태 직접 확인)

---

## 📊 실시간 모니터링

### Swagger UI에서 실시간 데이터 확인하기

1. **브라우저에서 열기**: http://localhost:8000/docs

2. **게임 상태 확인**:
   - `/api/game-state` 엔드포인트 찾기
   - "Try it out" 클릭
   - "Execute" 클릭
   - 실시간 데이터 확인

3. **주기적으로 새로고침**:
   - 브라우저 새로고침 (F5)
   - 또는 "Execute" 버튼을 다시 클릭

---

## 🔍 API 테스트 예시

### PowerShell에서 테스트

```powershell
# 게임 상태 확인
Invoke-WebRequest -Uri "http://localhost:8000/api/game-state" | ConvertFrom-Json

# 전투 통계 확인
Invoke-WebRequest -Uri "http://localhost:8000/api/combat-stats" | ConvertFrom-Json

# 학습 진행도 확인
Invoke-WebRequest -Uri "http://localhost:8000/api/learning-progress" | ConvertFrom-Json
```

---

### curl로 테스트 (Windows 10+)

```bash
# 게임 상태 확인
curl http://localhost:8000/api/game-state

# 전투 통계 확인
curl http://localhost:8000/api/combat-stats

# 헬스 체크
curl http://localhost:8000/health
```

---

## ⚠️ 문제 해결

### 문제 1: 연결할 수 없음

**증상**: 브라우저에서 "연결할 수 없음" 오류

**해결**:
1. 서버가 실행 중인지 확인:
   ```powershell
   Get-NetTCPConnection -LocalPort 8000
   ```

2. 서버 시작:
   ```powershell
   cd d:\Swarm-contol-in-sc2bot\wicked_zerg_challenger\monitoring
   .\start_server.ps1
   ```

---

### 문제 2: 404 오류

**증상**: 페이지를 찾을 수 없음

**해결**:
- 올바른 URL 확인:
  - ✅ `http://localhost:8000/docs`
  - ❌ `http://localhost:8000/dashboard` (존재하지 않음)

---

### 문제 3: CORS 오류

**증상**: 브라우저 콘솔에 CORS 오류 표시

**해결**:
- 서버의 CORS 설정이 올바른지 확인
- `MONITORING_ALLOWED_ORIGINS` 환경 변수 확인

---

## 📝 전체 엔드포인트 목록

| 엔드포인트 | 설명 | 링크 |
|-----------|------|------|
| `/` | API 루트 정보 | http://localhost:8000/ |
| `/docs` | Swagger UI 문서 | http://localhost:8000/docs |
| `/redoc` | ReDoc 문서 | http://localhost:8000/redoc |
| `/health` | 헬스 체크 | http://localhost:8000/health |
| `/api/game-state` | 게임 상태 | http://localhost:8000/api/game-state |
| `/api/combat-stats` | 전투 통계 | http://localhost:8000/api/combat-stats |
| `/api/learning-progress` | 학습 진행도 | http://localhost:8000/api/learning-progress |
| `/api/bot-config` | 봇 설정 | http://localhost:8000/api/bot-config |

---

## 🎯 추천 사용 방법

### 개발 중:
1. **Swagger UI 사용**: http://localhost:8000/docs
   - 모든 API를 한 곳에서 테스트
   - 실시간 데이터 확인
   - 요청/응답 형식 확인

### 모니터링:
1. **게임 상태 직접 확인**: http://localhost:8000/api/game-state
   - 브라우저에서 JSON 직접 확인
   - 또는 브라우저 확장 프로그램 사용 (JSON Formatter)

### 문서 확인:
1. **ReDoc 사용**: http://localhost:8000/redoc
   - 읽기 쉬운 문서 형식
   - 엔드포인트 상세 설명

---

**마지막 업데이트**: 2026-01-15  
**상태**: 웹 브라우저 접속 가이드 준비 완료
