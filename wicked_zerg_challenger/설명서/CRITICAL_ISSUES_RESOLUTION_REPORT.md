# 핵심 문제점 해결 보고서

**작성 일시**: 2026년 01-13  
**검토 범위**: 리플레이 학습 파이프라인 완성도 및 시스템 안정성  
**목적**: 사용자 지적 핵심 문제점 해결

---

## ? 발견된 핵심 문제점

### 1. 학습 횟수 카운팅 및 라이프사이클 관리 결함 ??

**문제점**: "리플레이당 최소 5번 학습" 조건이 코드 레벨에서 명확하게 강제되지 않음

**현재 상태**:
- ? `ReplayLearningTracker` 클래스 존재 (`local_training/scripts/replay_learning_manager.py`)
- ? `.learning_tracking.json` 파일로 학습 횟수 추적
- ?? 학습 파이프라인에서 강제적으로 카운팅이 적용되지 않을 수 있음

**해결 방안**:
- 학습 파이프라인에서 학습 횟수를 **반드시** 증가시키도록 강제
- `replay_lifecycle_manager.py`에서 5회 미만인 파일은 **절대** 이동/삭제하지 않도록 보강

---

### 2. 신경망 입력 정보의 불균형 ? (부분 해결)

**문제점**: 신경망 입력 벡터가 자신의 상태 정보에만 편중

**현재 상태**:
- ? `ZergNet` 클래스: `input_size=10` (기본값)
- ? `_collect_state()` 메서드: 10차원 벡터 반환
  - Self (5): Minerals, Gas, Supply, Workers, Army
  - Enemy (5): Enemy Army Count, Tech Level, Threat Level, Unit Diversity, Scout Coverage
- ?? 실제 학습 시 10차원이 제대로 사용되는지 검증 필요

**해결 방안**:
- `_collect_state()` 메서드가 항상 10차원을 반환하는지 검증
- `IntelManager`의 적 정보 수집이 제대로 작동하는지 확인

---

### 3. 병렬 실행 시 파일 시스템 충돌 ? (부분 해결)

**문제점**: 여러 봇 인스턴스가 동시에 상태 파일에 쓰기 시도

**현재 상태**:
- ? `main_integrated.py`: Atomic file writing 구현 (임시 파일 + `os.replace`)
- ? `wicked_zerg_bot_pro.py`: Atomic file writing 구현
- ? `stats/` 폴더 통일 (루트)
- ?? 모든 상태 파일 쓰기에 atomic writing이 적용되었는지 확인 필요

**해결 방안**:
- 모든 상태 파일 쓰기에 atomic writing 적용 확인
- 파일 잠금 오류 처리 강화

---

### 4. 연산 병목 구간 ? (부분 해결)

**문제점**: 전투 유닛 타겟 선정 로직의 성능 저하

**현재 상태**:
- ? `_select_priority_target`: `closer_than` API 사용
- ? `_check_and_defend_with_workers`: `closer_than` API 활용 강화
- ?? 다른 함수들도 최적화 필요할 수 있음

**해결 방안**:
- 모든 거리 계산에 `closer_than` API 우선 사용
- 불필요한 거리 계산 제거

---

### 5. 폴더 구조의 복잡성 및 중복 스크립트 ??

**문제점**: 유사한 기능의 스크립트가 여러 폴더에 흩어져 있음

**현재 상태**:
- ?? `local_training/scripts/`에 관리 스크립트와 봇 실행 스크립트 혼재
- ?? `tools/`와 `local_training/scripts/`에 중복 기능 가능성

**해결 방안**:
- 관리 스크립트를 `tools/`로 이동
- 봇 실행 스크립트만 `local_training/scripts/`에 유지

---

## ? 해결 작업 계획

### 우선순위 1: 학습 횟수 카운팅 강제 (최우선)

1. **`replay_build_order_learner.py` 수정**:
   - 학습 시작 시 `ReplayLearningTracker.increment_learning_count()` **반드시** 호출
   - 학습 완료 후 카운트 확인

2. **`replay_lifecycle_manager.py` 보강**:
   - 5회 미만인 파일은 **절대** 이동/삭제하지 않도록 명확히 구현
   - 경고 메시지 출력

### 우선순위 2: 신경망 입력 검증

1. **`wicked_zerg_bot_pro.py` 검증**:
   - `_collect_state()`가 항상 10차원을 반환하는지 확인
   - `IntelManager` 정보 수집 검증

2. **`zerg_net.py` 검증**:
   - `_normalize_state()`가 10차원을 올바르게 처리하는지 확인

### 우선순위 3: 파일 충돌 방지 강화

1. **모든 상태 파일 쓰기 검토**:
   - Atomic writing 적용 확인
   - 파일 잠금 오류 처리 강화

### 우선순위 4: 연산 최적화

1. **`combat_manager.py` 추가 최적화**:
   - 모든 거리 계산에 `closer_than` API 우선 사용
   - 불필요한 계산 제거

### 우선순위 5: 폴더 구조 정리

1. **스크립트 분리**:
   - 관리 스크립트 → `tools/`
   - 봇 실행 스크립트 → `local_training/scripts/` 유지

---

**작성일**: 2026년 01-13  
**작성자**: AI Assistant  
**상태**: ?? **해결 작업 진행 중**
