# 네트워크 연결 시간 초과 문제 해결 가이드

**문제**: `SocketTimeoutException` - 앱이 로컬 개발 서버에 연결하지 못함

**작성일**: 2026-01-15  
**상태**: ✅ 코드 개선 완료

---

## 🔍 문제 분석

### 발생 원인

1. **타임아웃 시간이 너무 짧음**
   - `ApiClient`: 5초 (연결/읽기)
   - `ManusApiClient`: 10초 (연결/읽기)
   - 서버 응답이 느릴 경우 타임아웃 발생

2. **재시도 로직 없음**
   - 네트워크 일시적 오류 시 자동 재시도 없음

3. **서버 URL 하드코딩**
   - 에뮬레이터와 실제 기기에서 다른 IP 필요
   - 설정 변경이 어려움

4. **로컬 서버 미실행**
   - 개발 서버가 실행되지 않았을 수 있음

5. **방화벽 차단**
   - Windows 방화벽이 포트 8000을 차단할 수 있음

---

## ✅ 해결 방법

### 1. 코드 개선 (완료됨) ⭐

#### 타임아웃 시간 증가

**변경 전**:
```kotlin
.connectTimeout(5, TimeUnit.SECONDS)  // ApiClient
.readTimeout(5, TimeUnit.SECONDS)
```

**변경 후**:
```kotlin
.connectTimeout(15, TimeUnit.SECONDS)  // ApiClient
.readTimeout(20, TimeUnit.SECONDS)
.writeTimeout(15, TimeUnit.SECONDS)  // 추가됨
.retryOnConnectionFailure(true)  // 자동 재시도 활성화
```

**개선 사항**:
- ✅ 연결 타임아웃: 5초 → 15초 (ApiClient), 10초 → 15초 (ManusApiClient)
- ✅ 읽기 타임아웃: 5초 → 20초 (ApiClient), 10초 → 20초 (ManusApiClient)
- ✅ 쓰기 타임아웃 추가: 15초
- ✅ 자동 재시도 활성화: `retryOnConnectionFailure(true)`

---

### 2. 로컬 서버 실행 확인

#### 서버 실행 확인

**PowerShell에서 확인**:
```powershell
# 포트 8000이 사용 중인지 확인
netstat -ano | findstr :8000

# 또는
Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue
```

**서버가 실행 중이면**:
```
Local Address: 0.0.0.0:8000 또는 127.0.0.1:8000
State: LISTENING
```

**서버가 실행 중이 아니면**:
- 서버를 시작하세요
- 예: `python manage.py runserver 0.0.0.0:8000` (Django)
- 예: `uvicorn main:app --host 0.0.0.0 --port 8000` (FastAPI)

---

### 3. 방화벽 설정 확인

#### Windows 방화벽 설정

**방법 1: PowerShell로 포트 열기** (관리자 권한 필요):
```powershell
# 인바운드 규칙 추가
New-NetFirewallRule -DisplayName "SC2 Bot API Server" `
    -Direction Inbound `
    -LocalPort 8000 `
    -Protocol TCP `
    -Action Allow
```

**방법 2: Windows 방화벽 GUI**:
1. **Windows 보안** > **방화벽 및 네트워크 보호** 열기
2. **고급 설정** 클릭
3. **인바운드 규칙** > **새 규칙** 클릭
4. **포트** 선택 > **다음**
5. **TCP** 선택, **특정 로컬 포트**: `8000` 입력
6. **연결 허용** 선택
7. 모든 프로필에 적용
8. 이름: "SC2 Bot API Server"

**방법 3: 개발 중 임시로 방화벽 비활성화** (권장하지 않음):
```powershell
# 관리자 권한 필요
Set-NetFirewallProfile -Profile Domain,Public,Private -Enabled False
```

---

### 4. 서버 URL 설정

#### 에뮬레이터 vs 실제 기기

**에뮬레이터에서 실행**:
```kotlin
private val BASE_URL = "http://10.0.2.2:8000"
```
- `10.0.2.2`는 Android 에뮬레이터의 특수 IP로 호스트의 `localhost`를 가리킴

**실제 기기에서 실행**:
```kotlin
// PC의 로컬 IP 주소 사용
private val BASE_URL = "http://192.168.1.100:8000"  // 예시
```

**PC IP 주소 확인**:
```powershell
# Windows
ipconfig

# IPv4 주소 찾기 (예: 192.168.1.100)
```

**동적 설정 (권장)**:
향후 개선 사항으로 `SharedPreferences` 또는 `BuildConfig`를 사용하여 런타임에 서버 URL을 변경할 수 있도록 할 수 있습니다.

---

### 5. 네트워크 연결 테스트

#### 브라우저에서 테스트

**에뮬레이터에서**:
- 에뮬레이터의 브라우저에서 `http://10.0.2.2:8000/api/game-state` 접속 시도

**실제 기기에서**:
- 기기의 브라우저에서 `http://YOUR_PC_IP:8000/api/game-state` 접속 시도

**성공 시**: JSON 응답이 표시됨  
**실패 시**: 연결 오류 메시지 표시

---

## 📝 수정된 파일

### 1. `ApiClient.kt`

**변경 사항**:
- ✅ 연결 타임아웃: 5초 → 15초
- ✅ 읽기 타임아웃: 5초 → 20초
- ✅ 쓰기 타임아웃 추가: 15초
- ✅ 자동 재시도 활성화

### 2. `ManusApiClient.kt`

**변경 사항**:
- ✅ 연결 타임아웃: 10초 → 15초
- ✅ 읽기 타임아웃: 10초 → 20초
- ✅ 쓰기 타임아웃 추가: 15초
- ✅ 자동 재시도 활성화

---

## 🔧 추가 확인 사항

### 1. 서버가 올바른 호스트에서 실행 중인지 확인

**잘못된 설정**:
```bash
# localhost만 리스닝 (에뮬레이터에서 접근 불가)
python manage.py runserver  # 기본값: 127.0.0.1:8000
```

**올바른 설정**:
```bash
# 모든 인터페이스에서 리스닝
python manage.py runserver 0.0.0.0:8000
```

---

### 2. 네트워크 보안 설정 확인

**AndroidManifest.xml**:
```xml
<application
    android:usesCleartextTraffic="true"  <!-- HTTP 허용 -->
    ...>
```
✅ 이미 설정되어 있음

---

### 3. 에뮬레이터 네트워크 설정

**Android Studio AVD Manager**:
- 에뮬레이터가 올바른 네트워크에 연결되어 있는지 확인
- **Settings** > **Network** > **Advanced** 확인

---

## 🚀 빠른 해결 체크리스트

- [ ] **서버 실행 확인**: 포트 8000에서 서버가 실행 중인가?
- [ ] **방화벽 확인**: Windows 방화벽이 포트 8000을 허용하는가?
- [ ] **서버 바인딩 확인**: 서버가 `0.0.0.0:8000`에서 리스닝하는가?
- [ ] **IP 주소 확인**: 실제 기기 사용 시 PC의 로컬 IP 주소 확인
- [ ] **브라우저 테스트**: 에뮬레이터/기기 브라우저에서 서버 접근 가능한가?
- [ ] **앱 재빌드**: 코드 변경 후 앱 재빌드 및 재설치

---

## 📊 타임아웃 설정 비교

| 클라이언트 | 연결 타임아웃 | 읽기 타임아웃 | 쓰기 타임아웃 | 재시도 |
|----------|------------|------------|------------|--------|
| **ApiClient (이전)** | 5초 | 5초 | 없음 | 없음 |
| **ApiClient (개선)** | 15초 | 20초 | 15초 | ✅ 활성화 |
| **ManusApiClient (이전)** | 10초 | 10초 | 없음 | 없음 |
| **ManusApiClient (개선)** | 15초 | 20초 | 15초 | ✅ 활성화 |

---

## 🎯 예상 결과

### 개선 전
- ❌ 서버 응답이 5초 이상 걸리면 타임아웃 발생
- ❌ 네트워크 일시적 오류 시 재시도 없음
- ❌ 연결 실패 시 즉시 오류 발생

### 개선 후
- ✅ 서버 응답이 20초 이내면 정상 작동
- ✅ 네트워크 일시적 오류 시 자동 재시도
- ✅ 더 긴 타임아웃으로 안정적인 연결

---

## 🔍 문제 해결 순서

1. **서버 실행 확인** (가장 중요)
   ```powershell
   netstat -ano | findstr :8000
   ```

2. **방화벽 설정 확인**
   ```powershell
   Get-NetFirewallRule | Where-Object {$_.DisplayName -like "*8000*"}
   ```

3. **서버 바인딩 확인**
   - 서버가 `0.0.0.0:8000`에서 리스닝하는지 확인

4. **브라우저 테스트**
   - 에뮬레이터/기기 브라우저에서 서버 접근

5. **앱 재빌드**
   - 코드 변경 후 앱 재빌드 및 재설치

---

## 📚 참고 자료

- [OkHttp Timeout Documentation](https://square.github.io/okhttp/4.x/okhttp/okhttp3/-ok-http-client/-builder/connect-timeout/)
- [Android Network Security Config](https://developer.android.com/training/articles/security-config)
- [Android Emulator Networking](https://developer.android.com/studio/run/emulator-networking)

---

**마지막 업데이트**: 2026-01-15  
**상태**: ✅ 코드 개선 완료  
**다음 단계**: 서버 실행 및 방화벽 설정 확인
