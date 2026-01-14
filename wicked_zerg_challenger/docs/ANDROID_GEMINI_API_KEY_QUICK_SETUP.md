# Android Studio Gemini API 키 빠른 설정 가이드

**작성 일시**: 2026-01-14  
**상태**: ? **빠른 설정 가이드 완료**

---

## ? 3단계로 API 키 설정하기

### 1단계: local.properties 파일 열기

1. **Android Studio에서 프로젝트 열기**
2. **프로젝트 뷰에서 `local.properties` 찾기**
   - 위치: `monitoring/mobile_app_android/local.properties`
   - 프로젝트 루트 폴더에 있음

3. **파일 열기** (더블클릭)

---

### 2단계: API 키 추가

`local.properties` 파일 맨 아래에 다음을 추가:

```properties
# Gemini API Key (DO NOT COMMIT TO GIT)
GEMINI_API_KEY=YOUR_API_KEY_HERE
```

**예시**:
```properties
# Gemini API Key (DO NOT COMMIT TO GIT)
GEMINI_API_KEY=AIzaSyAbc123def456ghi789jkl012mno345pqr678
```

**API 키 발급 방법**:
1. https://makersuite.google.com/app/apikey 접속
2. "Create API Key" 클릭
3. API 키 복사하여 위에 붙여넣기

---

### 3단계: Gradle 동기화

1. **Android Studio 상단 메뉴**: `File > Sync Project with Gradle Files`
2. **또는**: 상단 툴바의 "Sync Now" 클릭
3. **동기화 완료 대기** (몇 초 소요)

---

## ? 완료!

이제 코드에서 API 키를 사용할 수 있습니다:

```kotlin
import com.wickedzerg.mobilegcs.BuildConfig

class MyActivity {
    private val apiKey = BuildConfig.GEMINI_API_KEY
    
    fun useGemini() {
        if (apiKey.isNotEmpty()) {
            // Gemini API 사용
            println("API Key loaded: ${apiKey.take(10)}...")
        }
    }
}
```

---

## ? 확인 방법

### BuildConfig 확인

빌드 후 다음 위치에서 확인:
```
app/build/generated/source/buildConfig/debug/com/wickedzerg/mobilegcs/BuildConfig.java
```

`GEMINI_API_KEY` 필드가 있는지 확인하세요.

---

## ? 문제 해결

### API 키가 비어있음

1. `local.properties` 파일에 `GEMINI_API_KEY`가 정확히 입력되었는지 확인
2. Gradle 동기화 재실행
3. 프로젝트 클린 후 재빌드: `Build > Clean Project`

### BuildConfig가 생성되지 않음

1. `app/build.gradle.kts`에서 `buildConfig = true` 확인
2. Gradle 동기화 재실행

---

## ? 상세 가이드

더 자세한 내용은 `docs/ANDROID_GEMINI_API_KEY_SETUP.md`를 참조하세요.
