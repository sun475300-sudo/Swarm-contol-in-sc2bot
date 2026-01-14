# 파일 배치 오류 분석 보고서

**작성 일시**: 2026년 01-13  
**분석 범위**: `wicked_zerg_challenger`와 `local_training` 폴더의 파일 배치 오류  
**상태**: ? **파일 정리 완료 - 모든 문제 해결됨**

> **참고**: 이 문서는 초기 분석 보고서입니다. 정리 작업 완료 상태는 아래에 업데이트되어 있으며, 상세한 완료 보고서는 `FILE_ORGANIZATION_COMPLETE_REPORT.md`를 참조하세요.

---

## ? 폴더별 올바른 파일 배치 기준

### A. `wicked_zerg_challenger` (프로젝트 루트)

**역할**: 관리, 자동화, 인프라

**포함해야 할 파일**:
- ? 배치 파일: `bat/` 폴더 (모든 `.bat`, `.sh`, `.ps1`)
- ? 환경 설정: `.gitignore`, `requirements.txt`, `pyrightconfig.json`
- ? 관리 도구: `tools/` 폴더
- ? 모니터링: `monitoring/` 폴더
- ? 문서: `설명서/` 폴더
- ? 상태 파일: `stats/` 폴더

---

### B. `local_training` (핵심 로직)

**역할**: 게임 AI 엔진 및 모델

**포함해야 할 파일**:
- ? 메인 실행: `wicked_zerg_bot_pro.py`, `main_integrated.py`
- ? 매니저 모듈: `combat_manager.py`, `economy_manager.py` 등
- ? 신경망: `zerg_net.py`
- ? 학습 로직: `replay_build_order_learner.py`
- ? 봇 실행 스크립트: `scripts/` 폴더 (봇이 import하는 스크립트만)
- ? 모델/데이터: `models/`, `data/`

---

## ? 정리 작업 완료 상태

### 문제 1: `local_training/scripts/`에 관리 스크립트 혼재 → ? 해결 완료

#### 이동 완료된 파일 목록

| 파일명 | 이전 위치 | 현재 위치 | 상태 | Import 의존성 |
|--------|----------|----------|------|---------------|
| `cleanup_analysis.py` | `local_training/scripts/` | `tools/` | ? 이동 완료 | 없음 |
| `cleanup_entire_project.py` | `local_training/scripts/` | `tools/` | ? 이동 완료 | 없음 |
| `cleanup_unnecessary.py` | `local_training/scripts/` | `tools/` | ? 이동 완료 | 없음 |
| `code_check.py` | `local_training/scripts/` | `tools/` | ? 이동 완료 | 없음 |
| `download_and_train.py` | `local_training/scripts/` | `tools/` | ? 이동 완료 | ? `main_integrated.py` import 경로 수정 완료 |
| `enhanced_replay_downloader.py` | `local_training/scripts/` | `tools/` | ? 이동 완료 | 없음 |
| `optimize_code.py` | `local_training/scripts/` | `tools/` | ? 이동 완료 | ? `main_integrated.py` import 경로 수정 완료 |
| `optimize_local_training.py` | `local_training/scripts/` | `tools/` | ? 이동 완료 | 없음 |
| `optimize_training_root.py` | `local_training/scripts/` | `tools/` | ? 이동 완료 | 없음 |
| `organize_file_structure.py` | `local_training/scripts/` | `tools/` | ? 이동 완료 | 없음 |
| `verify_structure.py` | `local_training/scripts/` | `tools/` | ? 이동 완료 | 없음 |
| `move_backup_files.py` | `local_training/scripts/` | `tools/` | ? 이동 완료 | 없음 |
| `move_md_files.py` | `local_training/scripts/` | `tools/` | ? 이동 완료 | 없음 |
| `check_md_duplicates.py` | `local_training/scripts/` | `tools/` | ? 이동 완료 | 없음 |
| `test_basic_imports.py` | `local_training/scripts/` | `tools/` | ? 이동 완료 | 없음 |
| `test_config.py` | `local_training/scripts/` | `tools/` | ? 이동 완료 | 없음 |
| `test_integration.py` | `local_training/scripts/` | `tools/` | ? 이동 완료 | 없음 |
| `test_path_detection.py` | `local_training/scripts/` | `tools/` | ? 이동 완료 | 없음 |
| `fast_code_inspector.py` | `local_training/scripts/` | `tools/` | ? 이동 완료 | 없음 |
| `local_hidden_gems.py` | `local_training/scripts/` | `tools/` | ? 이동 완료 | 없음 |

**총 20개 파일 이동 완료**

#### 올바르게 배치된 파일 (유지)

| 파일명 | 현재 위치 | 상태 | 봇에서 import 여부 |
|--------|----------|------|-------------------|
| `replay_learning_manager.py` | `local_training/scripts/` | ? | ? `replay_build_order_learner.py` |
| `learning_logger.py` | `local_training/scripts/` | ? | ? `replay_build_order_learner.py` |
| `strategy_database.py` | `local_training/scripts/` | ? | ? `replay_build_order_learner.py` |
| `replay_quality_filter.py` | `local_training/scripts/` | ? | ? `download_and_train.py` |
| `parallel_train_integrated.py` | `local_training/scripts/` | ? | ? 직접 실행 |
| `run_hybrid_supervised.py` | `local_training/scripts/` | ? | ? 직접 실행 |
| `learning_status_manager.py` | `local_training/scripts/` | ? | ? `replay_build_order_learner.py` |
| `replay_crash_handler.py` | `local_training/scripts/` | ? | ? `replay_build_order_learner.py` |

---

### 문제 2: 루트에 배치 파일 분산 → ? 해결 완료

#### 이동 완료된 파일

| 파일명 | 이전 위치 | 현재 위치 | 상태 |
|--------|----------|----------|------|
| `build_order_setup.bat` | 루트 | `bat/` | ? 이동 완료 |
| `prepare_monsterbot.sh` | 루트 | `bat/` | ? 이동 완료 |
| `start_continuous_improvement.sh` | 루트 | `bat/` | ? 이동 완료 |
| `start_training.sh` | 루트 | `bat/` | ? 이동 완료 |
| `start_wicked_cline.sh` | 루트 | `bat/` | ? 이동 완료 |
| `train_3h_shutdown.ps1` | 루트 | `bat/` | ? 이동 완료 |

**총 6개 파일 이동 완료**

---

### 문제 3: 설정 파일 중복/위치 오류 → ? 해결 완료

#### 정리 완료된 파일

1. **`pyproject.toml`**
   - 이전 위치: `local_training/scripts/`
   - 현재 위치: 루트 `pyproject.toml`
   - 상태: ? 이동 완료

2. **`requirements.txt`**
   - 이전 위치: `local_training/scripts/` (중복)
   - 현재 위치: 삭제됨 (루트 `requirements.txt` 유지)
   - 상태: ? 중복 파일 삭제 완료

---

### 문제 4: Import 의존성 문제 → ? 해결 완료

#### 수정 완료된 Import 경로

1. **`main_integrated.py` → `tools.optimize_code`** (라인 454)
   - 이전: `from scripts.optimize_code import remove_korean_comments`
   - 현재: `from tools.optimize_code import remove_korean_comments`
   - 상태: ? 수정 완료

2. **`main_integrated.py` → `tools.download_and_train`** (라인 991)
   - 이전: `from scripts.download_and_train import ReplayDownloader`
   - 현재: `from tools.download_and_train import ReplayDownloader`
   - 상태: ? 수정 완료

3. **`tools/download_and_train.py` → `local_training.scripts.*`** (라인 48-49)
   - 이전: `from scripts.replay_quality_filter import ...`
   - 현재: `from local_training.scripts.replay_quality_filter import ...`
   - 상태: ? 수정 완료

---

## ? 정리 작업 완료 상태

### ? 우선순위 1: Import 의존성 있는 파일 처리 완료

1. **`download_and_train.py`**
   - 이동: `local_training/scripts/` → `tools/` ?
   - Import 수정: `main_integrated.py` 라인 991 ?

2. **`optimize_code.py`**
   - 이동: `local_training/scripts/` → `tools/` ?
   - Import 수정: `main_integrated.py` 라인 454 ?

### ? 우선순위 2: 관리 스크립트 일괄 이동 완료

**20개 파일을 `local_training/scripts/` → `tools/`로 이동 완료**:
- `cleanup_*.py` (3개) ?
- `optimize_*.py` (3개) ?
- `test_*.py` (4개) ?
- `move_*.py` (2개) ?
- `check_*.py` (1개) ?
- `organize_*.py` (1개) ?
- `verify_*.py` (1개) ?
- `fast_code_inspector.py` (1개) ?
- `local_hidden_gems.py` (1개) ?
- `enhanced_replay_downloader.py` (1개) ?
- `code_check.py` (1개) ?
- `download_and_train.py` (1개) ?
- `optimize_code.py` (1개) ?

### ? 우선순위 3: 배치 파일 통합 완료

**6개 파일을 루트 → `bat/`로 이동 완료** ?

### ? 우선순위 4: 설정 파일 정리 완료

- `local_training/scripts/pyproject.toml` → 루트 `pyproject.toml` ?
- `local_training/scripts/requirements.txt` → 삭제 (중복 제거) ?

---

## ? 최종 정리 완료 요약

### 이동 완료 파일 수

| 카테고리 | 파일 수 | 대상 폴더 | 상태 |
|---------|--------|----------|------|
| 관리 스크립트 | 20개 | `tools/` | ? 완료 |
| 배치 파일 | 6개 | `bat/` | ? 완료 |
| 설정 파일 | 2개 | 루트/삭제 | ? 완료 |
| **총계** | **28개** | - | ? **완료** |

### Import 경로 수정 완료

| 파일 | 수정된 import | 상태 |
|------|-------------|------|
| `main_integrated.py` | `scripts.optimize_code` → `tools.optimize_code` | ? 완료 |
| `main_integrated.py` | `scripts.download_and_train` → `tools.download_and_train` | ? 완료 |
| `tools/download_and_train.py` | `scripts.*` → `local_training.scripts.*` | ? 완료 |

---

**분석 완료일**: 2026년 01-13  
**작성자**: AI Assistant  
**상태**: ? **파일 정리 완료 - `FILE_ORGANIZATION_COMPLETE_REPORT.md` 참조**

---

## ? 정리 작업 완료 상태

### 완료된 작업

1. ? **Import 의존성 있는 파일 처리 완료**
   - `optimize_code.py`: `local_training/scripts/` → `tools/` 이동 완료
   - `download_and_train.py`: `local_training/scripts/` → `tools/` 이동 완료
   - `main_integrated.py` import 경로 수정 완료

2. ? **관리 스크립트 18개 이동 완료**
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

자세한 내용은 `FILE_ORGANIZATION_COMPLETE_REPORT.md`를 참조하세요.
