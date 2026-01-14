# 누락 파일 상태 확인 리포트

**작성 일시**: 2026-01-14  
**목적**: 사용자가 언급한 파일들의 상태 확인 및 분석  
**상태**: ? **확인 완료**

---

## ? 파일별 상태 확인

### 1. `tech_advancer.py` → `production_manager.py`에 통합됨

**상태**: ? **정상** (의도적으로 통합됨)

**증거:**
- `ARCHITECTURE_OVERVIEW.md` Line 50: "`tech_advancer.py`는 별도 파일로 존재하지 않으며, 업그레이드 로직은 `production_manager.py`에 통합되어 있습니다."
- 코드베이스에서 `tech_advancer` 참조 없음
- `production_manager.py`에 업그레이드 로직 포함됨

**결론**: 복원 불필요

---

### 2. `self_healing_orchestrator.py` → `genai_self_healing.py`가 대체

**상태**: ? **정상** (의도적으로 대체됨)

**증거:**
- `ARCHITECTURE_OVERVIEW.md` Line 139: "`self_healing_orchestrator.py` - **존재하지 않음** (genai_self_healing.py가 대체)"
- `genai_self_healing.py` 파일 존재 (루트 디렉토리)
- 코드베이스에서 `self_healing_orchestrator` 참조 없음

**결론**: 복원 불필요

---

### 3. `start_with_ngrok.sh` → 존재하지 않음 (참조만 있음)

**상태**: ?? **생성 필요**

**증거:**
- `local_training/scripts/parallel_train_integrated.py` Line 560에서 참조: `"./start_with_ngrok.sh"`
- 프로젝트에서 파일 검색 결과 없음
- 백업 디렉토리에서도 찾지 못함

**작업**: ngrok 터널링 스크립트 생성 필요

---

### 4. Android 네이티브 앱 소스 코드 → 웹 UI만 존재

**상태**: ?? **생성 필요**

**증거:**
- `ARCHITECTURE_OVERVIEW.md`에 Android 앱 언급 (Line 195-209)
- `README.md`에 Android 앱 언급
- 실제로는 `monitoring/mobile_app/public/index.html` (웹 UI)만 존재
- Android 소스 코드 (`*.java`, `*.kt`, `build.gradle`, `AndroidManifest.xml`) 없음
- 백업 디렉토리에서도 찾지 못함

**작업**: Android 앱 구조 생성 필요 (TWA 또는 웹뷰 기반)

---

## ? 요약

| 파일 | 현재 상태 | 백업 존재 | 복원 필요 | 비고 |
|------|----------|----------|----------|------|
| `tech_advancer.py` | 통합됨 | ? 있음 | ? 불필요 | `production_manager.py`에 통합 |
| `self_healing_orchestrator.py` | 대체됨 | ? 있음 | ? 불필요 | `genai_self_healing.py`로 대체 |
| `start_with_ngrok.sh` | 없음 | ? 없음 | ?? 생성 필요 | 참조만 있음 |
| Android 앱 소스 코드 | 없음 | ? 없음 | ?? 생성 필요 | 웹 UI만 존재 |

---

## ? 다음 단계

### 필요 작업

1. **`start_with_ngrok.sh` / `start_with_ngrok.bat` 생성**
   - `parallel_train_integrated.py`에서 참조 중
   - ngrok 터널링 스크립트 생성 필요

2. **Android 앱 구조 생성**
   - 문서에는 언급되어 있으나 실제 구현 없음
   - TWA 또는 웹뷰 기반 Android 앱 생성 필요

---

**생성 일시**: 2026-01-14  
**상태**: ? **확인 완료**
