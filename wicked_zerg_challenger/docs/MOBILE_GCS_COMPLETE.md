# Mobile GCS 완성 가이드

**작성 일시**: 2026-01-14  
**상태**: ? **PWA 구현 완료**

---

## ? Mobile GCS란?

Mobile GCS (Ground Control Station)는 모바일 기기에서 StarCraft II 봇의 훈련 상태를 실시간으로 모니터링하고 제어할 수 있는 시스템입니다.

**실제 드론 군집 시스템의 관제소와 동일한 개념**으로, 원격에서 시스템을 모니터링하고 제어할 수 있습니다.

---

## ? 현재 구현 상태

### 완료된 기능

1. **PWA (Progressive Web App)** ?
   - `manifest.json` 생성 완료
   - Service Worker 구현 완료
   - 모바일 최적화 HTML/CSS
   - 오프라인 지원

2. **백엔드 API** ?
   - REST API 엔드포인트 (`/api/game-state`, `/api/combat-stats`, etc.)
   - WebSocket 실시간 업데이트
   - FastAPI 백엔드 (선택 사항)

3. **아이콘 생성 도구** ?
   - `tools/generate_pwa_icons.py` - 자동 아이콘 생성

---

## ? 빠른 시작 (3단계)

### 1단계: 아이콘 생성

```powershell
# 방법 A: 자동 스크립트 (권장)
cd D:\Swarm-contol-in-sc2bot\Swarm-contol-in-sc2bot\wicked_zerg_challenger
bat\setup_mobile_gcs.bat

# 방법 B: 수동 실행
python tools\generate_pwa_icons.py
```

**필요한 패키지**: `Pillow`
```bash
pip install Pillow
```

### 2단계: 대시보드 서버 시작

```powershell
cd D:\Swarm-contol-in-sc2bot\Swarm-contol-in-sc2bot\wicked_zerg_challenger\monitoring
python dashboard.py
```

**출력**:
```
Server ready: http://localhost:8000
Serving from: monitoring/mobile_app/public
```

### 3단계: 모바일에서 접속

#### 같은 Wi-Fi 네트워크 사용

1. **PC의 IP 주소 확인**:
   ```powershell
   ipconfig
   # IPv4 주소 확인 (예: 192.168.0.100)
   ```

2. **모바일 브라우저에서 접속**:
   ```
   http://192.168.0.100:8000
   ```

3. **홈 화면에 추가**:
   - **Android**: 브라우저 메뉴 (?) > "홈 화면에 추가"
   - **iOS**: 공유 버튼 (□↑) > "홈 화면에 추가"

#### 외부 접속 (LTE/5G) - ngrok 사용

1. **ngrok 다운로드 및 실행**:
   ```bash
   # https://ngrok.com/download
   ngrok http 8000
   ```

2. **ngrok URL 확인**:
   ```
   Forwarding: https://xxxx-xx-xx-xx-xx.ngrok.io -> http://localhost:8000
   ```

3. **모바일에서 접속**:
   ```
   https://xxxx-xx-xx-xx-xx.ngrok.io
   ```

---

## ? 생성된 파일 목록

### 필수 파일

1. **`monitoring/static/manifest.json`** ?
   - PWA 설정 파일
   - 앱 이름, 아이콘, 테마 색상 등 정의

2. **`monitoring/static/sw.js`** ?
   - Service Worker
   - 오프라인 지원 및 캐싱

3. **`monitoring/static/icon-192.png`** (생성 필요)
   - 192x192 아이콘
   - `generate_pwa_icons.py`로 생성

4. **`monitoring/static/icon-512.png`** (생성 필요)
   - 512x512 아이콘
   - `generate_pwa_icons.py`로 생성

### 도구 파일

1. **`tools/generate_pwa_icons.py`**
   - PWA 아이콘 자동 생성 스크립트

2. **`bat/setup_mobile_gcs.bat`**
   - 원클릭 설정 스크립트

---

## ? 사용 방법

### 로컬 네트워크 접속

1. PC와 모바일이 같은 Wi-Fi에 연결
2. PC의 IP 주소 확인 (`ipconfig`)
3. 모바일 브라우저에서 `http://[PC_IP]:8000` 접속
4. 홈 화면에 추가

### 외부 네트워크 접속 (ngrok)

1. ngrok 설치 및 실행
2. ngrok URL을 모바일에서 접속
3. HTTPS 자동 지원 (PWA 필수 요구사항 충족)

---

## ? 모니터링 기능

### 실시간 데이터

- **게임 상태**: 미네랄, 가스, 인구수
- **유닛 구성**: 저글링, 로치, 히드라리스크 등
- **승률 통계**: 총 게임 수, 승/패, 승률
- **학습 진행**: 에피소드, 평균 보상, 손실

### API 엔드포인트

- `GET /api/game-state` - 현재 게임 상태
- `GET /api/combat-stats` - 전투 통계
- `GET /api/learning-progress` - 학습 진행 상황
- `GET /api/code-health` - 코드 건강도
- `WebSocket /ws/game-status` - 실시간 업데이트

---

## ? 다음 단계

### 기본 사용

1. ? PWA 아이콘 생성 (`bat\setup_mobile_gcs.bat`)
2. ? 대시보드 서버 시작 (`python monitoring\dashboard.py`)
3. ? 모바일에서 접속 및 홈 화면 추가

### 고급 기능 (선택 사항)

1. **알림 기능 추가**: Push API를 사용한 실시간 알림
2. **오프라인 모드 강화**: 더 많은 데이터 캐싱
3. **제어 기능 추가**: 봇 설정 변경, 훈련 중지/재개

---

## ? 문제 해결

### 아이콘이 표시되지 않음

```powershell
# 아이콘 파일 확인
dir monitoring\static\icon-*.png

# 없으면 재생성
python tools\generate_pwa_icons.py
```

### Service Worker 등록 실패

1. 브라우저 개발자 도구 > Application > Service Workers 확인
2. HTTPS 사용 (로컬은 `localhost`만 허용)
3. `manifest.json` 경로 확인 (`/static/manifest.json`)

### 모바일에서 접속 불가

1. **방화벽 확인**: Windows 방화벽에서 포트 8000 허용
2. **IP 주소 확인**: `ipconfig`로 정확한 IP 확인
3. **같은 네트워크**: PC와 모바일이 같은 Wi-Fi에 연결되어 있는지 확인

---

## ? 참고 문서

- **빠른 시작**: `docs/MOBILE_GCS_QUICK_START.md`
- **상세 가이드**: `docs/MOBILE_GCS_BUILD_GUIDE.md`
- **모니터링 시스템**: `monitoring/MONITORING_SYSTEM_REPORT.md`

---

## ? 완료!

이제 Mobile GCS가 준비되었습니다. 모바일에서 훈련을 실시간으로 모니터링할 수 있습니다! ?

**실행 순서**:
1. `bat\setup_mobile_gcs.bat` 실행
2. `python monitoring\dashboard.py` 실행
3. 모바일에서 접속하여 홈 화면에 추가
