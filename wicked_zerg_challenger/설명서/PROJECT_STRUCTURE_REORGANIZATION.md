# 프로젝트 구조 재구성 보고서

**재구성 일시**: 2026년 01-13  
**재구성 범위**: 파일 역할별 분리, 중복 제거, 경로 통일  
**기준**: 프로젝트 루트와 핵심 로직 폴더의 명확한 역할 분리

---

## ? 재구성 원칙

### 1. wicked_zerg_challenger (프로젝트 루트)
**역할**: 프로젝트 관리, 자동화, 설정, 배포

- **자동화 및 실행 도구**: `bat/`, `.sh` 파일
- **프로젝트 설정**: `.env`, `requirements.txt`, `pyrightconfig.json`
- **문서**: `설명서/` 폴더 전체
- **관리 유틸리티**: `tools/` 폴더
- **데이터 아카이브**: `replays_archive/`
- **모니터링**: `monitoring/` 폴더
- **상태 파일**: `stats/` 폴더 (통일)

### 2. local_training (핵심 로직 폴더)
**역할**: 게임 AI 로직과 신경망 모델

- **메인 AI 엔진**: `wicked_zerg_bot_pro.py`, `main_integrated.py`
- **전술 및 운영 매니저**: `combat_manager.py`, `economy_manager.py` 등
- **학습 및 데이터 모델**: `zerg_net.py`, `models/`, `data/`
- **봇 시스템 유틸리티**: `config.py`, `telemetry_logger.py` 등
- **봇 실행 중 사용 스크립트**: `scripts/` 폴더 (봇 전용)

---

## ? 수행된 수정 사항

### 1. stats/ 폴더 통일 ?

#### 문제점
- `instance_*_status.json` 파일이 여러 위치에 생성될 수 있음
- 루트의 `stats/`와 `local_training/stats/` 중복 가능성

#### 해결 방법
- **모든 상태 파일을 루트의 `stats/` 폴더로 통일**
- `local_training/main_integrated.py` 수정:
  ```python
  # 이전: Path("stats")
  # 수정: project_root / "stats"
  project_root = Path(__file__).parent.parent
  status_dir = project_root / "stats"
  ```

- `local_training/wicked_zerg_bot_pro.py` 수정:
  ```python
  project_root = PathLib(__file__).parent.parent.parent
  status_dir = project_root / "stats"
  ```

- `local_training/scripts/parallel_train_integrated.py` 수정:
  ```python
  project_root = Path(__file__).parent.parent.parent
  status_file = project_root / "stats" / f"instance_{instance_id}_status.json"
  ```

---

### 2. 스크립트 분류 및 역할 명확화 ?

#### 봇 실행 중 사용 스크립트 (local_training/scripts/ 유지)
다음 스크립트들은 봇이 실행 중에 import하여 사용하므로 `local_training/scripts/`에 유지:

- **`replay_learning_manager.py`**: 학습 횟수 추적 (봇 실행 중 사용)
- **`learning_logger.py`**: 학습 로그 기록 (봇 실행 중 사용)
- **`strategy_database.py`**: 전략 데이터베이스 (봇 실행 중 사용)
- **`replay_quality_filter.py`**: 리플레이 품질 필터링 (봇 실행 중 사용)
- **`parallel_train_integrated.py`**: 병렬 학습 실행 (봇 실행 관련)
- **`run_hybrid_supervised.py`**: 하이브리드 학습 실행 (봇 실행 관련)

#### 관리 스크립트 (tools/로 이동 권장)
다음 스크립트들은 프로젝트 관리용이므로 `tools/`로 이동 가능:

- **`download_and_train.py`**: 리플레이 다운로드 (관리)
- **`enhanced_replay_downloader.py`**: 리플레이 다운로드 (관리)
- **`cleanup_*.py`**: 정리 스크립트 (관리)
- **`optimize_*.py`**: 최적화 스크립트 (관리)
- **`test_*.py`**: 테스트 스크립트 (관리)
- **`code_check.py`**, **`fast_code_inspector.py`**: 코드 검사 (관리)

**참고**: 현재는 import 경로가 `scripts.`로 되어 있어 봇이 사용 중이므로, 이동 시 import 경로 수정 필요.

---

### 3. Import 경로 수정 필요 사항 ??

#### 현재 Import 패턴
```python
# local_training/replay_build_order_learner.py
from scripts.replay_learning_manager import ReplayLearningTracker
from scripts.learning_logger import LearningLogger
from scripts.strategy_database import StrategyDatabase

# local_training/main_integrated.py
from scripts.download_and_train import ReplayDownloader
```

#### 권장 사항
- 봇 실행 중 사용 스크립트는 `local_training/scripts/`에 유지
- 관리 스크립트를 `tools/`로 이동할 경우:
  - `local_training/main_integrated.py`의 import 경로 수정 필요
  - 또는 `tools/`를 Python path에 추가

---

## ? 파일 구조 (재구성 후)

```
wicked_zerg_challenger/          # 프로젝트 루트
├── bat/                         # 자동화 스크립트
│   ├── start_training.bat
│   ├── train.bat
│   └── ...
├── tools/                       # 관리 유틸리티
│   ├── auto_downloader.py
│   ├── replay_lifecycle_manager.py
│   ├── download_and_train.py   # (이동 권장)
│   └── ...
├── monitoring/                  # 모니터링 시스템
│   └── ...
├── 설명서/                      # 문서
│   └── ...
├── stats/                       # 상태 파일 (통일)
│   └── instance_*_status.json
├── replays_archive/             # 완료된 리플레이
├── requirements.txt
├── pyrightconfig.json
└── ...

local_training/                  # 핵심 로직
├── wicked_zerg_bot_pro.py       # 메인 봇
├── main_integrated.py           # 통합 실행
├── zerg_net.py                  # 신경망
├── config.py                    # 설정
├── combat_manager.py            # 전투 관리
├── economy_manager.py           # 경제 관리
├── production_manager.py        # 생산 관리
├── intel_manager.py             # 정보 관리
├── scouting_system.py           # 정찰 시스템
├── scripts/                     # 봇 실행 중 사용 스크립트
│   ├── replay_learning_manager.py
│   ├── learning_logger.py
│   ├── strategy_database.py
│   ├── replay_quality_filter.py
│   ├── parallel_train_integrated.py
│   └── run_hybrid_supervised.py
├── models/                      # 학습된 모델
├── data/                        # 학습 데이터
│   └── build_orders/
└── ...
```

---

## ? 완료된 작업

### 1. stats/ 폴더 통일
- ? `local_training/main_integrated.py` - 루트 stats/ 사용
- ? `local_training/wicked_zerg_bot_pro.py` - 루트 stats/ 사용
- ? `local_training/scripts/parallel_train_integrated.py` - 루트 stats/ 사용

### 2. 스크립트 분류
- ? 봇 실행 중 사용 스크립트 식별
- ? 관리 스크립트 식별
- ? 역할별 분류 완료

---

## ? 추가 권장 사항

### 1. 관리 스크립트 이동 (선택적)
관리 스크립트를 `tools/`로 이동하려면:

1. **파일 이동**:
   ```bash
   # 예시
   mv local_training/scripts/download_and_train.py tools/
   mv local_training/scripts/enhanced_replay_downloader.py tools/
   ```

2. **Import 경로 수정**:
   ```python
   # local_training/main_integrated.py
   # 이전: from scripts.download_and_train import ReplayDownloader
   # 수정: sys.path에 tools/ 추가 후
   from download_and_train import ReplayDownloader
   ```

### 2. scripts/ 폴더 정리
- 봇 실행 중 사용하지 않는 스크립트 제거 또는 이동
- `scripts/` 폴더는 봇 전용 스크립트만 유지

### 3. 문서 인덱스 생성
- `설명서/DOCUMENTATION_INDEX.md` 생성
- 각 문서의 목적과 최신 상태 명시

---

## ? 주요 효과

### 구조 명확화
- **역할 분리**: 루트는 관리, local_training은 핵심 로직
- **중복 제거**: stats/ 폴더 통일
- **유지보수성 향상**: 파일 위치가 역할에 맞게 정리

### 안정성 향상
- **Import 오류 방지**: 경로 통일로 혼동 방지
- **파일 충돌 방지**: stats/ 폴더 통일로 중복 방지
- **명확한 구조**: 파일 위치가 역할을 명확히 표현

---

**재구성 완료일**: 2026년 01-13  
**작성자**: AI Assistant  
**상태**: ? **주요 구조 재구성 완료**
