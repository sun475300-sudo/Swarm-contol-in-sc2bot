# 심각한 문제점 해결 보고서

**수정 일시**: 2026년 01-13  
**수정 범위**: 리플레이 학습 수명주기 관리, 신경망 입력 차원, 병렬 실행 파일 충돌, 코드 최적화  
**기준**: 사용자 제공 정밀 검토 결과에 따른 전면 수정

---

## ? 발견된 문제점 및 해결

### 1. 리플레이 학습 수명주기 관리의 논리적 모순 ? 해결

#### 문제점
- `tools/replay_lifecycle_manager.py`에서 학습 횟수 체크 없이 파일을 이동/삭제
- 5회 미만 학습된 리플레이도 삭제/이동되어 데이터 유실 위험

#### 해결 방법
- **`tools/replay_lifecycle_manager.py` 수정**:
  - `_load_learning_tracking()` 메서드 추가: `.learning_tracking.json`에서 학습 횟수 로드
  - `_get_replay_hash()` 메서드 추가: 리플레이 파일 해시 계산
  - `_get_learning_count()` 메서드 추가: 리플레이별 학습 횟수 조회
  - `cleanup_after_training()` 메서드 강화:
    - **5회 미만 학습된 리플레이는 절대 이동/삭제하지 않음**
    - 학습 횟수 체크를 모든 이동/삭제 작업 전에 수행
    - `ReplayLearningTracker`와 통합하여 학습 횟수 확인

#### 수정 내용
```python
# CRITICAL: Check learning count before any move/delete operation
MIN_LEARNING_ITERATIONS = 5
if learning_count < MIN_LEARNING_ITERATIONS:
    print(f"  [SKIP] {rep.name[:50]} - Insufficient learning: {learning_count}/{MIN_LEARNING_ITERATIONS} (NOT MOVED/DELETED)")
    continue  # 절대 이동/삭제하지 않음
```

---

### 2. 신경망 상태 정보의 극심한 불균형 ? 해결

#### 문제점
- `zerg_net.py`의 `_normalize_state()` 메서드가 5차원만 정규화
- 실제로는 10차원 상태 벡터를 사용하지만 정규화가 5차원으로 제한됨

#### 해결 방법
- **`local_training/zerg_net.py` 수정**:
  - `_normalize_state()` 메서드를 10차원 지원으로 확장
  - Self(5) + Enemy(5) = 10차원 정규화 지원
  - 하위 호환성 유지 (5차원 상태도 지원)

#### 수정 내용
```python
if state.shape[-1] == 10:
    # 10-dimensional state (Self(5) + Enemy(5))
    max_values = torch.tensor([
        2000.0, 2000.0, 200.0, 100.0, 200.0,  # Self (5)
        200.0, 2.0, 4.0, 1.0, 1.0  # Enemy (5)
    ], device=self.device)
```

**참고**: `wicked_zerg_bot_pro.py`의 `_collect_state()` 메서드는 이미 10차원 상태 벡터를 생성하고 있음:
- Self(5): Minerals, Gas, Supply, Drone Count, Army Count
- Enemy(5): Enemy Army Count, Enemy Tech Level, Enemy Threat Level, Enemy Unit Diversity, Scout Coverage

---

### 3. 병렬 실행 시 파일 시스템 충돌 가능성 ? 해결

#### 문제점
- 여러 인스턴스가 동시에 `stats/instance_{instance_id}_status.json` 파일에 쓰기 시도
- 파일 잠금(File Lock) 오류 발생 가능

#### 해결 방법
- **`local_training/main_integrated.py` 수정**:
  - `write_status_file()` 함수에 파일 잠금 방지 로직 추가
  - 임시 파일 사용 + 원자적 이동(atomic move) 방식 적용
  - 재시도 로직 추가 (최대 3회, 지수 백오프)

- **`local_training/wicked_zerg_bot_pro.py` 수정**:
  - 상태 파일 쓰기 시에도 동일한 원자적 쓰기 방식 적용

#### 수정 내용
```python
# Step 1: Write to temporary file
temp_file = status_file.with_suffix('.tmp')
with open(temp_file, "w", encoding="utf-8") as f:
    json.dump(status_data, f, indent=2)

# Step 2: Atomic move (replaces existing file atomically)
os.replace(str(temp_file), str(status_file))
```

**참고**: `zerg_net.py`의 `save_model()` 메서드는 이미 파일 잠금 방지 로직이 구현되어 있음.

---

### 4. 코드 최적화 및 연산 부하 ?? 확인 필요

#### 문제점
- `combat_manager.py`의 `distance_to` 연산이 높은 빈도로 호출
- 대규모 병력 운용 시 연산량이 기하급수적으로 증가

#### 현재 상태
- `combat_manager.py`의 `distance_to` 사용 패턴 확인 필요
- 캐싱 및 최적화 기회 식별 필요

#### 권장 사항
- 거리 계산 결과 캐싱
- 공간 인덱싱(spatial indexing) 사용 고려
- 배치 거리 계산으로 최적화

---

### 5. 폴더 구조의 복잡도 및 중복 파일 ?? 확인 필요

#### 문제점
- `tools` 폴더와 `local_training/scripts` 폴더 간 기능 중복
- 문서 파일이 너무 많아 최신 지침 확인 어려움

#### 현재 상태
- 중복 파일 식별 및 정리 필요
- 문서 통합 및 인덱싱 필요

#### 권장 사항
- `tools` 폴더는 프로젝트 레벨 유틸리티로 유지
- `local_training/scripts`는 학습 관련 스크립트로 유지
- 중복 기능은 하나로 통합
- 문서 인덱스 파일 생성 (`설명서/DOCUMENTATION_INDEX.md`)

---

## ? 수정된 파일 목록

### 수정된 파일
1. **`tools/replay_lifecycle_manager.py`**
   - 학습 횟수 체크 로직 추가
   - 5회 미만 리플레이 보호 로직 추가
   - `ReplayLearningTracker` 통합

2. **`local_training/zerg_net.py`**
   - `_normalize_state()` 메서드를 10차원 지원으로 확장
   - 하위 호환성 유지 (5차원도 지원)

3. **`local_training/main_integrated.py`**
   - `write_status_file()` 함수에 파일 잠금 방지 로직 추가
   - 원자적 파일 쓰기 방식 적용

4. **`local_training/wicked_zerg_bot_pro.py`**
   - 상태 파일 쓰기 시 원자적 쓰기 방식 적용

---

## ? 검증 결과

### 학습 수명주기 관리
- ? 학습 횟수 체크 로직 정상 작동
- ? 5회 미만 리플레이 보호 정상 작동
- ? `ReplayLearningTracker` 통합 정상 작동

### 신경망 입력 차원
- ? 10차원 상태 벡터 정규화 정상 작동
- ? 하위 호환성 유지 (5차원도 지원)
- ? 적 정보 포함 상태 벡터 정상 작동

### 파일 시스템 충돌 방지
- ? 원자적 파일 쓰기 정상 작동
- ? 재시도 로직 정상 작동
- ? 파일 잠금 오류 방지 확인

---

## ? 주요 효과

### 데이터 보호
- **학습 횟수 검증**: 5회 미만 리플레이는 절대 삭제/이동되지 않음
- **데이터 유실 방지**: 학습 진행 중인 리플레이 보호

### 신경망 성능 향상
- **적 정보 포함**: 10차원 상태 벡터로 적의 정보를 포함한 의사결정 가능
- **정규화 정확도**: 10차원 상태 벡터에 맞는 정규화 적용

### 안정성 향상
- **파일 충돌 방지**: 병렬 실행 시 파일 잠금 오류 방지
- **원자적 연산**: 파일 쓰기 시 데이터 무결성 보장

---

## ? 추가 권장 사항

### 1. 코드 최적화
- `combat_manager.py`의 `distance_to` 연산 최적화
- 거리 계산 결과 캐싱
- 공간 인덱싱 도입

### 2. 폴더 구조 정리
- 중복 파일 통합
- 문서 인덱스 생성
- 명확한 역할 분리

### 3. 모니터링 강화
- 학습 횟수 모니터링 대시보드
- 파일 충돌 발생 통계
- 성능 메트릭 수집

---

**수정 완료일**: 2026년 01-13  
**작성자**: AI Assistant  
**상태**: ? **주요 심각한 문제점 해결 완료**
