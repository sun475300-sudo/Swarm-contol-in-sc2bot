# 3개 도메인 구현 계획

**작성 일시**: 2026-01-14  
**목적**: 시스템 안정성, 모바일 관제, 클라우드 지능 도메인 구현 상태 개선  
**상태**: ? **계획 수립**

---

## ? 현재 구현 상태

| 도메인 | 구현 상태 | 완성도 | 주요 문제점 |
|--------|----------|--------|------------|
| **3. 시스템 안정성** | ?? 부분 구현 | 70% | 자가치유 모듈만 존재, 통합 필요 |
| **4. 모바일 관제** | ?? 부분 구현 | 60% | Flask만 구현, Android 앱 없음 |
| **5. 클라우드 지능** | ?? 부분 구현 | 30% | 모듈만 존재, 통합 필요 |

---

## ? 구현 계획

### 1. 시스템 안정성 (Self-Healing & DevOps) - 70% → 100%

**현재 상태:**
- ? `genai_self_healing.py` 모듈 존재
- ? 패키징/업로드 스크립트 구현 (`tools/package_for_aiarena*.py`)
- ? `wicked_zerg_bot_pro.py`에 통합되지 않음
- ? 에러 핸들러와 연결되지 않음

**구현 항목:**

#### 1-1. Gen-AI Self-Healing 통합
- **파일**: `wicked_zerg_bot_pro.py`
- **작업**: `on_step` 메서드의 에러 핸들러에 `genai_self_healing` 통합
- **위치**: Line 1477-1520 (Global error handler)
- **내용**:
  ```python
  # 에러 발생 시 Gemini API를 통한 자동 분석 및 패치 제안
  if self.self_healing and self.self_healing.is_available():
      context = {
          'iteration': iteration,
          'game_time': self.time,
          'instance_id': getattr(self, 'instance_id', 0)
      }
      patch = self.self_healing.analyze_error(e, context)
      if patch:
          # 패치 제안을 로그에 저장
          logger.info(f"[SELF-HEALING] Patch suggested: {patch.description}")
  ```

#### 1-2. 초기화 코드 추가
- **파일**: `wicked_zerg_bot_pro.py`
- **위치**: `__init__` 메서드
- **내용**: `self.self_healing = GenAISelfHealing()` 초기화

**예상 완성도**: 70% → 100%

---

### 2. 모바일 관제 시스템 (Mobile GCS) - 60% → 100%

**현재 상태:**
- ? Flask 대시보드 구현 (`monitoring/dashboard.py`)
- ? 웹 UI 존재 (`monitoring/mobile_app/public/index.html`)
- ? API 엔드포인트 구현 (`monitoring/dashboard_api.py`)
- ? Android 네이티브 앱 없음
- ? TWA(Trusted Web Activity) 구조 없음

**구현 항목:**

#### 2-1. Android 앱 구조 생성 (선택 1: TWA 기반)
- **폴더**: `mobile_app/` (신규 생성)
- **구조**:
  ```
  mobile_app/
  ├── build.gradle (프로젝트 수준)
  ├── settings.gradle
  ├── app/
  │   ├── build.gradle (앱 수준)
  │   ├── src/
  │   │   └── main/
  │   │       ├── AndroidManifest.xml
  │   │       ├── java/.../MainActivity.java
  │   │       └── res/
  └── gradle.properties
  ```
- **내용**: TWA(Trusted Web Activity)를 사용하여 웹 대시보드를 앱처럼 실행

#### 2-2. Android 앱 구조 생성 (선택 2: 웹뷰 기반)
- **더 간단한 방법**: 웹뷰를 사용하여 웹 대시보드를 표시
- **구조**: TWA보다 간단하지만 네이티브 기능 제한

**권장 사항**: TWA 기반 (더 현대적이고 보안성이 좋음)

**예상 완성도**: 60% → 100%

---

### 3. 클라우드 지능 (Cloud Intelligence) - 30% → 100%

**현재 상태:**
- ? `genai_self_healing.py` 모듈 존재
- ? `wicked_zerg_bot_pro.py`에 통합되지 않음
- ? Gemini API 통합 미흡

**구현 항목:**

#### 3-1. Gemini API 통합
- **작업**: 1번(시스템 안정성)과 동일
- **파일**: `wicked_zerg_bot_pro.py`
- **내용**: 에러 핸들러에 Gemini API 통합

#### 3-2. 환경 변수 설정
- **필요 사항**: `GOOGLE_API_KEY` 또는 `GEMINI_API_KEY` 환경 변수 설정
- **문서**: `.env.example` 파일에 추가

**참고**: 클라우드 지능 도메인은 시스템 안정성(자가치유) 도메인과 밀접하게 연관되어 있으므로, 1번과 함께 구현하는 것이 효율적입니다.

**예상 완성도**: 30% → 100% (1번과 함께 구현)

---

## ? 구현 우선순위

### Phase 1: 시스템 안정성 + 클라우드 지능 통합 (높은 우선순위)
1. ? `genai_self_healing.py` 모듈 확인
2. ?? `wicked_zerg_bot_pro.py`에 통합
3. ?? 에러 핸들러에 연결
4. ?? 테스트 및 검증

**예상 작업 시간**: 1-2시간

---

### Phase 2: 모바일 관제 시스템 (중간 우선순위)
1. ?? Android 앱 구조 생성 (TWA 또는 웹뷰)
2. ?? 빌드 설정 파일 생성 (`build.gradle` 등)
3. ?? 매니페스트 파일 생성 (`AndroidManifest.xml`)
4. ?? 빌드 및 테스트

**예상 작업 시간**: 2-4시간

---

## ? 구현 체크리스트

### 시스템 안정성 (Self-Healing)
- [ ] `wicked_zerg_bot_pro.py`에 `genai_self_healing` import 추가
- [ ] `__init__` 메서드에 `self.self_healing` 초기화 추가
- [ ] 에러 핸들러에 `analyze_error` 호출 추가
- [ ] 패치 제안 로그 저장 확인
- [ ] 테스트 및 검증

### 모바일 관제 (Mobile GCS)
- [ ] Android 앱 구조 생성 (TWA 또는 웹뷰)
- [ ] `mobile_app/build.gradle` 생성
- [ ] `mobile_app/app/build.gradle` 생성
- [ ] `AndroidManifest.xml` 생성
- [ ] MainActivity.java 생성
- [ ] 빌드 테스트

### 클라우드 지능 (Cloud Intelligence)
- [ ] Gemini API 통합 (1번과 함께)
- [ ] 환경 변수 설정 가이드
- [ ] API 키 관리 문서

---

## ? 관련 문서

- `ARCHITECTURE_OVERVIEW.md` - 아키텍처 개요
- `genai_self_healing.py` - Gen-AI Self-Healing 모듈
- `wicked_zerg_bot_pro.py` - 메인 봇 클래스
- `monitoring/dashboard.py` - Flask 대시보드
- `monitoring/mobile_app/public/index.html` - 웹 UI

---

**생성 일시**: 2026-01-14  
**상태**: ? **계획 수립 완료**
