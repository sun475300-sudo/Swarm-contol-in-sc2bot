# Scripts 폴더 정리 계획

**정리 일시**: 2026년 01-13  
**정리 범위**: local_training/scripts/ 폴더 역할별 분리  
**기준**: 봇 실행 중 사용 vs 관리 스크립트 구분

---

## ? 스크립트 분류

### 봇 실행 중 사용 스크립트 (local_training/scripts/ 유지)

다음 스크립트들은 봇이 실행 중에 import하여 사용하므로 **유지**:

1. **`replay_learning_manager.py`**
   - 학습 횟수 추적
   - Import 위치: `replay_build_order_learner.py`, `integrated_pipeline.py`

2. **`learning_logger.py`**
   - 학습 로그 기록
   - Import 위치: `replay_build_order_learner.py`

3. **`strategy_database.py`**
   - 전략 데이터베이스 관리
   - Import 위치: `replay_build_order_learner.py`, `download_and_train.py`

4. **`replay_quality_filter.py`**
   - 리플레이 품질 필터링
   - Import 위치: `download_and_train.py`

5. **`parallel_train_integrated.py`**
   - 병렬 학습 실행
   - 봇 실행 관련

6. **`run_hybrid_supervised.py`**
   - 하이브리드 학습 실행
   - 봇 실행 관련

### 관리 스크립트 (tools/로 이동 또는 정리)

다음 스크립트들은 프로젝트 관리용이므로 **tools/로 이동 권장**:

1. **`download_and_train.py`**
   - 리플레이 다운로드 (관리)
   - 현재 import: `main_integrated.py`
   - 이동 시 import 경로 수정 필요

2. **`enhanced_replay_downloader.py`**
   - 리플레이 다운로드 (관리)
   - 중복 기능 가능성

3. **`cleanup_*.py`** (여러 파일)
   - 정리 스크립트 (관리)

4. **`optimize_*.py`** (여러 파일)
   - 최적화 스크립트 (관리)
   - 현재 import: `main_integrated.py` (optimize_code)

5. **`test_*.py`** (여러 파일)
   - 테스트 스크립트 (관리)

6. **`code_check.py`**, **`fast_code_inspector.py`**
   - 코드 검사 (관리)

7. **`local_hidden_gems.py`**
   - 코드 분석 (관리)

8. **`organize_file_structure.py`**
   - 파일 구조 정리 (관리)

9. **`verify_structure.py`**
   - 구조 검증 (관리)

---

## ? 정리 작업 계획

### 1단계: Import 경로 확인
- 봇 실행 중 사용하는 스크립트 식별 완료
- 관리 스크립트의 import 위치 확인 완료

### 2단계: 관리 스크립트 이동 (선택적)
- `download_and_train.py` → `tools/` (import 경로 수정 필요)
- `optimize_code.py` → `tools/` (import 경로 수정 필요)
- 기타 관리 스크립트 → `tools/` 또는 삭제

### 3단계: scripts/ 폴더 최소화
- 봇 실행 중 사용 스크립트만 유지
- `__init__.py` 추가하여 패키지화

---

## ?? 주의 사항

### Import 경로 수정 필요
다음 파일들의 import 경로를 수정해야 함:

1. **`local_training/main_integrated.py`**:
   ```python
   # 현재
   from scripts.download_and_train import ReplayDownloader
   from scripts.optimize_code import remove_korean_comments
   
   # 이동 후 (sys.path에 tools/ 추가 필요)
   import sys
   from pathlib import Path
   tools_path = Path(__file__).parent.parent / "tools"
   if str(tools_path) not in sys.path:
       sys.path.insert(0, str(tools_path))
   from download_and_train import ReplayDownloader
   from optimize_code import remove_korean_comments
   ```

2. **`local_training/scripts/download_and_train.py`**:
   ```python
   # 현재
   from scripts.replay_quality_filter import ReplayQualityFilter
   from scripts.strategy_database import StrategyDatabase
   
   # 이동 후 (상대 import 또는 절대 import로 변경)
   # 옵션 1: tools/로 이동 시
   from replay_quality_filter import ReplayQualityFilter  # 같은 폴더
   from strategy_database import StrategyDatabase  # 같은 폴더
   
   # 옵션 2: local_training/scripts/에 유지
   # 현재대로 유지
   ```

---

## ? 최종 구조 (권장)

### local_training/scripts/ (봇 실행 중 사용만)
```
scripts/
├── __init__.py
├── replay_learning_manager.py
├── learning_logger.py
├── strategy_database.py
├── replay_quality_filter.py
├── parallel_train_integrated.py
└── run_hybrid_supervised.py
```

### tools/ (관리 스크립트)
```
tools/
├── download_and_train.py (이동)
├── enhanced_replay_downloader.py (이동)
├── optimize_code.py (이동)
├── cleanup_*.py (이동)
├── test_*.py (이동)
└── ...
```

---

**정리 계획일**: 2026년 01-13  
**상태**: ?? **계획 수립 완료, 실행 대기**
