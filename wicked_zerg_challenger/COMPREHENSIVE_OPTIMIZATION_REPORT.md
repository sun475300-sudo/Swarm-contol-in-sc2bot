# 종합 최적화 리포트

## 1. 불필요한 파일

- 발견된 파일: 97개
- 발견된 디렉토리: 68개

### 삭제 대상 파일 (상위 20개)

- `combat_manager.py.bak`
- `COMPLETE_RUN_SCRIPT.py.bak`
- `config.py.bak`
- `economy_manager.py.bak`
- `genai_self_healing.py.bak`
- `intel_manager.py.bak`
- `map_manager.py.bak`
- `micro_controller.py.bak`
- `production_manager.py.bak`
- `queen_manager.py.bak`
- `rogue_tactics_manager.py.bak`
- `run.py.bak`
- `run_with_training.py.bak`
- `scouting_system.py.bak`
- `spell_unit_manager.py.bak`
- `telemetry_logger.py.bak`
- `unit_factory.py.bak`
- `wicked_zerg_bot_pro.py.bak`
- `zerg_net.py.bak`
- `combat\macro_combat.py.bak`

## 2. 코드 스타일 일관성

- 총 스타일 이슈: 6648개
- 영향받는 파일: 89개

## 3. 실행 로직 분석

- 메인 스크립트: 8개
  - `COMPLETE_RUN_SCRIPT.py`
  - `run_with_training.py`
  - `run_with_training.py.bak`
  - `bat\run_refactoring_analysis.bat`
  - `bat\run_runtime_check.bat`
  - `local_training\scripts\run_hybrid_supervised.py`
  - `local_training\scripts\run_hybrid_supervised.py.bak`
  - `tools\run_runtime_check.bat`

## 4. 최적화 제안

- 큰 파일 발견 (2개): 분리 고려
-   - local_training\main_integrated.py: 1367줄
-   - tools\download_and_train.py: 1179줄

