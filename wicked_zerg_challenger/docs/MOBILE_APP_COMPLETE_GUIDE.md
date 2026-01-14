# ? 모바일 애플리케이션 제작 완전 가이드

**작성일**: 2026-01-14  
**목표**: SC2 Zerg Bot 모니터링을 위한 모바일 앱 제작

---

## ? 3가지 방법 비교

| 방법 | 난이도 | 시간 | 장점 | 단점 |
|------|-------|------|------|------|
| **1. PWA** | ? 쉬움 | 1-2시간 | 설치 불필요, 크로스 플랫폼 | 일부 기능 제한 |
| **2. Android Native** | ?? 보통 | 3-5일 | 완전한 기능, 네이티브 성능 | Android만 지원 |
| **3. React Native** | ??? 어려움 | 1-2주 | iOS/Android 동시 지원 | 초기 설정 복잡 |

---

## ? 방법 1: PWA (Progressive Web App) - 추천!

**가장 빠르고 쉬운 방법입니다.**

### 단계별 가이드

#### 1단계: PWA 설정 스크립트 실행

```powershell
# 프로젝트 루트에서 실행
cd D:\Swarm-contol-in-sc2bot\wicked_zerg_challenger
bat\setup_mobile_gcs.bat
```

또는 수동으로:

```powershell
# PWA 아이콘 생성
python tools\generate_pwa_icons.py
```

**필요한 패키지**:
```bash
pip install Pillow
```

#### 2단계: 대시보드 서버 실행

```powershell
cd monitoring
python dashboard.py
```

**출력 확인**:
```
Server ready: http://localhost:8000
Serving from: monitoring/mobile_app/public
WebSocket: ws://localhost:8000/ws/game-status
```

#### 3단계: 모바일에서 접속

##### 옵션 A: 같은 Wi-Fi 네트워크 (권장)

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
   - **Android**: 브라우저 메뉴 > "홈 화면에 추가"
   - **iOS**: 공유 버튼 > "홈 화면에 추가"

##### 옵션 B: ngrok으로 외부 접속 (LTE/5G)

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

4. **홈 화면에 추가** (앱처럼 사용)

---

## ? 방법 2: Android Native App (Kotlin)

**완전한 네이티브 앱을 원하는 경우**

### 사전 준비

1. **Android Studio 설치**
   - https://developer.android.com/studio
   - Android Studio 2023.1 이상 권장

2. **JDK 17 이상 설치**
   - Android Studio 설치 시 자동 포함

### 단계별 가이드

#### 1단계: 프로젝트 열기

1. **Android Studio 실행**
2. **"Open" 클릭**
3. **프로젝트 경로 선택**:
   ```
   D:\Swarm-contol-in-sc2bot\wicked_zerg_challenger\monitoring\mobile_app_android
   ```
4. **Gradle 동기화 대기** (처음에는 시간이 걸림)

#### 2단계: PC IP 주소 설정

1. **파일 열기**:
   ```
   app/src/main/java/com/wickedzerg/mobilegcs/api/ApiClient.kt
   ```

2. **IP 주소 변경**:
   ```kotlin
   // TODO: Change this to your PC's IP address
   private val BASE_URL = "http://192.168.0.100:8000"  // 여기를 변경
   ```

3. **PC의 IP 주소 확인**:
   ```powershell
   ipconfig
   # IPv4 주소 확인 116.120.36.38
   ```

#### 3단계: 빌드 및 실행

##### 방법 A: Android Studio에서 실행

1. **USB로 Android 기기 연결**
2. **기기에서 "USB 디버깅" 활성화**
3. **Android Studio에서 "Run" 버튼 클릭** (▶?)
4. **기기 선택 후 설치**

##### 방법 B: APK 빌드 후 수동 설치

**Windows (PowerShell)**:
```powershell
cd monitoring\mobile_app_android

# Debug APK 빌드
.\gradlew.bat assembleDebug
```

**Linux/Mac**:
```bash
cd monitoring/mobile_app_android

# Debug APK 빌드
./gradlew assembleDebug

# 실행 권한 부여 (처음 한 번만)
chmod +x gradlew
```

**생성된 APK 위치**:
```
app/build/outputs/apk/debug/app-debug.apk
```

**APK 설치 방법**:
1. USB로 기기에 복사
2. 또는 이메일/클라우드로 전송
3. 기기에서 APK 파일 열기
4. "알 수 없는 소스" 허용 (필요한 경우)
5. 설치 진행

#### 4단계: 방화벽 설정 (중요!)

Windows 방화벽에서 포트 8000을 열어야 합니다:

1. **Windows 설정** > **네트워크 및 인터넷** > **방화벽**
2. **고급 설정** > **인바운드 규칙** > **새 규칙**
3. **포트** > **TCP** > **8000** > **허용**

---

## ? 필수 설정 체크리스트

### PWA 방법

- [ ] `bat\setup_mobile_gcs.bat` 실행 완료
- [ ] `python monitoring\dashboard.py` 실행 중
- [ ] PC와 모바일이 같은 Wi-Fi에 연결됨
- [ ] PC의 IP 주소 확인 완료
- [ ] 모바일 브라우저에서 접속 성공
- [ ] 홈 화면에 추가 완료

### Android Native 방법

- [ ] Android Studio 설치 완료
- [ ] 프로젝트 열기 성공
- [ ] Gradle 동기화 완료
- [ ] `ApiClient.kt`에서 IP 주소 변경 완료
- [ ] 방화벽 포트 8000 열림
- [ ] `python monitoring\dashboard.py` 실행 중
- [ ] APK 빌드 성공 또는 기기에서 실행 성공

---

## ? 문제 해결

### PWA 문제

#### 아이콘이 표시되지 않음

```powershell
# 아이콘 파일 확인
dir monitoring\static\icon-*.png

# 아이콘 재생성
python tools\generate_pwa_icons.py
```

#### Service Worker 오류

1. 브라우저 개발자 도구 > Application > Service Workers 확인
2. HTTPS 필요 (일부 브라우저는 `localhost`만 허용)
3. `manifest.json` 파일 확인

#### 모바일에서 접속 불가

1. **방화벽 확인**: Windows 방화벽에서 포트 8000 열림
2. **IP 주소 확인**: `ipconfig`로 정확한 IP 확인
3. **네트워크 확인**: PC와 모바일이 같은 Wi-Fi에 연결됨
4. **서버 실행 확인**: `python monitoring\dashboard.py`가 실행 중인지 확인

### Android Native 문제

#### Gradle 동기화 실패

1. **인터넷 연결 확인**: Gradle이 라이브러리를 다운로드해야 함
2. **방화벽 확인**: 회사 네트워크에서 차단될 수 있음
3. **Gradle 버전 확인**: `gradle/wrapper/gradle-wrapper.properties` 확인

#### 빌드 오류

1. **SDK 버전 확인**: `compileSdk = 34` 확인
2. **JDK 버전 확인**: JDK 17 이상 필요
3. **캐시 정리**: `./gradlew clean` 후 재빌드

#### 앱에서 서버 연결 실패

1. **IP 주소 확인**: `ApiClient.kt`에서 `BASE_URL` 확인
2. **방화벽 확인**: PC의 방화벽에서 포트 8000 열림
3. **네트워크 확인**: PC와 모바일이 같은 Wi-Fi에 연결됨
4. **서버 실행 확인**: `python monitoring\dashboard.py`가 실행 중인지 확인

#### HTTP 연결 오류 (Android 9+)

`AndroidManifest.xml`에 다음이 설정되어 있는지 확인:

```xml
<application
    android:usesCleartextTraffic="true"
    ...>
```

---

## ? 앱 기능

### 현재 구현된 기능

- ? 실시간 게임 상태 데이터 (1초마다 업데이트)
- ? 자원 표시 (미네랄, 가스, 인구수)
- ? 게임 정보 표시
- ? 전투 통계
- ? 학습 진행 상황

### 향후 추가 가능한 기능

- [ ] 게임 상태 차트 (그래프)
- [ ] 전투 로그
- [ ] 학습 진행 상황 상세
- [ ] 알림 설정 (게임 종료, 승리 등)
- [ ] 다크/라이트 테마 전환
- [ ] 다중 게임 인스턴스 모니터링

---

## ? UI 특징

### PWA

- SC2 스타일 디자인 (#16213e 배경, #00ff00 텍스트)
- 반응형 레이아웃
- 실시간 업데이트
- 오프라인 지원 (Service Worker)

### Android Native

- Material Design 컴포넌트
- SC2 테마 색상 적용
- 부드러운 애니메이션
- 네이티브 성능

---

## ? 추가 자료

### 프로젝트 문서

- **PWA 빠른 시작**: `docs/MOBILE_GCS_QUICK_START.md`
- **Android 앱 빌드**: `docs/ANDROID_APP_BUILD_GUIDE.md`
- **Android 빠른 시작**: `docs/ANDROID_APP_QUICK_START.md`
- **프로젝트 README**: `monitoring/mobile_app_android/README.md`

### 외부 자료

- **Android 개발자 가이드**: https://developer.android.com
- **Kotlin 문서**: https://kotlinlang.org/docs/home.html
- **PWA 가이드**: https://web.dev/progressive-web-apps/
- **OkHttp 문서**: https://square.github.io/okhttp/

---

## ? 완료!

이제 모바일 앱이 준비되었습니다. 다음 단계:

1. **PWA**: 모바일 브라우저에서 접속하여 홈 화면에 추가
2. **Android**: Android Studio에서 실행하거나 APK 설치

**추천**: 처음에는 **PWA 방법**을 사용하여 빠르게 테스트하고, 더 많은 기능이 필요하면 **Android Native**로 전환하세요!

---

## ? 팁

1. **개발 중**: PWA로 빠르게 프로토타입 테스트
2. **프로덕션**: Android Native로 완전한 기능 구현
3. **크로스 플랫폼**: React Native 고려 (iOS도 필요할 경우)

**질문이나 문제가 있으면 이슈를 등록하거나 문서를 참고하세요!**
