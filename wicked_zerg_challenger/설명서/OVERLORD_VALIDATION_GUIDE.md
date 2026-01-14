# 대군주 생산 로직 일원화 성능 검증 가이드

## 개요

**대군주 생산 로직 일원화 (Phase 7)** 의 성능 검증을 위한 게임 테스트 및 분석 가이드입니다.

### 검증 항목

1. **초반 3분 자원 최적화 (0-180초)**
   - 절약된 라바 1마리와 미네랄 100이 드론/저글링으로 전환되는지 확인
   - 목표: 초반 드론 생산이 기존 대비 1-2마리 증가

2. **후반 인구수 버퍼 효율성 (180~200 구간)**
   - 병력 급속 소모 시 대군주가 제때 생산되는지 확인
   - 목표: 인구수 최소값 >= 5 (안정적 버퍼 유지)

---

## 검증 메트릭

### ? 초반 3분 (OPENING 단계 - 0~180초)

| 메트릭 | 추적 방식 | 목표 값 |
|--------|---------|--------|
| **180초 시점 드론 수** | `ProductionManager.validation_metrics["early_game"]["drones_at_180s"]` | +1~2 마리 증가 |
| **라바 효율성** | `드론 증가량 / 최대 라바 수` | >= 0.5 |
| **인구수 막힘** | `supply_left < 3` 발생 횟수 | 0회 |
| **미네랄 활용** | 평균 미네랄 보유량 | 50~200 범위 |

### ? 후반 (PRODUCTION/MID 단계 - 인구수 180 이상)

| 메트릭 | 추적 방식 | 목표 값 |
|--------|---------|--------|
| **최소 인구수** | `ProductionManager.validation_metrics["late_game"]["min_supply_ever"]` | >= 5 |
| **대군주 생산 횟수** | `overlord_productions 리스트 길이` | >= 2회 |
| **긴급 생산 비율** | `emergency 타입 / 전체` | <= 30% |
| **예측 생산 비율** | `predictive 타입 / 전체` | >= 70% |
| **인구수 막힘 사건** | `supply_blocks` 카운트 | <= 2회 |

---

## 검증 방법

### 방법 1: 게임 로그 분석 (추천)

```bash
# 1단계: 게임 실행
python test_overlord_optimization.py --games 5

# 2단계: 기존 텔레메트리 분석
python verify_overlord_optimization.py

# 3단계: 자동 생성된 보고서 확인
# overlord_optimization_report_*.json
```

### 방법 2: 수동 검증 (빠른 확인)

게임을 실행하면서 콘솔에서 다음 로그를 확인합니다:

```
[OVERLORD] Emergency production at 4 supply left     # 긴급 생산 (좋음)
[OVERLORD] Predictive production: 2 overlords ...   # 예측 생산 (매우 좋음)
[WARNING] Supply block risk! Need 2 overlords ...   # 인구수 막힘 (나쁨)
```

### 방법 3: 실시간 메트릭 확인

```python
# 게임 도중에 언제든 확인 가능
bot.production_manager.validation_metrics

# 출력 예시:
{
    "early_game": {
        "drones_at_180s": 24,           # 180초 시점 드론 수
        "larva_used_early": 15,
        "minerals_spent_early": 1200,
        "supply_blocks": 0              # 초반 인구수 막힘 없음 ?
    },
    "late_game": {
        "overlord_productions": [
            (456.0, "emergency", 3),
            (820.0, "predictive", 6),
            (1120.0, "predictive", 4)
        ],
        "min_supply_ever": 6,           # 최소 인구수 >= 5 ?
        "supply_blocks": 1              # 거의 발생하지 않음
    }
}
```

---

## 성공 기준

### ? PASS (모두 충족)

- ? 초반 3분에 인구수 막힘 발생 0회
- ? 180초 드론 수 >= 23마리
- ? 후반 최소 인구수 >= 5
- ? 긴급 생산 < 전체의 30%
- ? 대군주 생산 >= 2회

### ? CAUTION (일부 미충족)

- ?? 초반 인구수 막힘 1-2회
- ?? 후반 최소 인구수 3~4
- ?? 긴급 생산 > 전체의 40%

### ? FAIL (많이 미충족)

- ? 초반 인구수 막힘 3회 이상
- ? 후반 최소 인구수 < 2
- ? 대군주 생산 미흡 (<1회)

---

## 데이터 해석

### 1. 초반 3분 자원 절약 효과

**의미**: 제거된 3개의 중복 대군주 생산 로직으로 인해 절약된 라바와 미네랄이 실제 유닛 생산으로 전환되는지 확인

**기대 효과**:
- 중복 제거 전: on_step(매 프레임) + fix_production_bottleneck(매 1초) + _build_army_aggressive(필요시) = 1게임에 3~5마리 초과 생산
- 중복 제거 후: ProductionManager만 생산 = 1게임에 1~2마리 절약

**측정 방법**:
```
180초 시점 드론 수 = 초기 12마리 + 추가 생산
예상: 23~25마리 (이전 21~23마리 대비 2마리 증가)
```

### 2. 후반 인구수 버퍼 효율성

**의미**: ProductionManager의 예측 기반 대군주 생산이 병력 소모 시 적절히 작동하는지 확인

**기대 효과**:
- 예측 기반 생산 (권장): supply_left < buffer (8~16) → 미리 대군주 생산 (최적)
- 긴급 대응 (허용): supply_left < 5 → 즉시 대군주 생산 (좋음)
- 인구수 막힘 (실패): supply_left < 0 → 유닛 생산 불가능 (나쁨)

**측정 방법**:
```
overlord_productions 분석:
- (time, "predictive", supply_left): 예측 생산 - 이상적 ?
- (time, "emergency", supply_left): 긴급 생산 - 허용됨 ??
- supply_blocks 카운트: 막힘 발생 - 피해야 함 ?
```

---

## 게임 테스트 절차

### 단계 1: 사전 준비

```bash
# 텔레메트리 파일 백업 (비교용)
mkdir -p backup_telemetry
cp telemetry_*.json backup_telemetry/
```

### 단계 2: 게임 실행

```bash
# 단일 게임 테스트
python wicked_zerg_bot_pro.py

# 또는 배치 테스트 (5판)
python test_overlord_optimization.py --games 5
```

### 단계 3: 자동 분석

게임이 끝나면 자동으로 생성되는 보고서 확인:

```bash
# 최신 텔레메트리 분석
python verify_overlord_optimization.py

# 또는 특정 파일 분석
python verify_overlord_optimization.py --telemetry telemetry_0.json
```

### 단계 4: 결과 해석

생성된 JSON 보고서 확인:
```
overlord_optimization_report_20260111_154301.json
```

---

## 예상 결과

### 정상 작동 시나리오

```json
{
  "early_game_analysis": {
    "drones_at_180s": 24,
    "efficiency_score": 85.5
  },
  "late_game_analysis": {
    "average_supply_left": 7.2,
    "min_supply_left": 5,
    "supply_block_count": 0,
    "buffer_efficiency": 82.3
  }
}
```

### 문제 발생 시나리오

```json
{
  "late_game_analysis": {
    "min_supply_left": 2,          // ? 너무 낮음
    "supply_block_count": 3,       // ? 많이 발생
    "buffer_efficiency": 25.0      // ? 매우 낮음
  }
}
// → ProductionManager._produce_overlord() 버퍼 값 증가 필요
```

---

## 트러블슈팅

### 문제 1: 초반에 자주 인구수 막힘 발생

**원인**: 초반 빌드 오더가 라바를 과다 소비

**해결책**:
1. ProductionManager 최우선 순위 재확인
2. Serral 빌드 오더의 라바 소비 점검
3. 초반 미네랄 임계값 조정

```python
# production_manager.py line 500
aggressive_flush_threshold = get_learned_parameter(
    "aggressive_flush_threshold", 600  # 증가: 500 → 600
)
```

### 문제 2: 후반에 자주 인구수 막힘 발생

**원인**: 예측 버퍼가 충분하지 않음

**해결책**:
1. 동적 버퍼 값 증가

```python
# production_manager.py line 670
if game_time < 600:  # 3-10 minutes
    supply_buffer = 14  # 증가: 12 → 14
```

2. 군사 건물 가속 로직 강화

```python
# production_manager.py line 710
production_multiplier = 1.0 + (military_buildings * 0.3)  # 증가: 0.2 → 0.3
```

### 문제 3: 대군주가 너무 많이 생산됨

**원인**: 버퍼가 너무 높음

**해결책**:
1. 동적 버퍼 값 감소

```python
# production_manager.py line 670
if game_time < 600:  # 3-10 minutes
    supply_buffer = 10  # 감소: 12 → 10
```

---

## 로그 출력 해석

### 일반적인 로그 순서

```
[OVERLORD] Predictive production: 2 overlords (supply: 8/200)  # 최적
[OVERLORD] Emergency production at 4 supply left              # 허용
[WARNING] [120s] Supply block risk! Need 2 overlords ...      # 경고
```

### 좋은 신호

```
- 예측 생산 비율 높음 (>70%)
- 긴급 생산 적음 (<30%)
- 인구수 막힘 경고 거의 없음 (0~1회/게임)
```

### 나쁜 신호

```
- 긴급 생산만 나타남 (예측 생산 없음)
- 인구수 막힘 경고 자주 발생 (>3회/게임)
- supply_left < 0 상황 발생 (유닛 생산 불가)
```

---

## 최종 검증 체크리스트

- [ ] 게임 5판 이상 테스트 완료
- [ ] 초반 3분 메트릭 수집됨 (drones_at_180s, supply_blocks)
- [ ] 후반 메트릭 수집됨 (min_supply_ever, overlord_productions)
- [ ] 분석 보고서 자동 생성됨 (JSON)
- [ ] 초반 인구수 막힘 0회 확인
- [ ] 후반 최소 인구수 >= 5 확인
- [ ] 대군주 생산 >= 2회 확인
- [ ] 모든 3개 bot 파일(root/deploy/submission) 동기화 확인

---

## 다음 단계

1. **게임 테스트 실행**: `python test_overlord_optimization.py --games 5`
2. **결과 분석**: `python verify_overlord_optimization.py`
3. **보고서 검토**: JSON 파일 분석
4. **필요시 조정**: 트러블슈팅 가이드 참고
5. **Git 커밋**: 검증 완료 후 Phase 8 시작

---

## 참고 문헌

- **ProductionManager._produce_overlord()**: Lines 640-800 (root)
- **Validation Metrics**: ProductionManager.__init__ (Line 150+)
- **Update 메트릭 초기화**: ProductionManager.update() (Line 470+)

