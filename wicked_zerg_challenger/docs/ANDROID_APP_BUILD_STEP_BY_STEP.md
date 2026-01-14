# Android 앱 빌드 방법 (단계별 가이드)

**작성 일시**: 2026-01-14  
**상태**: ? **상세 가이드 완료**

---

## ? Android 앱 빌드 방법

### 방법 1: Android Studio 사용 (권장) ?

#### 1단계: Android Studio 설치

1. **Android Studio 다운로드**
   - https://developer.android.com/studio
   - "Download Android Studio" 클릭
   - 설치 파일 실행

2. **설치 과정**
   - 설치 마법사 따라하기
   - Android SDK 자동 다운로드 (시간 소요, 인터넷 필요)
   - 설치 완료 후 Android Studio 실행

---

#### 2단계: 프로젝트 열기

1. **Android Studio 실행**
2. **"Open" 선택** (Welcome 화면에서)
3. **프로젝트 폴더 선택**:
   ```
   D:\Swarm-contol-in-sc2bot\Swarm-contol-in-sc2bot\wicked_zerg_challenger\monitoring\mobile_app_android
   ```
4. **Gradle 동기화 대기**
   - 하단에 "Gradle Sync" 진행 상황 표시
   - 완료까지 몇 분 소요 (처음 한 번만)
   - "Build" 탭에서 진행 상황 확인 가능

---

#### 3단계: 서버 IP 주소 설정

1. **파일 열기**
   - 왼쪽 프로젝트 트리에서:
     ```
     app > src > main > java > com > wickedzerg > mobilegcs > api > ApiClient.kt
     ```
   - 파일을 더블클릭하여 열기

2. **IP 주소 수정**
   - Line 13 근처를 찾습니다:
     ```kotlin
     // TODO: Change this to your PC's IP address
     private val BASE_URL = "http://192.168.0.100:8000"
     ```
   - `192.168.0.100`을 **본인의 PC IP 주소**로 변경

3. **PC의 IP 주소 확인 방법**

   **Windows (PowerShell/CMD)**:
   ```powershell
   ipconfig
   ```
   
   출력 예시:
   ```
   IPv4 주소 . . . . . . . . . : 192.168.0.100
   ```
   
   이 주소를 `BASE_URL`에 입력하세요.

   **예시**:
   ```kotlin
   private val BASE_URL = "http://192.168.0.100:8000"  // 본인 PC IP로 변경
   ```

4. **파일 저장**
   - `Ctrl + S` (Windows) 또는 `Cmd + S` (Mac)

---

#### 4단계: 대시보드 서버 실행

**중요**: 앱이 작동하려면 대시보드 서버가 실행 중이어야 합니다!

1. **새 터미널/명령 프롬프트 열기**
2. **서버 실행**:
   ```powershell
   cd D:\Swarm-contol-in-sc2bot\Swarm-contol-in-sc2bot\wicked_zerg_challenger\monitoring
   python dashboard.py
   ```
3. **서버 시작 확인**:
   ```
   Server ready: http://localhost:8000
   ```
   이 메시지가 보이면 서버가 정상 작동 중입니다.

---

#### 5단계: Android 기기 준비

1. **USB로 Android 기기 연결**
   - USB 케이블로 PC와 기기 연결

2. **USB 디버깅 활성화**
   - 기기에서: **설정 > 휴대전화 정보 > 빌드 번호** 7번 연속 탭
   - **설정 > 개발자 옵션 > USB 디버깅** 활성화
   - PC 연결 시 "USB 디버깅 허용" 팝업에서 **"허용"** 선택

3. **기기 인식 확인**
   - Android Studio 하단 "Logcat" 옆에 기기 이름이 표시되면 성공
   - 또는 상단 툴바에서 기기 선택 드롭다운 확인

---

#### 6단계: 빌드 및 실행

1. **"Run" 버튼 클릭**
   - 상단 툴바의 녹색 재생 버튼 (▶?) 클릭
   - 또는 `Shift + F10` (Windows/Linux) / `Ctrl + R` (Mac)

2. **기기 선택**
   - "Select Deployment Target" 창이 나타나면
   - 연결된 Android 기기 선택
   - "OK" 클릭

3. **빌드 진행**
   - 하단 "Build" 탭에서 빌드 진행 상황 확인
   - 처음 빌드는 몇 분 소요 (의존성 다운로드)

4. **앱 설치 및 실행**
   - 빌드 완료 후 자동으로 기기에 설치됨
   - 앱이 자동으로 실행됨

---

### 방법 2: 명령줄 빌드 (Gradle)

Android Studio 없이 APK 파일만 생성하는 방법입니다.

#### 1단계: 서버 IP 주소 설정

**중요**: 빌드 전에 반드시 IP 주소를 설정해야 합니다!

1. **파일 열기** (메모장 또는 코드 에디터):
   ```
   monitoring\mobile_app_android\app\src\main\java\com\wickedzerg\mobilegcs\api\ApiClient.kt
   ```

2. **IP 주소 수정**:
   ```kotlin
   private val BASE_URL = "http://YOUR_PC_IP:8000"  // 본인 PC IP로 변경
   ```

3. **PC IP 확인**:
   ```powershell
   ipconfig
   ```

---

#### 2단계: Gradle Wrapper 확인

**중요**: Android Studio에서 프로젝트를 한 번 열어서 Gradle Wrapper를 생성해야 합니다!

```powershell
cd D:\Swarm-contol-in-sc2bot\Swarm-contol-in-sc2bot\wicked_zerg_challenger\monitoring\mobile_app_android

# Gradle Wrapper 파일 확인
dir gradlew.bat
```

**없다면**: Android Studio에서 프로젝트를 열어서 Gradle 동기화를 한 번 실행하세요.

---

#### 3단계: APK 빌드

**Windows (PowerShell/CMD)**:
```powershell
cd D:\Swarm-contol-in-sc2bot\Swarm-contol-in-sc2bot\wicked_zerg_challenger\monitoring\mobile_app_android

# Debug APK 빌드
.\gradlew.bat assembleDebug
```

**Linux/Mac**:
```bash
cd monitoring/mobile_app_android

# 실행 권한 부여 (처음 한 번만)
chmod +x gradlew

# Debug APK 빌드
./gradlew assembleDebug
```

**빌드 완료 메시지**:
```
BUILD SUCCESSFUL in 2m 30s
```

---

#### 4단계: APK 파일 위치

빌드가 완료되면 APK 파일이 생성됩니다:

```
monitoring\mobile_app_android\app\build\outputs\apk\debug\app-debug.apk
```

---

#### 5단계: APK 설치

1. **APK 파일을 Android 기기로 전송**
   - USB로 복사
   - 이메일로 전송
   - 클라우드 스토리지 사용

2. **기기에서 설치**
   - 파일 관리자에서 APK 파일 열기
   - "알 수 없는 소스" 허용 (필요한 경우)
   - 설치 진행

---

## ? 문제 해결

### Gradle 동기화 실패

**증상**: "Gradle sync failed"

**해결 방법**:
1. **인터넷 연결 확인**: Gradle이 의존성을 다운로드해야 함
2. **프록시 설정**: 회사 네트워크인 경우 설정 필요
3. **Gradle 버전 확인**: `gradle/wrapper/gradle-wrapper.properties` 확인
4. **캐시 삭제**: `File > Invalidate Caches / Restart`

---

### 빌드 오류

**증상**: "Build failed"

**해결 방법**:
1. **SDK 버전 확인**: `compileSdk = 34` 확인
2. **JDK 버전 확인**: JDK 17 이상 필요
3. **의존성 충돌**: `./gradlew clean` 후 재빌드
4. **에러 메시지 확인**: Build 탭에서 상세 에러 확인

---

### 기기가 인식되지 않음

**증상**: "No devices found"

**해결 방법**:
1. **USB 디버깅 확인**: 기기에서 USB 디버깅 활성화
2. **USB 드라이버 설치**: 기기 제조사 USB 드라이버 설치
3. **USB 케이블 확인**: 데이터 전송 가능한 케이블 사용
4. **기기 재연결**: USB 케이블 뽑았다가 다시 연결

---

### 앱이 서버에 연결되지 않음

**증상**: 앱에서 "Disconnected" 표시

**해결 방법**:
1. **서버 실행 확인**: `python monitoring/dashboard.py` 실행 중인지 확인
2. **IP 주소 확인**: `ApiClient.kt`의 `BASE_URL` 확인
3. **방화벽 확인**: Windows 방화벽에서 포트 8000 허용
4. **같은 네트워크**: PC와 모바일이 같은 Wi-Fi에 연결되어 있는지 확인

---

## ? 체크리스트

빌드 전 확인 사항:

- [ ] Android Studio 설치 완료
- [ ] 프로젝트 열기 및 Gradle 동기화 완료
- [ ] `ApiClient.kt`에서 서버 IP 주소 설정 완료
- [ ] 대시보드 서버 실행 중 (`python dashboard.py`)
- [ ] Android 기기 USB 디버깅 활성화
- [ ] 기기가 Android Studio에서 인식됨

---

## ? 빠른 참조

### 서버 IP 주소 확인
```powershell
ipconfig
# IPv4 주소 확인
```

### 대시보드 서버 실행
```powershell
cd monitoring
python dashboard.py
```

### APK 빌드 (명령줄)
```powershell
cd monitoring\mobile_app_android
.\gradlew.bat assembleDebug
```

### APK 위치
```
app\build\outputs\apk\debug\app-debug.apk
```

---

## ? 관련 문서

- **빠른 시작**: `docs/ANDROID_APP_QUICK_START.md`
- **상세 가이드**: `docs/ANDROID_APP_BUILD_GUIDE.md`
- **프로젝트 README**: `monitoring/mobile_app_android/README.md`

---

**빌드 성공을 기원합니다!** ?
