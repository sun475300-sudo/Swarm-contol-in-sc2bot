# Archive Paths Explanation

**작성 일시**: 2026-01-14  
**상태**: ? **설명 완료**

---

## ? 두 경로의 차이점

### 1. `wicked_zerg_challenger/replays_archive/`

**위치**: 프로젝트 내부 폴더  
**경로**: `D:\Swarm-contol-in-sc2bot\Swarm-contol-in-sc2bot\wicked_zerg_challenger\replays_archive`

**용도**:
- **Fallback 경로**: `D:/replays/replays`가 없을 때 사용되는 대체 경로
- **레거시 데이터**: 과거 훈련에서 생성된 상태 파일들
- **우선순위**: 낮음 (fallback only)

**내용**:
- `training_YYYYMMDD_HHMMSS/` 폴더들
- 각 폴더 내부:
  - `instance_0_status.json` - 게임 인스턴스 상태
  - `instance_1_status.json` - 게임 인스턴스 상태
  - `instance_2_status.json` - 게임 인스턴스 상태
  - `supervised_training_stats.json` - 감독 학습 통계

**특징**:
- 프로젝트와 함께 버전 관리됨 (Git)
- 주로 게임 실행 상태 추적용
- 약 44개의 훈련 폴더 존재

---

### 2. `D:/replays/archive/`

**위치**: 외부 독립 경로  
**경로**: `D:\replays\archive`

**용도**:
- **주요 출력 경로**: 리플레이 학습 결과를 저장하는 메인 위치
- **학습된 파라미터**: 빌드오더 학습 결과 저장
- **우선순위**: 높음 (primary output location)

**내용**:
- `training_YYYYMMDD_HHMMSS/` 폴더들
- 각 폴더 내부:
  - `learned_build_orders.json` - 학습된 빌드오더 파라미터
    - `learned_parameters`: 학습된 타이밍 파라미터
    - `source_replays`: 학습에 사용된 리플레이 수
    - `replay_directory`: 원본 리플레이 경로
    - `build_orders`: 추출된 빌드오더 샘플 (최대 10개)

**특징**:
- 프로젝트와 독립적인 외부 경로
- 리플레이 학습 결과 전용
- 약 8개의 훈련 폴더 존재 (최근 학습 결과)

---

## ? 사용 흐름

### 리플레이 학습 시:

1. **입력**: `D:/replays/replays` (리플레이 파일 소스)
2. **처리**: `replay_build_order_learner.py`가 빌드오더 추출
3. **출력**: `D:/replays/archive/training_YYYYMMDD_HHMMSS/learned_build_orders.json`

### 게임 훈련 시:

1. **입력**: `D:/replays/replays` (리플레이 파일 소스)
2. **처리**: `main_integrated.py`가 게임 실행 및 학습
3. **출력**: 
   - `wicked_zerg_challenger/replays_archive/` (게임 상태 추적)
   - `D:/replays/archive/` (학습 결과 - 최신 코드)

---

## ? 코드에서의 사용

### `replay_build_order_learner.py`:

```python
# 입력 경로 (우선순위)
possible_paths = [
    Path("D:/replays/replays"),  # 최우선
    Path(__file__).parent.parent / "replays_archive",  # Fallback
    # ...
]

# 출력 경로
archive_dir = Path("D:/replays/archive") / f"training_{timestamp}"
output_path = archive_dir / "learned_build_orders.json"
```

### `main_integrated.py`:

```python
# 입력 경로 (우선순위)
possible_paths = [
    Path("D:/replays/replays"),  # 최우선
    Path(__file__).parent.parent / "replays_archive",  # Fallback
    # ...
]
```

---

## ? 요약

| 항목 | `replays_archive/` | `D:/replays/archive/` |
|------|-------------------|---------------------|
| **위치** | 프로젝트 내부 | 외부 독립 경로 |
| **용도** | Fallback 경로, 게임 상태 추적 | 리플레이 학습 결과 저장 |
| **내용** | `instance_*_status.json` | `learned_build_orders.json` |
| **우선순위** | 낮음 (fallback) | 높음 (primary) |
| **Git 관리** | 예 (프로젝트와 함께) | 아니오 (외부 경로) |
| **폴더 수** | 약 44개 | 약 8개 |

---

## ? 권장 사항

1. **리플레이 학습 결과**: `D:/replays/archive/` 사용 (현재 활성)
2. **프로젝트 내부**: `replays_archive/`는 레거시 데이터이므로 정리 가능
3. **새로운 학습**: 항상 `D:/replays/archive/`에 저장됨

---

**결론**: 두 경로는 서로 다른 용도로 사용되며, 현재는 `D:/replays/archive/`가 리플레이 학습 결과의 주요 저장 위치입니다.
