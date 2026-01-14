# Build-Order Gap Analyzer (빌드오더 오차 분석기)

## 개요

Build-Order Gap Analyzer는 프로게이머의 리플레이 데이터와 봇이 실제로 수행한 데이터를 프레임 단위로 대조하여 **'성능 저하의 구간'**을 찾아내는 시스템입니다.

## 핵심 기능

### 1. Time Gap (시간 오차) 분석
- 프로게이머와 봇의 건물 건설 시간 비교
- 오차가 30초 이상이면 "critical", 15초 이상이면 "major"로 분류
- 예: "프로는 1분 30초에 산란못을 완성했는데, 봇은 왜 1분 50초에 지었는가?"

### 2. Sequence Error (순서 오류) 분석
- 빌드 오더의 순서가 올바른지 검증
- 누락된 건물이나 잘못된 순서 감지
- 예: "프로는 가스를 짓고 바로 바퀴 소굴을 올렸는데, 봇은 왜 저글링 발업부터 눌렀는가?"

### 3. Resource Efficiency (자원 효율) 분석
- Supply 구간별 자원 보유량 비교
- 미네랄/가스 낭비 정도 측정
- 예: "프로는 인구수 20일 때 미네랄이 0에 수렴하는데, 봇은 왜 400이나 남았는가?"

### 4. 자동 보완 로직
- 분석 결과를 바탕으로 CurriculumManager의 우선순위 업데이트
- Gemini Self-Healing과 연동하여 자동 코드 패치 생성

## 사용 방법

### 자동 실행 (권장)

게임이 패배로 끝나면 자동으로 분석이 실행됩니다:

```python
# wicked_zerg_bot_pro.py의 on_end 메서드에서 자동 실행
if str(game_result) == "Defeat":
    gap_analysis = analyze_bot_performance(self, "defeat")
    # Gemini Self-Healing에 전달하여 자동 패치 생성
```

### 수동 실행

```python
from local_training.strategy_audit import StrategyAudit, analyze_bot_performance

# 봇 인스턴스가 있는 경우
result = analyze_bot_performance(bot, "defeat")

# 직접 분석
auditor = StrategyAudit()
result = auditor.analyze(
    build_order_timing=build_order_timing_dict,
    telemetry_data=telemetry_data_list,
    game_id="game_001"
)
```

## 분석 결과 구조

```python
@dataclass
class GapAnalysisResult:
    game_id: str
    analysis_time: str
    time_gaps: List[TimeGap]           # 시간 오차 리스트
    sequence_errors: List[SequenceError]  # 순서 오류 리스트
    resource_efficiency: List[ResourceEfficiency]  # 자원 효율 리스트
    critical_issues: List[str]          # 가장 심각한 문제 3개
    recommendations: List[str]          # 개선 권장사항
```

## 출력 파일

분석 결과는 다음 경로에 저장됩니다:

```
local_training/data/strategy_audit/gap_analysis_{game_id}.json
```

## Gemini Self-Healing 연동

패배한 게임의 분석 결과는 자동으로 Gemini Self-Healing에 전달되어:

1. **문제 분석**: 가장 늦은 건물 3개 식별
2. **코드 패치 생성**: economy_manager.py, production_manager.py 최적화 제안
3. **자동 적용**: enable_auto_patch가 True인 경우 자동으로 패치 적용

### 예시 피드백

```
=== Build-Order Gap Analysis ===
Game ID: game_0_20250114_143022

Critical Issues (프로 대비 가장 늦은 건물 3개):
  1. SpawningPool: 18.5초 늦음 (프로: 90.0초, 봇: 108.5초)
  2. Extractor: 12.3초 늦음 (프로: 108.0초, 봇: 120.3초)
  3. Hatchery: 8.2초 늦음 (프로: 96.0초, 봇: 104.2초)

Time Gaps (시간 오차):
  - SpawningPool: 18.5초 늦음 (critical)
  - Extractor: 12.3초 늦음 (major)
  - Hatchery: 8.2초 늦음 (minor)

Resource Efficiency Issues (자원 효율 문제):
  - Supply 20: 효율 0.45 (미네랄 낭비: 350, 가스 낭비: 150)

Recommendations (권장사항):
  1. SpawningPool 건설을 18.5초 더 빠르게 시작하도록 economy_manager.py의 드론 생산 로직을 최적화하세요.
  2. Supply 20 구간에서 자원 효율이 낮습니다. production_manager.py의 Emergency Flush 로직을 강화하세요.
```

## CurriculumManager 연동

분석 결과를 바탕으로 CurriculumManager의 건물 우선순위가 자동으로 업데이트됩니다:

```python
from local_training.strategy_audit import update_curriculum_priority

# 가장 심각한 시간 오차를 가진 건물의 우선순위를 "Urgent"로 설정
update_curriculum_priority(curriculum_manager, gap_analysis)
```

## 데이터 요구사항

### 프로게이머 데이터
- `learned_build_orders.json` 파일이 필요합니다
- 경로: `local_training/scripts/learned_build_orders.json` 또는 `D:/replays/archive/training_*/learned_build_orders.json`

### 봇 데이터
- `build_order_timing`: production_manager의 build_order_timing 딕셔너리
- `telemetry_data`: telemetry_logger의 telemetry_data 리스트

## 제한사항

1. **프로 데이터 변환**: 현재는 Supply를 시간으로 대략적으로 변환합니다 (supply * 1.5초). 더 정교한 변환이 필요할 수 있습니다.

2. **자원 효율 기준**: 프로게이머의 자원 보유량은 평균값을 사용합니다. 실제 리플레이 데이터가 있으면 더 정확합니다.

3. **순서 비교**: 처음 10개 건물만 비교합니다. 더 긴 빌드 오더는 확장이 필요합니다.

## 향후 개선 사항

1. **정교한 시간 변환**: Supply 대신 실제 게임 시간 사용
2. **프로 데이터 확장**: 더 많은 리플레이 샘플 사용
3. **실시간 분석**: 게임 중에도 실시간으로 분석하여 즉시 조정
4. **머신러닝 통합**: 분석 결과를 학습 데이터로 활용

## 관련 파일

- `local_training/strategy_audit.py`: 핵심 분석 로직
- `wicked_zerg_bot_pro.py`: 게임 종료 시 자동 실행
- `genai_self_healing.py`: Gemini 연동
- `local_training/curriculum_manager.py`: 우선순위 업데이트
