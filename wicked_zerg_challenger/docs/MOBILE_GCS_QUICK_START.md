# Mobile GCS 빠른 시작 가이드

**작성 일시**: 2026-01-14  
**상태**: ? **PWA 완성**

---

## ? 3단계로 Mobile GCS 사용하기

### 1단계: PWA 아이콘 생성

```powershell
# 방법 A: 자동 스크립트 실행
cd D:\Swarm-contol-in-sc2bot\Swarm-contol-in-sc2bot\wicked_zerg_challenger
bat\setup_mobile_gcs.bat

# 방법 B: 수동 실행
python tools\generate_pwa_icons.py
```

**필요한 패키지**: `Pillow` (이미지 생성용)
```bash
pip install Pillow
```

---

### 2단계: 대시보드 서버 시작

```powershell
cd D:\Swarm-contol-in-sc2bot\Swarm-contol-in-sc2bot\wicked_zerg_challenger\monitoring
python dashboard.py
```

**출력 예시**:
```
Server ready: http://localhost:8000
Serving from: monitoring/mobile_app/public
WebSocket: ws://localhost:8000/ws/game-status
```

---

### 3단계: 모바일에서 접속

#### 옵션 A: 같은 Wi-Fi 네트워크 사용

1. **PC의 로컬 IP 확인**:
   ```powershell
   ipconfig
   # IPv4 주소 확인 (예: 192.168.0.100)
   ```

2. **모바일 브라우저에서 접속**:
   ```
   http://192.168.0.100:8000
   ```

3. **홈 화면에 추가**:
   - **Android**: 브라우저 메뉴 > "홈 화면에 추가"
   - **iOS**: 공유 버튼 > "홈 화면에 추가"

#### 옵션 B: ngrok으로 외부 접속 (LTE/5G)

1. **ngrok 설치 및 실행**:
   ```bash
   # ngrok 다운로드: https://ngrok.com/download
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

4. **홈 화면에 추가** (위와 동일)

---

## ? PWA 기능 확인

### 설치 확인

1. 모바일 브라우저에서 대시보드 접속
2. 브라우저가 자동으로 "앱 설치" 프롬프트 표시
3. 또는 수동으로 "홈 화면에 추가" 선택

### 오프라인 지원

- Service Worker가 활성화되면 오프라인에서도 기본 UI 접근 가능
- API 데이터는 네트워크 연결 필요

### 실시간 업데이트

- WebSocket을 통한 실시간 게임 상태 업데이트
- 500ms마다 자동 갱신

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
3. `manifest.json` 경로 확인

### 모바일에서 접속 불가

1. **방화벽 확인**: Windows 방화벽에서 포트 8000 허용
2. **IP 주소 확인**: `ipconfig`로 정확한 IP 확인
3. **같은 네트워크**: PC와 모바일이 같은 Wi-Fi에 연결되어 있는지 확인

---

## ? 현재 구현 상태

### ? 완료된 기능
- PWA Manifest (`manifest.json`)
- Service Worker (`sw.js`)
- 아이콘 생성 스크립트
- 모바일 최적화 HTML/CSS
- 실시간 WebSocket 연결
- REST API 엔드포인트

### ? 사용 가능한 기능
- 실시간 게임 상태 모니터링
- 자원 (미네랄/가스) 추적
- 유닛 구성 확인
- 승률 통계
- 학습 진행 상황

---

## ? 완료!

이제 Mobile GCS가 준비되었습니다. 모바일에서 훈련을 실시간으로 모니터링할 수 있습니다!

**다음 단계**:
1. `bat\setup_mobile_gcs.bat` 실행
2. `python monitoring\dashboard.py` 실행
3. 모바일에서 접속하여 홈 화면에 추가

---

**참고**: 상세한 구축 가이드는 `docs/MOBILE_GCS_BUILD_GUIDE.md`를 참조하세요.
