# 학습 실행 에러 및 버그 리포트

**작성 일시**: 2026년 01-13  
**리포트 범위**: 리플레이 학습 실행 중 발견된 에러 및 버그  
**상태**: ? **SyntaxError 수정 완료**, ?? **경로 문제 확인 필요**

---

## ? 발견된 에러

### 1. ? SyntaxError: expected 'except' or 'finally' block (수정 완료)

#### 에러 위치
- **파일**: `local_training/replay_build_order_learner.py`
- **라인**: 451번째 줄
- **에러 메시지**: `SyntaxError: expected 'except' or 'finally' block`

#### 문제 원인
```python
try:
    # Extract build order with phase-specific focus
    build_order = self.extract_build_order(replay_path, phase_focus=phase_info)
if build_order:  # ? try 블록 밖에 있음
```

`if build_order:` 구문이 `try` 블록 밖에 있어서 SyntaxError 발생.

#### 수정 내용
```python
try:
    # Extract build order with phase-specific focus
    build_order = self.extract_build_order(replay_path, phase_focus=phase_info)
    
    if build_order:  # ? try 블록 안으로 이동
        # ... 나머지 코드 ...
```

#### 수정 상태
- ? **수정 완료**: `if build_order:` 블록을 `try` 블록 안으로 이동
- ? **들여쓰기 수정**: 전체 블록 들여쓰기 정리
- ? **구문 검증 완료**: `python -m py_compile` 통과

---

### 2. ? NameError: name 'Any' is not defined (수정 완료)

#### 에러 위치
- **파일**: `local_training/replay_build_order_learner.py`
- **라인**: 242번째 줄
- **에러 메시지**: `NameError: name 'Any' is not defined. Did you mean: 'any'?`

#### 문제 원인
```python
from typing import Dict, List, Optional, Tuple  # ? Any 누락

def _extract_strategies(...) -> List[Dict[str, Any]]:  # ? Any 사용
```

`typing` 모듈에서 `Any`를 import하지 않았는데 사용함.

#### 수정 내용
```python
from typing import Dict, List, Optional, Tuple, Any  # ? Any 추가
```

#### 수정 상태
- ? **수정 완료**: `Any`를 `typing` import에 추가
- ? **구문 검증 완료**: `python -m py_compile` 통과

---

## ?? 발견된 경고 및 문제

### 3. ?? 모든 리플레이가 "IN PROGRESS" 상태로 건너뛰어짐

#### 문제 현상
```
[IN PROGRESS] 20240208 - GAME 1 - Dark vs herO - ZvP - Oceanborn.SC2Replay - Already being learned, skipping
[IN PROGRESS] 20240208 - GAME 1 - Dark vs ShoWTimE - ZvP - Hard Lead.SC2Replay - Already being learned, skipping
...
(모든 100개 리플레이가 동일하게 건너뛰어짐)
[WARNING] No build orders extracted. Check replay directory.
Extracted build orders from 0 replays
```

#### 문제 원인
- **Stale Session 문제**: 이전 학습 실행이 비정상 종료되어 `crash_log.json`의 `in_progress` 상태가 정리되지 않음
- **복구 로직 문제**: `recover_stale_sessions(max_age_seconds=3600)`가 1시간 이내의 세션만 복구하지만, 실제로는 더 오래된 세션이 남아있을 수 있음
- **수동 복구 필요**: `crash_log.json` 파일을 수동으로 정리하거나, `max_age_seconds`를 더 크게 설정해야 함

#### 해결 방법

**방법 1: Stale Session 복구 시간 증가**
```python
# replay_build_order_learner.py 라인 413
crash_handler.recover_stale_sessions(max_age_seconds=86400)  # 24시간으로 증가
```

**방법 2: crash_log.json 수동 정리**
- `D:\replays\replays\crash_log.json` 파일에서 `in_progress` 항목 삭제
- 또는 파일 전체 삭제 후 재생성

**방법 3: 강제 복구 옵션 추가**
- `--force-recover` 옵션으로 모든 stale session 강제 복구

#### 확인 필요 사항
- [ ] `D:\replays\replays\crash_log.json` 파일 확인
- [ ] `in_progress` 항목 확인 및 정리
- [ ] Stale session 복구 시간 조정

---

## ? 학습 실행 로그 분석

### 실행 시간
- **시작 시간**: 2026-01-13 21:31:29
- **종료 시간**: 2026-01-13 21:34:39
- **소요 시간**: 약 3분 10초

### 처리된 리플레이
- **처리 대상**: 100개 리플레이
- **추출 성공**: 0개
- **추출 실패**: 100개 (또는 경로 문제로 파일을 찾지 못함)

### 로그 메시지
```
[INFO] Processing 100 replays...
[INFO] Extracted build orders from 0 replays
[WARNING] No build orders extracted. Check replay directory.
```

---

## ? 수정 완료 사항

### 1. SyntaxError 수정
- ? `if build_order:` 블록을 `try` 블록 안으로 이동
- ? 들여쓰기 정리
- ? 구문 검증 완료

### 2. NameError 수정
- ? `Any`를 `typing` import에 추가
- ? 구문 검증 완료

---

## ?? 추가 조사 필요 사항

### 1. Stale Session 문제 해결
- [x] ? **Stale session 복구 시간 증가**: 1시간 → 24시간으로 수정 완료
- [ ] `D:\replays\replays\crash_log.json` 파일 확인 및 정리
- [ ] `in_progress` 항목 수동 정리 (필요 시)

### 2. 리플레이 경로 확인
- [x] ? `D:\replays\replays\` 디렉토리 존재 확인 (206개 파일 확인됨)
- [ ] 리플레이 파일 접근 권한 확인
- [ ] 환경 변수 설정 확인

### 3. 리플레이 파일 유효성 확인
- [ ] Zerg 플레이어 포함 여부 확인
- [ ] 게임 시간 확인 (최소 5분)
- [ ] 리플레이 파일 손상 여부 확인

### 4. sc2reader 패키지 확인
- [ ] 설치 여부 확인 (`pip list | findstr sc2reader`)
- [ ] 버전 호환성 확인

---

## ? 권장 조치 사항

### 즉시 조치
1. ? **SyntaxError 수정 완료** - 코드 수정 완료
2. ? **NameError 수정 완료** - import 추가 완료
3. ? **Stale Session 복구 시간 증가** - 1시간 → 24시간으로 수정 완료
4. ?? **crash_log.json 정리** - `in_progress` 항목 수동 정리 필요
5. ?? **리플레이 파일 유효성 검증** - Zerg 플레이어 포함 여부 확인

### 추가 조사
1. 리플레이 파일 샘플 검증 (수동으로 몇 개 파일 확인)
2. `sc2reader` 로드 테스트
3. 경로 감지 로직 디버깅

---

## ? 다음 단계

### 1. 리플레이 경로 문제 해결
- 리플레이 디렉토리 경로 확인
- 환경 변수 설정 확인
- 자동 경로 감지 로직 개선

### 2. 리플레이 파일 유효성 검증
- 샘플 리플레이 파일 수동 검증
- Zerg 플레이어 포함 여부 확인
- 게임 시간 확인

### 3. 에러 로깅 개선
- 더 상세한 에러 메시지 추가
- 리플레이별 실패 원인 로깅
- 경로 문제 진단 로깅

---

**리포트 작성일**: 2026년 01-13  
**작성자**: AI Assistant  
**상태**: ? **SyntaxError/NameError 수정 완료**, ? **Stale Session 복구 시간 증가 완료**, ?? **crash_log.json 정리 필요**

---

## ? 수정 완료 요약

### 수정된 파일
1. ? `local_training/replay_build_order_learner.py`
   - SyntaxError 수정 (451번째 줄)
   - NameError 수정 (`Any` import 추가)
   - Stale session 복구 시간 증가 (1시간 → 24시간)

### 다음 실행 시 예상 동작
- Stale session이 24시간 이내면 자동 복구
- 24시간 이상된 stale session은 수동 정리 필요
- 정리 후 재실행 시 정상 학습 진행 예상
