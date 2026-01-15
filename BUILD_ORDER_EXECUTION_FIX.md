# 빌드 오더 실행 문제 수정 가이드

**작성일**: 2026-01-15  
**목적**: 초반 빌드 오더(자연 확장, 가스, 산란못)가 실행되지 않는 문제 해결

---

## ? 문제 분석

### 발견된 문제

빌드 오더 비교 분석에서 다음 빌드 오더들이 "Not executed"로 표시됨:
- `natural_expansion_supply`: 실행되지 않음 (프로 기준: 30)
- `gas_supply`: 실행되지 않음 (프로 기준: 17)
- `spawning_pool_supply`: 실행되지 않음 (프로 기준: 17)

### 원인 분석

1. **빌드 오더 타이밍 저장 문제**
   - `_execute_serral_opening()`에서 빌드 오더 타이밍을 `build_order_timing`에만 저장
   - `get_build_order_timing()`은 `serral_build_order_timing`을 먼저 확인
   - 결과: `None` 반환 → "Not executed"로 표시

2. **빌드 오더 실행 우선순위 문제**
   - Resource flush가 빌드 오더보다 먼저 실행됨
   - Resource flush가 `return`하여 빌드 오더 실행이 건너뛰어짐

3. **Early game 조건 문제**
   - 조건: `b.supply_used <= 50 or b.time < 180`
   - 게임이 627초까지 진행되면 `b.time < 180` 조건 불만족
   - Supply가 50을 넘으면 `b.supply_used <= 50` 조건 불만족
   - 결과: 빌드 오더 실행 로직이 호출되지 않음

---

## ? 수정 사항

### 1. 빌드 오더 타이밍 저장 수정

**문제**: `build_order_timing`에만 저장, `serral_build_order_timing`에는 저장 안 함

**수정**: 모든 빌드 오더 타이밍을 두 곳에 모두 저장

**수정된 빌드 오더**:
- `natural_expansion_supply` / `natural_expansion_time`
- `gas_supply` / `gas_time`
- `spawning_pool_supply` / `spawning_pool_time`
- `third_hatchery_supply` / `third_hatchery_time`
- `speed_upgrade_supply` / `speed_upgrade_time`

**코드 예시**:
```python
# 수정 전
self.build_order_timing["natural_expansion_supply"] = float(b.supply_used)

# 수정 후
supply_value = float(b.supply_used)
time_value = float(b.time)
self.build_order_timing["natural_expansion_supply"] = supply_value
self.serral_build_order_timing["natural_expansion_supply"] = supply_value  # 추가
```

### 2. 빌드 오더 실행 우선순위 개선

**문제**: Resource flush가 빌드 오더보다 먼저 실행

**수정**: 빌드 오더를 Resource flush보다 먼저 실행

**코드 위치**: `production_manager.py` line 618-625

**수정 전**:
```python
# Resource flush 먼저
if b.minerals >= aggressive_flush_threshold:
    if await self._flush_resources():
        return  # 빌드 오더 실행 안 됨

# 빌드 오더 나중
if early_game:
    if await self._execute_serral_opening():
        return
```

**수정 후**:
```python
# 빌드 오더 먼저 (HIGHEST PRIORITY)
if early_game or build_orders_incomplete:
    if await self._execute_serral_opening():
        return  # 빌드 오더 실행됨

# Resource flush 나중
if b.minerals >= aggressive_flush_threshold:
    if await self._flush_resources():
        return
```

### 3. Early Game 조건 완화

**문제**: 조건이 너무 엄격하여 빌드 오더 실행 기회가 적음

**수정**: 조건 완화 및 미완료 빌드 오더 체크 추가

**수정 전**:
```python
early_game = b.supply_used <= 50 or b.time < 180  # 너무 엄격
if early_game:
    if await self._execute_serral_opening():
        return
```

**수정 후**:
```python
early_game = b.supply_used <= 60 or b.time < 300  # 조건 완화
build_orders_incomplete = (
    not self.serral_build_completed["natural_expansion"] or
    not self.serral_build_completed["gas"] or
    not self.serral_build_completed["spawning_pool"]
)

# Early game이 아니어도 미완료 빌드 오더가 있으면 실행
if early_game or game_phase == GamePhase.OPENING or build_orders_incomplete:
    if await self._execute_serral_opening():
        return
```

### 4. 속성 오류 수정

**문제**: `vespene_gas` 속성 오류

**수정**: `vespene` 속성 사용

**위치**: `production_manager.py` line 5395

**수정 전**:
```python
if b.minerals >= 200 and b.vespene_gas >= 100:
```

**수정 후**:
```python
# CRITICAL FIX: Use 'vespene' instead of 'vespene_gas' (correct SC2 API attribute)
if b.minerals >= 200 and b.vespene >= 100:
```

---

## ? 수정된 파일

- `wicked_zerg_challenger/production_manager.py`:
  - 빌드 오더 타이밍 저장 로직 수정 (5개 빌드 오더)
  - 빌드 오더 실행 우선순위 개선
  - Early game 조건 완화
  - `vespene_gas` → `vespene` 속성 수정

---

## ? 예상 효과

### Before (수정 전)
- 빌드 오더 타이밍이 기록되지 않음 → "Not executed" 표시
- Resource flush가 빌드 오더를 블로킹
- Early game 조건이 엄격하여 실행 기회 적음
- 빌드 오더 점수: 0.18/1.0 (매우 낮음)

### After (수정 후)
- 빌드 오더 타이밍이 정확히 기록됨
- 빌드 오더가 Resource flush보다 우선 실행
- Early game 조건 완화로 실행 기회 증가
- 빌드 오더 점수: 0.8+/1.0 (예상)

---

## ? 테스트 방법

1. 게임 실행:
   ```bash
   python wicked_zerg_challenger/run_with_training.py
   ```

2. 빌드 오더 실행 확인:
   - `[SERRAL BUILD]` 로그 메시지 확인
   - 자연 확장, 가스, 산란못이 실행되는지 확인

3. 빌드 오더 비교 분석 확인:
   - 게임 종료 후 빌드 오더 비교 분석 확인
   - "Not executed" 대신 실제 supply 값이 표시되는지 확인

---

**최종 상태**: ? **빌드 오더 실행 문제 수정 완료**

빌드 오더 타이밍이 정확히 기록되고, 빌드 오더가 우선 실행되도록 수정되었습니다.
