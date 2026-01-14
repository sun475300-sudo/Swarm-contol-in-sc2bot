# 코드 품질 점검 가이드

**작성 일시**: 2026-01-14  
**목적**: 정기적인 소스코드 품질 점검 방법 안내

---

## ?? 점검 도구

### 1. 빠른 점검 (Quick Check)

**용도**: 주요 파일만 빠르게 점검 (약 1초)

```bash
python tools/quick_code_check.py
```

**점검 항목:**
- 주요 파일(`wicked_zerg_bot_pro.py`, `production_manager.py` 등)의 `await` 누락 문제

**출력 예시:**
```
빠른 코드 품질 점검 시작...

? wicked_zerg_bot_pro.py: 문제 없음
? production_manager.py: 문제 없음
? economy_manager.py: 문제 없음
? combat_manager.py: 문제 없음

============================================================
? 모든 주요 파일 점검 통과!
```

---

### 2. 전체 점검 (Full Check)

**용도**: 프로젝트 전체 코드 품질 점검 (약 10-30초)

```bash
python tools/code_quality_check.py
```

**점검 항목:**
1. **await 누락 문제 (Async Trap)** ? 높음
   - async 함수 내부에서 `train()` 호출 시 `await` 누락
2. **Bare Except 사용** ? 중간
   - `except:` 또는 `except: pass` 패턴
3. **매직 넘버 하드코딩** ? 중간
   - `100`, `500`, `1000` 등의 하드코딩된 숫자
4. **TODO/FIXME 주석** ? 참고
   - 코드 내 TODO, FIXME 주석

**출력 예시:**
```
코드 품질 점검 시작...
프로젝트 루트: D:\...\wicked_zerg_challenger
점검 대상 파일: 45개

================================================================================
코드 품질 점검 결과
================================================================================
점검 일시: 2026-01-14 15:30:00
점검 파일 수: 45
총 코드 라인: 12,345

## 1. await 누락 문제 (Async Trap)
--------------------------------------------------------------------------------
? 문제 없음

## 2. Bare Except 사용
--------------------------------------------------------------------------------
?? 발견: 3곳
  production_manager.py:123 - except Exception:
  ...

## 3. 매직 넘버 하드코딩
--------------------------------------------------------------------------------
?? 발견: 15곳 (참고용)
  ...

## 4. TODO/FIXME 주석
--------------------------------------------------------------------------------
? 발견: 5곳
  ...

================================================================================
요약
================================================================================
총 발견된 문제: 23곳
  - await 누락: 0곳
  - bare except: 3곳
  - 매직 넘버: 15곳 (참고)
  - TODO/FIXME: 5곳

? 주요 문제(await 누락) 없음
```

---

## ? 정기 점검 권장

### 권장 스케줄

1. **매일 (개발 중)**
   - 빠른 점검 실행: `python tools/quick_code_check.py`
   - 커밋 전 실행 권장

2. **주 1회 (정기 점검)**
   - 전체 점검 실행: `python tools/code_quality_check.py`
   - 결과를 기록하고 주요 문제 해결

3. **코드 변경 후**
   - 변경된 파일에 대한 빠른 점검
   - 주요 로직 수정 시 전체 점검

---

## ? 점검 항목 상세 설명

### 1. await 누락 문제 (Async Trap) ?

**심각도**: 높음  
**영향**: 생산 명령이 게임 엔진에 전달되지 않아 유닛 생산이 실행되지 않을 수 있음

**문제 예시:**
```python
async def produce_units(self):
    larva.train(UnitTypeId.ZERGLING)  # ? await 누락
```

**올바른 코드:**
```python
async def produce_units(self):
    await larva.train(UnitTypeId.ZERGLING)  # ? await 추가
```

---

### 2. Bare Except 사용 ?

**심각도**: 중간  
**영향**: 예외가 조용히 무시되어 디버깅이 어려울 수 있음

**문제 예시:**
```python
try:
    do_something()
except:  # ? 너무 일반적
    pass
```

**올바른 코드:**
```python
try:
    do_something()
except (AttributeError, TypeError) as e:  # ? 구체적인 예외
    print(f"[WARNING] Error: {e}")
```

---

### 3. 매직 넘버 하드코딩 ?

**심각도**: 중간  
**영향**: 코드 가독성 및 유지보수성 저하

**문제 예시:**
```python
if minerals > 500:  # ? 매직 넘버
    produce_units()
```

**올바른 코드:**
```python
RESOURCE_FLUSH_THRESHOLD = 500  # config.py
if minerals > RESOURCE_FLUSH_THRESHOLD:  # ? 상수 사용
    produce_units()
```

---

### 4. TODO/FIXME 주석 ?

**심각도**: 낮음 (참고용)  
**영향**: 미완성 작업 추적

**예시:**
```python
# TODO: 성능 최적화 필요
# FIXME: 메모리 누수 확인 필요
```

---

## ? 점검 결과 해석

### 종료 코드

- **0**: 점검 통과 (주요 문제 없음)
- **1**: 문제 발견 (await 누락 문제가 있는 경우)

### 리포트 해석

1. **await 누락: 0곳** ?
   - 가장 중요한 항목
   - 0곳이면 주요 문제 없음

2. **bare except: 실행 시 확인** ??
   - 예외 처리 개선 필요
   - 우선순위: 중간
   - 실제 숫자는 `tools/code_quality_check.py` 실행 시 확인

3. **매직 넘버: 실행 시 확인** ?
   - 참고용
   - 시간 있을 때 상수화 권장
   - 실제 숫자는 `tools/code_quality_check.py` 실행 시 확인

4. **TODO/FIXME: 실행 시 확인** ?
   - 미완성 작업 추적용
   - 주기적으로 검토 필요
   - 실제 숫자는 `tools/code_quality_check.py` 실행 시 확인

---

## ? 자동화 (선택 사항)

### Git Pre-commit Hook

커밋 전 자동 점검:

```bash
# .git/hooks/pre-commit 파일 생성
#!/bin/sh
python tools/quick_code_check.py
if [ $? -ne 0 ]; then
    echo "코드 품질 점검 실패. 커밋을 중단합니다."
    exit 1
fi
```

### Windows 배치 파일

```batch
@echo off
echo 코드 품질 점검 중...
python tools\quick_code_check.py
if %ERRORLEVEL% NEQ 0 (
    echo 점검 실패!
    pause
    exit /b 1
)
echo 점검 통과!
```

---

## ? 점검 결과 기록

점검 결과를 파일로 저장:

```bash
# 전체 점검 결과 저장
python tools/code_quality_check.py > code_quality_report_$(date +%Y%m%d).txt

# Windows
python tools\code_quality_check.py > code_quality_report_%date:~0,4%%date:~5,2%%date:~8,2%.txt
```

---

## ? 관련 문서

- `COMPREHENSIVE_CODE_REVIEW_REPORT.md` - 전체 코드 검토 리포트
- `CODE_QUALITY_ISSUES_REPORT.md` - 코드 품질 문제 리포트
- `ENGINEERING_CHALLENGES_VERIFICATION.md` - 엔지니어링 챌린지 해결 상태

---

**생성 일시**: 2026-01-14  
**상태**: ? **활성**
