# Android Mobile GCS App

**작성 일시**: 2026-01-14  
**상태**: ? **Android 앱 프로젝트 생성**

---

## ? Android 앱 프로젝트 구조

이 폴더는 Android Studio 프로젝트의 루트 디렉토리입니다.

### 프로젝트 구조

```
mobile_app_android/
├── app/
│   ├── src/
│   │   ├── main/
│   │   │   ├── java/com/wickedzerg/mobilegcs/
│   │   │   │   ├── MainActivity.kt
│   │   │   │   ├── api/
│   │   │   │   │   ├── ApiClient.kt
│   │   │   │   │   └── GameStateService.kt
│   │   │   │   ├── models/
│   │   │   │   │   └── GameState.kt
│   │   │   │   └── ui/
│   │   │   │       ├── DashboardFragment.kt
│   │   │   │       └── StatsFragment.kt
│   │   │   ├── res/
│   │   │   │   ├── layout/
│   │   │   │   │   ├── activity_main.xml
│   │   │   │   │   └── fragment_dashboard.xml
│   │   │   │   ├── values/
│   │   │   │   │   ├── strings.xml
│   │   │   │   │   └── colors.xml
│   │   │   │   └── mipmap/
│   │   │   │       └── ic_launcher.png
│   │   │   └── AndroidManifest.xml
│   │   └── build.gradle.kts
│   └── build.gradle.kts
├── build.gradle.kts
├── settings.gradle.kts
└── gradle.properties
```

---

## ? 빠른 시작

### 1. Android Studio에서 프로젝트 열기

1. Android Studio 실행
2. "Open" 선택
3. `mobile_app_android` 폴더 선택
4. Gradle 동기화 대기

### 2. 빌드 및 실행

```bash
# Debug APK 빌드
./gradlew assembleDebug

# 또는 Android Studio에서 "Run" 버튼 클릭
```

### 3. APK 설치

생성된 APK 위치:
```
app/build/outputs/apk/debug/app-debug.apk
```

---

## ? 필수 설정

### 1. 서버 IP 주소 설정

`app/src/main/java/com/wickedzerg/mobilegcs/api/ApiClient.kt`에서 서버 IP를 설정하세요:

```kotlin
private const val BASE_URL = "http://YOUR_PC_IP:8000"
```

### 2. 인터넷 권한

`AndroidManifest.xml`에 인터넷 권한이 포함되어 있습니다:

```xml
<uses-permission android:name="android.permission.INTERNET" />
```

### 3. 네트워크 보안 설정 (HTTPS가 아닌 경우)

Android 9+ (API 28+)에서는 기본적으로 HTTP 연결이 차단됩니다. `AndroidManifest.xml`에 다음을 추가:

```xml
<application
    android:usesCleartextTraffic="true"
    ...>
```

---

## ? 개발 가이드

### API 엔드포인트

앱은 다음 API를 사용합니다:
- `GET /api/game-state` - 현재 게임 상태
- `GET /api/combat-stats` - 전투 통계
- `GET /api/learning-progress` - 학습 진행 상황

### 주요 기능

1. **실시간 모니터링**: 1초마다 게임 상태 업데이트
2. **자원 추적**: 미네랄, 가스, 인구수 표시
3. **유닛 구성**: 저글링, 로치, 히드라리스크 등
4. **승률 통계**: 총 게임 수, 승/패, 승률

---

## ? 의존성

주요 라이브러리:
- `okhttp3` - HTTP 클라이언트
- `gson` - JSON 파싱
- `coroutines` - 비동기 처리
- `lifecycle` - Android Lifecycle 관리

---

## ? 다음 단계

1. Android Studio에서 프로젝트 열기
2. 서버 IP 주소 설정
3. 빌드 및 실행
4. 모바일 기기에 설치

---

**참고**: 상세한 코드는 각 파일을 참조하세요.
