# local_training 폴더 파일 구분

**작성일**: 2026-01-13  
**목적**: `local_training/` 폴더와 `local_training/scripts/` 폴더에 있어야 할 파일을 명확히 구분

---

## ? local_training/ (루트 폴더)에 있어야 할 파일

**역할**: 봇이 직접 import하여 사용하는 핵심 로직 파일

### ? 메인 실행 파일
- `main_integrated.py` - 통합 학습 실행 진입점
- `wicked_zerg_bot_pro.py` - 메인 봇 클래스 (모든 매니저 통합)

### ?? 핵심 매니저 모듈 (게임 로직)
- `combat_manager.py` - 전투 전략 및 유닛 제어
- `combat_tactics.py` - 구체적인 전투 행동
- `economy_manager.py` - 자원 및 건물 관리
- `intel_manager.py` - 적 정보 및 데이터 캐싱
- `production_manager.py` - 유닛 생산 로직
- `production_resilience.py` - 비상 생산 및 병목 해결
- `queen_manager.py` - 퀸 관리
- `scouting_system.py` - 정찰 및 맵 탐험
- `micro_controller.py` - 상세 유닛 마이크로 제어
- `personality_manager.py` - 개성 및 채팅 시스템
- `telemetry_logger.py` - 게임 데이터 로깅
- `map_manager.py` - 맵 관리
- `unit_factory.py` - 유닛 팩토리
- `rogue_tactics_manager.py` - 로그 전술 관리
- `spell_unit_manager.py` - 스펠 유닛 관리

### ? 학습 및 신경망
- `zerg_net.py` - 신경망 모델 (ZergNet) 및 강화학습
- `curriculum_manager.py` - 커리큘럼 학습 시스템
- `replay_build_order_learner.py` - 리플레이에서 빌드 오더 추출

### ?? 설정 및 파이프라인
- `config.py` - 전역 설정 값
- `integrated_pipeline.py` - 통합 학습 파이프라인

### ? 데이터 폴더
- `models/` - 학습된 모델 가중치 (.pt 파일)
- `data/` - 학습 데이터
  - `build_orders/` - 리플레이에서 추출한 빌드 오더
- `logs/` - 실행 로그
- `replays/` - 학습용 리플레이
- `test_replays/` - 테스트용 리플레이

### ? 문서
- `설명서/` - local_training 로직 관련 문서

### ? 기타 (실행 시 생성)
- `training_stats.json` - 학습 통계
- `telemetry_*.json` - 텔레메트리 데이터

---

## ? local_training/scripts/ 폴더에 있어야 할 파일

**역할**: 봇 실행 중에 import되어 사용되는 스크립트 (봇 런타임 스크립트)

### ? 봇 실행 중 사용 스크립트 (올바른 위치)

#### 학습 관리
- `replay_learning_manager.py` - 학습 반복 추적 (각 리플레이별 학습 횟수 관리)
- `learning_logger.py` - 학습 로그 기록
- `learning_status_manager.py` - 학습 상태 추적 (필수)

#### 전략 및 데이터베이스
- `strategy_database.py` - 전략 데이터베이스 관리

#### 리플레이 처리
- `replay_quality_filter.py` - 리플레이 품질 필터링
- `replay_crash_handler.py` - 크래시 처리 및 잘못된 리플레이 감지
- `replay_learning_tracker_sqlite.py` - SQLite 기반 리플레이 학습 추적

#### 학습 실행
- `parallel_train_integrated.py` - 병렬 학습 실행
- `run_hybrid_supervised.py` - 하이브리드 감독 학습 실행

#### 패키지 초기화
- `__init__.py` - Python 패키지 초기화 파일

### ? scripts/ 폴더 내 데이터 폴더 (스크립트 실행 시 생성)
- `scripts/data/` - 스크립트 실행 데이터
- `scripts/logs/` - 스크립트 실행 로그
- `scripts/replays/` - 스크립트 처리 리플레이
- `scripts/stats/` - 스크립트 통계

### ? scripts/ 폴더 내 상태 파일 (스크립트 실행 시 생성)
- `learning_status.json` - 학습 상태 파일

---

## ? 구분 원칙

### local_training/ (루트)에 있어야 하는 파일
- ? `wicked_zerg_bot_pro.py`에서 직접 import되는 파일
- ? 게임 실행에 필수적인 핵심 로직
- ? 메인 실행 진입점
- ? 신경망 모델 및 학습 관련 핵심 모듈

### local_training/scripts/에 있어야 하는 파일
- ? 봇 실행 중에 `from scripts.xxx import yyy` 형태로 import되는 파일
- ? 학습 관리, 로그 기록, 데이터베이스 관리 등 지원 기능
- ? 병렬 학습, 하이브리드 학습 등 학습 실행 스크립트
- ? 리플레이 처리 및 필터링 유틸리티

---

## ? 실제 import 패턴 예시

### local_training/ (루트) 파일들이 import하는 패턴:

```python
# wicked_zerg_bot_pro.py
from combat_manager import CombatManager
from economy_manager import EconomyManager
from zerg_net import ZergNet

# replay_build_order_learner.py
from scripts.replay_learning_manager import ReplayLearningTracker
from scripts.learning_logger import LearningLogger
from scripts.strategy_database import StrategyDatabase
```

---

## ?? 주의사항

### scripts/ 폴더에 있으면 안 되는 파일
- ? 관리 유틸리티 (cleanup, optimize, test 등) → `tools/` 폴더로 이동
- ? 다운로드 스크립트 → `tools/` 폴더로 이동
- ? 코드 검사 스크립트 → `tools/` 폴더로 이동

### 루트에 있으면 안 되는 파일
- ? 프로젝트 관리 스크립트 → `tools/` 폴더로 이동
- ? 모니터링 파일 → `monitoring/` 폴더로 이동
- ? 배포 스크립트 → 루트 또는 `tools/` 폴더

---

## ? 현재 local_training/scripts/ 폴더 파일 현황

### ? 올바른 위치에 있는 파일
- `replay_learning_manager.py` ?
- `learning_logger.py` ?
- `strategy_database.py` ?
- `replay_quality_filter.py` ?
- `parallel_train_integrated.py` ?
- `run_hybrid_supervised.py` ?
- `learning_status_manager.py` ?
- `replay_crash_handler.py` ?
- `replay_learning_tracker_sqlite.py` ?
- `__init__.py` ?

### ? scripts/ 폴더 내 데이터 폴더 (생성됨, 정상)
- `scripts/data/` ?
- `scripts/logs/` ?
- `scripts/replays/` ?
- `scripts/stats/` ?

---

**작성일**: 2026-01-13
