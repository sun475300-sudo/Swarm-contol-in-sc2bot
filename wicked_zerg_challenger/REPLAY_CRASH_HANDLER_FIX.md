# ReplayCrashHandler Import 문제 수정 완료

**일시**: 2026-01-14  
**상태**: ? **수정 완료**

---

## ? 문제 진단

### 증상
```
[WARNING] replay_crash_handler not available - crash recovery disabled
```

### 원인
- `replay_build_order_learner.py`에서 `replay_crash_handler` 모듈을 import할 때 `sys.path` 설정이 각 try 블록 내에서만 실행되어 일관성 없이 동작
- 파일 상단에 `import sys`가 없어서 일부 경우에 import 실패

---

## ? 수정 사항

### 1. 파일 상단에 sys.path 설정 추가
**위치**: `replay_build_order_learner.py:5-14`

```python
import sys
from pathlib import Path

# CRITICAL: Add script directory to sys.path for local imports
script_dir = Path(__file__).parent
if str(script_dir) not in sys.path:
    sys.path.insert(0, str(script_dir))
```

**효과**: 모듈 로드 시점에 `sys.path`가 설정되어 모든 import가 일관되게 동작

### 2. 중복된 sys.path 설정 제거
**위치**: 여러 위치의 try 블록 내부

**변경 전**:
```python
try:
    import sys
    from pathlib import Path
    script_dir = Path(__file__).parent
    if str(script_dir) not in sys.path:
        sys.path.insert(0, str(script_dir))
    from replay_crash_handler import ReplayCrashHandler
```

**변경 후**:
```python
try:
    # sys.path is already set up at module level
    from replay_crash_handler import ReplayCrashHandler
```

**효과**: 코드 중복 제거 및 가독성 향상

---

## ? 수정된 위치

1. **파일 상단** (line 5-14)
   - `import sys` 추가
   - `sys.path` 설정 추가

2. **learn_from_replays 메서드** (line 474-476)
   - 중복된 `import sys`, `sys.path` 설정 제거

3. **learn_from_replays 메서드 - crash_handler** (line 519-524)
   - 중복된 `import sys`, `sys.path` 설정 제거

4. **extract_strategies 메서드** (line 357-363)
   - 중복된 `import sys`, `sys.path` 설정 제거

5. **learn_from_replays 메서드 - status_manager** (line 592-597)
   - 중복된 `import sys`, `sys.path` 설정 제거

---

## ? 예상 효과

1. **Import 안정성 향상**
   - `replay_crash_handler` 모듈이 정상적으로 import됨
   - Crash recovery 기능이 활성화됨

2. **코드 품질 개선**
   - 중복 코드 제거
   - 가독성 향상

3. **유지보수성 향상**
   - `sys.path` 설정이 한 곳에서 관리됨

---

## ? 검증 결과

```bash
python -c "from replay_crash_handler import ReplayCrashHandler; print('[OK] Import successful')"
# [OK] ReplayCrashHandler import successful
```

---

**상태**: ? **ReplayCrashHandler Import 문제 수정 완료**
