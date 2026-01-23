# 총 개선점 보고서

## 수정 완료된 버그 (3개)

### 1. ✅ ProductionResilience._safe_train() 버그 수정
**파일**: `local_training/production_resilience.py:87`
**문제**: `unit.train()`의 결과를 `bot.do()`로 실행하지 않아 유닛이 생산 안됨
```python
# BEFORE (잘못됨):
result = unit.train(unit_type)
if hasattr(result, '__await__'):
    await result  # 실행 안됨
return True

# AFTER (올바름):
action = unit.train(unit_type)
self.bot.do(action)  # 실제 유닛 생산 실행
return True
```

### 2. ✅ economy_manager._train_drone_if_needed() 버그 수정
**파일**: `economy_manager.py:110`
**문제**: `await bot.do()` 사용 - bot.do()는 async가 아님
```python
# BEFORE:
await self.bot.do(larva_unit.train(UnitTypeId.DRONE))

# AFTER:
if hasattr(self.bot, 'production') and self.bot.production:
    await self.bot.production._safe_train(larva_unit, UnitTypeId.DRONE)
else:
    self.bot.do(larva_unit.train(UnitTypeId.DRONE))
```

### 3. ✅ economy_manager._train_overlord_if_needed() 버그 수정
**파일**: `economy_manager.py:78`
**문제**: `await bot.do()` 사용
```python
# AFTER:
if hasattr(self.bot, 'production') and self.bot.production:
    await self.bot.production._safe_train(larva_unit, UnitTypeId.OVERLORD)
else:
    self.bot.do(larva_unit.train(UnitTypeId.OVERLORD))
```

---

## 필요한 개선사항 (4개)

### 1. ❌ 조기 확장 (1분 이후 자원 여유 시)
**현재 상태**: 확장이 너무 늦음
**목표**: 1분(60초) 이후 미네랄 400+ 시 즉시 확장

**수정 위치**: `local_training/production_resilience.py:312`
```python
# CURRENT:
if b.minerals > 400 and b.already_pending(UnitTypeId.HATCHERY) == 0:
    bases = b.townhalls.amount if hasattr(b, "townhalls") else 1
    if b.can_afford(UnitTypeId.HATCHERY):
        # 확장 시도

# SUGGESTED:
game_time = getattr(b, "time", 0.0)
# 1분 이후 미네랄 400+ 시 확장
if game_time >= 60 and b.minerals > 400 and b.already_pending(UnitTypeId.HATCHERY) == 0:
    if b.can_afford(UnitTypeId.HATCHERY):
        await self._try_expand()
        print(f"[EARLY_EXPAND] [{int(game_time)}s] Expanding at 1min+ with {int(b.minerals)} minerals")
```

### 2. ❌ 전투 후 역공격 로직
**현재 상태**: 전투 후 아군이 많이 남아도 방어만 함
**목표**: 전투 승리 시 (아군 서플라이 >> 적 서플라이) 즉시 역공격

**수정 위치**: `combat_manager.py` - 새 메서드 추가
```python
async def _check_counterattack_opportunity(self, army_units, enemy_units):
    """
    전투 후 역공격 기회 확인

    조건:
    1. 최근 교전이 있었음 (5초 이내)
    2. 아군 서플라이 > 적 서플라이 * 2 (압도적 우위)
    3. 최소 서플라이 10 이상

    액션:
    - 즉시 적 기지로 공격
    """
    game_time = getattr(self.bot, "time", 0)

    # Check if there was recent combat
    if not hasattr(self, "_last_combat_time"):
        self._last_combat_time = 0

    # Track combat (if we attacked or were attacked in last 5 seconds)
    if enemy_units and army_units:
        self._last_combat_time = game_time

    time_since_combat = game_time - self._last_combat_time
    if time_since_combat > 5:  # No recent combat
        return False

    # Calculate army supplies
    our_supply = sum(getattr(u, "supply_cost", 1) for u in army_units)
    enemy_supply = sum(getattr(u, "supply_cost", 1) for u in enemy_units)

    # Check if we have overwhelming advantage
    if our_supply >= 10 and our_supply > enemy_supply * 2:
        print(f"[COUNTER_ATTACK] Our supply: {our_supply}, Enemy: {enemy_supply} - Attacking!")
        return True

    return False
```

**통합 위치**: `combat_manager.py:on_step()` 메서드에 추가

### 3. ❌ 일꾼 분배 빈도 증가
**현재 상태**:
- 가스 분배: 22프레임마다 (~1초)
- 미네랄 재분배: 44프레임마다 (~2초)

**문제**: 재분배가 느려서 일꾼이 본기지에 과포화

**수정 위치**: `economy_manager.py:47-52`
```python
# CURRENT:
if iteration % 22 == 0:
    await self._distribute_workers_to_gas()
if iteration % 44 == 0:
    await self._redistribute_mineral_workers()

# SUGGESTED:
# 더 자주 재분배 (11프레임 = 0.5초, 22프레임 = 1초)
if iteration % 11 == 0:
    await self._distribute_workers_to_gas()
if iteration % 22 == 0:
    await self._redistribute_mineral_workers()
```

### 4. ❌ 저글링/바퀴 업그레이드 로직 추가
**현재 상태**: Evolution Chamber 업그레이드만 존재
**누락**:
- Metabolic Boost (저글링 이동속도)
- Adrenal Glands (저글링 공격속도)
- Burrow (잠복)
- Glial Reconstitution (바퀴 잠복 이동)

**수정 필요**: 새 파일 생성 `unit_upgrade_manager.py`

---

## 적용 계획

1. **즉시 적용 (핵심 버그)**: ✅ 완료
   - ProductionResilience._safe_train
   - economy_manager 드론/오버로드 생산

2. **다음 재시작 시 적용 (로직 개선)**:
   - 조기 확장 (1분+)
   - 일꾼 재분배 빈도 증가
   - 전투 후 역공격
   - 유닛 업그레이드 시스템

---

## 검증 방법

### 드론 생산 확인
```bash
tail -f training.log | grep -E "DRONE|train|Zergling"
```
예상 결과:
- `[TRAIN] Drone trained successfully`
- `[EARLY_DEFENSE] Emergency Zergling production: 0 -> 6`

### 일꾼 분배 확인
```bash
tail -f training.log | grep -E "redistribute|worker"
```
예상 결과:
- `[ECONOMY] Redistributed 5 workers from Base 1 to Base 2`

### 역공격 확인
```bash
tail -f training.log | grep -E "COUNTER_ATTACK"
```
예상 결과:
- `[COUNTER_ATTACK] Our supply: 25, Enemy: 8 - Attacking!`

---

## 현재 훈련 상태

게임 진행 중 (8분+):
- ✅ 봇 초기화 성공
- ✅ 모든 매니저 실행 중
- ❌ 드론 생산 로그 없음 → 수정 코드가 아직 미적용 (Python 캐시)
- ⚠️ 공격 받음 (324초)

**다음 단계**: 게임 종료 후 재시작하여 수정사항 확인
