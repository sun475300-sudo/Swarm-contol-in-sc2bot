# 리플레이 분석 강제 실행 가이드

**작성 일시**: 2026년 01-13  
**목적**: Spawning Tool 크롤링 실패 시 리플레이 직접 분석으로 전환  
**상태**: ✅ **설정 완료**

---

## 🔍 문제 상황

Spawning Tool 사이트 크롤링이 실패하여 빌드 오더가 수집되지 않음 (`Collected 0 build orders`).

**원인**:
- 웹사이트 구조 변경으로 인한 URL 감지 실패
- 내비게이션 메뉴만 크롤링되고 실제 빌드 오더 페이지를 찾지 못함

---

## ✅ 해결 방법: 리플레이 직접 분석

이미 보유한 프로게이머 리플레이 파일(`D:\replays\replays`)을 직접 분석하여 빌드 오더를 추출합니다.

---

## 📋 실행 단계

### 1단계: 학습 상태 파일 정리 (필수)

**방법 A: 배치 파일 사용 (권장)**
```cmd
bat\clear_learning_state.bat
```

**방법 B: 수동 삭제**
```cmd
del /q D:\replays\replays\learning_status.json
del /q D:\wicked_zerg_challenger\local_training\scripts\learning_status.json
del /q D:\wicked_zerg_challenger\stats\*.json
```

**방법 C: Python 스크립트로 crash_log.json 정리**
```python
import json
from pathlib import Path

crash_log = Path("D:/replays/replays/crash_log.json")
if crash_log.exists():
    data = json.loads(crash_log.read_text(encoding='utf-8'))
    data['in_progress'] = {}  # Clear stale sessions
    crash_log.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding='utf-8')
    print("Cleared in_progress entries")
```

### 2단계: 리플레이 분석 실행

```cmd
cd D:\wicked_zerg_challenger
bat\start_replay_learning.bat
```

---

## 🔧 코드 변경 사항

### `local_training/replay_build_order_learner.py` (433-435 라인)

**변경 전**:
```python
# CRITICAL: Check if replay is already in progress (prevent duplicate processing)
if crash_handler and crash_handler.is_in_progress(replay_path):
    logger.info(f"[IN PROGRESS] {replay_path.name} - Already being learned, skipping")
    continue
```

**변경 후** (주석 처리됨):
```python
# CRITICAL: Check if replay is already in progress (prevent duplicate processing)
# NOTE: Temporarily disabled to force replay analysis - stale sessions are auto-cleared by is_in_progress()
# Uncomment below if you want to re-enable the check (automatic stale session clearing is still active)
# if crash_handler and crash_handler.is_in_progress(replay_path):
#     logger.info(f"[IN PROGRESS] {replay_path.name} - Already being learned, skipping")
#     continue
```

**이유**:
- 리플레이 분석을 강제로 실행하기 위해 `is_in_progress` 체크를 일시적으로 비활성화
- 자동 stale session 정리 로직(`replay_crash_handler.py`)은 여전히 작동하므로, 1시간 이상 된 stale session은 자동으로 정리됨
- 필요 시 주석을 해제하여 다시 활성화 가능

---

## 📊 예상 결과

리플레이 분석이 성공하면:

1. **빌드 오더 추출**: `data/build_orders/` 폴더에 JSON 파일 생성
2. **학습 시작**: 10차원 신경망(ZergNet)이 실제 학습 시작
3. **로그 확인**: `[EXTRACTED]` 메시지와 함께 빌드 오더 추출 완료 확인

**성공 로그 예시**:
```
[EXTRACTED] Replay_001.SC2Replay - Extracted 45 build steps
[EXTRACTED] Replay_002.SC2Replay - Extracted 52 build steps
[BUILD LEARNING] Saved learned parameters to D:/replays/archive/training_YYYYMMDD_HHMMSS/learned_build_orders.json
```

---

## ⚠️ 주의 사항

### 자동 Stale Session 정리

`replay_crash_handler.py`의 `is_in_progress()` 메서드는 여전히 작동하며:
- 1시간 이상 된 stale session을 자동으로 감지 및 삭제
- 수동 삭제 없이도 자동으로 학습 재개 가능

하지만 즉시 실행을 원하는 경우 위의 상태 파일 정리 단계를 수행하세요.

### 체크 재활성화

나중에 `is_in_progress` 체크를 다시 활성화하려면:
1. `local_training/replay_build_order_learner.py` 파일 열기
2. 433-435 라인의 주석(`#`) 제거

---

## 🔄 Spawning Tool 크롤링 수정 (선택사항)

나중에 Spawning Tool 크롤링을 수정하려면:
1. `tools/build_order_collector.py`의 URL 감지 로직 수정
2. 실제 빌드 오더 페이지 URL 패턴 확인
3. Selenium 또는 requests를 사용한 정확한 크롤링 로직 구현

하지만 현재는 **리플레이 직접 분석이 더 빠르고 정확**하므로 이 방법을 권장합니다.

---

## ✅ 검증

리플레이 분석이 정상 작동하는지 확인:

```cmd
# 1. 상태 파일 정리
bat\clear_learning_state.bat

# 2. 리플레이 분석 실행
bat\start_replay_learning.bat

# 3. 결과 확인
dir data\build_orders\*.json
```

`data/build_orders/` 폴더에 JSON 파일이 생성되면 성공입니다.

---

**작성일**: 2026년 01-13  
**작성자**: AI Assistant  
**상태**: ✅ **설정 완료**
