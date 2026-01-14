# 파일 배치 오류 정밀 검토 보고서

**작성 일시**: 2026년 01-13  
**검토 범위**: `wicked_zerg_challenger`와 `local_training` 폴더의 파일 배치  
**상태**: ? **심각한 파일 배치 오류 발견 (28개 파일 이동 필요)**

---

## ? 폴더별 역할 정의

### A. `wicked_zerg_challenger` (프로젝트 루트: 관리 및 인프라)

**역할**: AI의 '몸체' - 외부 인터페이스 및 전체 공정 제어

**포함해야 할 파일/폴더**:
```
wicked_zerg_challenger/
├── bat/                    # 모든 실행 스크립트 (.bat, .sh, .ps1)
├── tools/                  # 관리 유틸리티
│   ├── replay_lifecycle_manager.py
│   ├── auto_downloader.py
│   ├── ZergOps_Pipeline.py
│   └── ... (관리 스크립트들)
├── monitoring/             # 모니터링 시스템
├── 설명서/                 # 프로젝트 전체 문서
├── stats/                  # 상태 파일 통합 저장소
├── replays_archive/        # 완료된 리플레이
├── requirements.txt
├── pyrightconfig.json
└── pyproject.toml (선택)
```

---

### B. `local_training` (핵심 로직: 게임 AI 엔진)

**역할**: AI의 '두뇌' - 실제 스타2 게임 내 순수 로직

**포함해야 할 파일/폴더**:
```
local_training/
├── wicked_zerg_bot_pro.py  # 메인 봇
├── main_integrated.py      # 통합 실행
├── zerg_net.py             # 신경망 (15차원 입력)
├── combat_manager.py       # 전투 관리
├── economy_manager.py       # 경제 관리
├── intel_manager.py         # 정보 관리
├── production_manager.py    # 생산 관리
├── ... (기타 매니저들)
├── replay_build_order_learner.py  # 학습 로직
├── scripts/                 # 봇 실행 중 사용 스크립트만
│   ├── replay_learning_manager.py
│   ├── learning_logger.py
│   ├── strategy_database.py
│   ├── replay_quality_filter.py
│   ├── parallel_train_integrated.py
│   ├── run_hybrid_supervised.py
│   ├── learning_status_manager.py
│   └── replay_crash_handler.py
├── models/                  # 학습된 모델 (.pt)
├── data/                    # 학습 데이터
│   └── build_orders/       # 추출된 빌드 JSON
└── 설명서/                  # local_training 로직 문서
```

---

## ? 발견된 심각한 문제점

### 문제 1: `local_training/scripts/`에 관리 스크립트 20개 혼재 ??

#### 잘못 배치된 파일 (→ `tools/`로 이동 필요)

**정리/관리 스크립트** (13개):
1. ? `cleanup_analysis.py` - 프로젝트 정리 분석
2. ? `cleanup_entire_project.py` - 프로젝트 전체 정리
3. ? `cleanup_unnecessary.py` - 불필요 파일 정리
4. ? `code_check.py` - 코드 검사
5. ? `organize_file_structure.py` - 파일 구조 정리
6. ? `verify_structure.py` - 구조 검증
7. ? `move_backup_files.py` - 백업 파일 이동
8. ? `move_md_files.py` - MD 파일 이동
9. ? `check_md_duplicates.py` - MD 중복 검사
10. ? `fast_code_inspector.py` - 코드 검사
11. ? `local_hidden_gems.py` - 코드 분석
12. ? `enhanced_replay_downloader.py` - 리플레이 다운로더
13. ? `optimize_local_training.py` - 로컬 훈련 최적화

**최적화 스크립트** (2개):
14. ? `optimize_code.py` - 코드 최적화 ?? (봇에서 import)
15. ? `optimize_training_root.py` - 훈련 루트 최적화

**다운로드/학습 스크립트** (1개):
16. ? `download_and_train.py` - 리플레이 다운로드 및 학습 ?? (봇에서 import)

**테스트 스크립트** (4개):
17. ? `test_basic_imports.py` - 기본 import 테스트
18. ? `test_config.py` - 설정 테스트
19. ? `test_integration.py` - 통합 테스트
20. ? `test_path_detection.py` - 경로 감지 테스트

**총 20개 파일 이동 필요**

---

### 문제 2: 루트에 배치 파일 분산 ??

#### 잘못 배치된 파일 (→ `bat/`로 이동 필요)

1. ? `build_order_setup.bat` → `bat/build_order_setup.bat`
2. ? `prepare_monsterbot.sh` → `bat/prepare_monsterbot.sh`
3. ? `start_continuous_improvement.sh` → `bat/start_continuous_improvement.sh`
4. ? `start_training.sh` → `bat/start_training.sh`
5. ? `start_wicked_cline.sh` → `bat/start_wicked_cline.sh`
6. ? `train_3h_shutdown.ps1` → `bat/train_3h_shutdown.ps1`

**총 6개 파일 이동 필요**

---

### 문제 3: 설정 파일 위치 오류 ??

1. ? `local_training/scripts/pyproject.toml`
   - 현재: `local_training/scripts/`
   - 권장: 루트 또는 `local_training/`
   - 문제: `scripts/`는 봇 실행 스크립트만 있어야 함

2. ? `local_training/scripts/requirements.txt`
   - 현재: `local_training/scripts/`
   - 권장: 루트 `requirements.txt`와 통합 또는 삭제
   - 문제: 중복 가능성

**총 2개 파일 이동/통합 필요**

---

### 문제 4: Import 의존성 문제 ????

#### 발견된 Import 의존성

1. **`main_integrated.py` → `scripts.optimize_code`** (라인 457)
   ```python
   from scripts.optimize_code import remove_korean_comments
   ```
   - 문제: `optimize_code.py`는 관리 스크립트인데 봇에서 import
   - 영향: 파일 이동 시 import 경로 수정 필요
   - 해결: `tools/`로 이동 후 import 경로 수정 또는 제거

2. **`main_integrated.py` → `scripts.download_and_train`** (라인 1010)
   ```python
   from scripts.download_and_train import ReplayDownloader
   ```
   - 문제: `download_and_train.py`는 관리 스크립트인데 봇에서 import
   - 영향: 파일 이동 시 import 경로 수정 필요
   - 해결: `tools/`로 이동 후 import 경로 수정 또는 제거

3. **`download_and_train.py` → `scripts.replay_quality_filter`** (라인 48)
   ```python
   from scripts.replay_quality_filter import ReplayQualityFilter
   from scripts.strategy_database import StrategyDatabase
   ```
   - 문제: `download_and_train.py`가 봇 실행 스크립트를 import
   - 영향: `download_and_train.py`를 `tools/`로 이동하면 import 경로 수정 필요
   - 해결: `tools/`로 이동 후 `from local_training.scripts.`로 경로 수정

---

## ? 정리 작업 계획

### 1단계: Import 의존성 있는 파일 처리 (최우선)

#### `optimize_code.py` 처리
- **현재 위치**: `local_training/scripts/`
- **이동 위치**: `tools/`
- **작업**:
  1. 파일 이동: `local_training/scripts/optimize_code.py` → `tools/optimize_code.py`
  2. Import 수정: `main_integrated.py` 라인 457
     ```python
     # 이전
     from scripts.optimize_code import remove_korean_comments
     
     # 수정 후
     from tools.optimize_code import remove_korean_comments
     # 또는 제거 (자동 최적화가 필요 없다면)
     ```

#### `download_and_train.py` 처리
- **현재 위치**: `local_training/scripts/`
- **이동 위치**: `tools/`
- **작업**:
  1. 파일 이동: `local_training/scripts/download_and_train.py` → `tools/download_and_train.py`
  2. Import 수정: `main_integrated.py` 라인 1010
     ```python
     # 이전
     from scripts.download_and_train import ReplayDownloader
     
     # 수정 후
     from tools.download_and_train import ReplayDownloader
     ```
  3. 내부 import 수정: `download_and_train.py` 라인 48-49
     ```python
     # 이전
     from scripts.replay_quality_filter import ReplayQualityFilter
     from scripts.strategy_database import StrategyDatabase
     
     # 수정 후
     from local_training.scripts.replay_quality_filter import ReplayQualityFilter
     from local_training.scripts.strategy_database import StrategyDatabase
     ```

---

### 2단계: 관리 스크립트 일괄 이동

**18개 파일을 `local_training/scripts/` → `tools/`로 이동**:

```
cleanup_analysis.py
cleanup_entire_project.py
cleanup_unnecessary.py
code_check.py
enhanced_replay_downloader.py
optimize_local_training.py
optimize_training_root.py
organize_file_structure.py
verify_structure.py
move_backup_files.py
move_md_files.py
check_md_duplicates.py
test_basic_imports.py
test_config.py
test_integration.py
test_path_detection.py
fast_code_inspector.py
local_hidden_gems.py
```

---

### 3단계: 배치 파일 통합

**6개 파일을 루트 → `bat/`로 이동**:

```
build_order_setup.bat
prepare_monsterbot.sh
start_continuous_improvement.sh
start_training.sh
start_wicked_cline.sh
train_3h_shutdown.ps1
```

---

### 4단계: 설정 파일 정리

1. **`local_training/scripts/pyproject.toml`**
   - 이동: 루트 또는 `local_training/`
   - 권장: 루트 (프로젝트 전체 설정)

2. **`local_training/scripts/requirements.txt`**
   - 통합: 루트 `requirements.txt`와 비교 후 통합 또는 삭제

---

## ? 최종 정리 요약

### 이동 필요 파일 수

| 카테고리 | 파일 수 | 대상 폴더 | 우선순위 |
|---------|--------|----------|---------|
| Import 의존성 있는 파일 | 2개 | `tools/` | ???? 최우선 |
| 관리 스크립트 | 18개 | `tools/` | ?? 높음 |
| 배치 파일 | 6개 | `bat/` | ?? 중간 |
| 설정 파일 | 2개 | 루트/통합 | ?? 낮음 |
| **총계** | **28개** | - | - |

### Import 경로 수정 필요

| 파일 | 수정 필요 import | 우선순위 |
|------|-----------------|---------|
| `main_integrated.py` | `scripts.optimize_code` → `tools.optimize_code` | ???? 최우선 |
| `main_integrated.py` | `scripts.download_and_train` → `tools.download_and_train` | ???? 최우선 |
| `tools/download_and_train.py` | `scripts.*` → `local_training.scripts.*` | ?? 높음 |

---

## ? 검증 체크리스트

### 파일 배치 검증
- [x] ? 관리 스크립트가 `tools/`에 있는지 확인
- [x] ? 봇 실행 스크립트만 `local_training/scripts/`에 있는지 확인
- [x] ? 배치 파일이 `bat/`에 통합되어 있는지 확인
- [x] ? 설정 파일이 적절한 위치에 있는지 확인

### Import 경로 검증
- [x] ? `main_integrated.py`의 import 경로 수정
- [x] ? `download_and_train.py` 이동 후 import 경로 수정
- [x] ? `optimize_code.py` 이동 후 import 경로 수정

---

**분석 완료일**: 2026년 01-13  
**작성자**: AI Assistant  
**상태**: ? **파일 정리 완료 - `FILE_ORGANIZATION_FINAL_SUMMARY.md` 참조**

---

## ? 정리 작업 완료 상태

### 완료된 작업

1. ? **Import 의존성 있는 파일 처리 완료**
   - `optimize_code.py`: `local_training/scripts/` → `tools/` 이동 완료
   - `download_and_train.py`: `local_training/scripts/` → `tools/` 이동 완료
   - `main_integrated.py` import 경로 수정 완료

2. ? **관리 스크립트 20개 이동 완료**
   - 모든 관리 스크립트가 `tools/`로 이동 완료

3. ? **배치 파일 6개 통합 완료**
   - 모든 배치 파일이 `bat/`로 이동 완료

4. ? **설정 파일 정리 완료**
   - `pyproject.toml`: 루트로 이동 완료
   - `requirements.txt`: 중복 파일 삭제 완료

### 최종 상태

- **총 28개 파일 이동 완료**
- **3개 import 경로 수정 완료**
- **구문 검증 통과**

자세한 내용은 `FILE_ORGANIZATION_FINAL_SUMMARY.md`를 참조하세요.
