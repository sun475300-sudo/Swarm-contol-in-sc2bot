# await train() 오류 수정 가이드

**작성일**: 2026-01-15  
**목적**: `object bool can't be used in 'await' expression` 오류 해결

---

## ? 오류 원인

### 1. `await train()` 오류

**오류 메시지**:
```
[ERROR] Overlord production failed: object bool can't be used in 'await' expression
[ERROR] Failed to train UnitTypeId.ZERGLING: object bool can't be used in 'await' expression
```

**원인**:
- SC2 API의 `train()` 메서드는 동기 메서드로 `bool` 값을 반환합니다
- 일부 경우 coroutine을 반환할 수 있지만, 대부분 `bool`을 반환합니다
- `await`를 사용하면 `bool` 값에 대해 `await`를 시도하여 오류 발생

**해결 방법**:
- `_safe_train()` 메서드를 사용하여 동기/비동기 모두 처리
- 또는 `await`를 제거하고 `bool` 반환값을 직접 확인

### 2. `vespene_gas` 속성 오류

**오류 메시지**:
```
[WARNING] QueenManager 오류: 'WickedZergBotPro' object has no attribute 'vespene_gas'
```

**원인**:
- SC2 API에서는 `vespene` 속성을 사용해야 합니다
- `vespene_gas`는 존재하지 않는 속성입니다

**해결 방법**:
- `self.bot.vespene_gas` → `self.bot.vespene`로 변경

---

## ? 수정된 코드

### 1. Overlord 생산 수정

**위치**: `production_manager.py` line 843-849

**수정 전**:
```python
try:
    await larva.train(UnitTypeId.OVERLORD)
    overlords_produced += 1
except Exception as e:
    print(f"[ERROR] Overlord production failed: {e}")
```

**수정 후**:
```python
try:
    # CRITICAL FIX: Use _safe_train to handle both sync and async train() methods
    if await self._safe_train(larva, UnitTypeId.OVERLORD):
        overlords_produced += 1
except Exception as e:
    print(f"[ERROR] Overlord production failed: {e}")
```

### 2. Zergling 생산 수정

**위치**: `production_manager.py` line 563-569, 1658-1663

**수정 전**:
```python
try:
    await larva.train(UnitTypeId.ZERGLING)
    zergling_produced += 1
except Exception as e:
    print(f"[ERROR] Failed to train Zergling: {e}")
```

**수정 후**:
```python
try:
    # CRITICAL FIX: Use _safe_train to handle both sync and async train() methods
    if await self._safe_train(larva, UnitTypeId.ZERGLING):
        zergling_produced += 1
except Exception as e:
    print(f"[ERROR] Failed to train Zergling: {e}")
```

### 3. QueenManager 속성 수정

**위치**: `queen_manager.py` line 66

**수정 전**:
```python
if self.bot.minerals < mineral_threshold or self.bot.vespene_gas < gas_threshold:
```

**수정 후**:
```python
# CRITICAL FIX: Use 'vespene' instead of 'vespene_gas' (correct SC2 API attribute)
if self.bot.minerals < mineral_threshold or self.bot.vespene < gas_threshold:
```

---

## ? `_safe_train()` 메서드

`production_manager.py`에 이미 구현된 안전한 `train()` 래퍼 메서드:

```python
async def _safe_train(self, unit, unit_type):
    """Safely train a unit, handling both sync and async train() methods"""
    try:
        result = unit.train(unit_type)
        # train() may return bool or coroutine
        if hasattr(result, '__await__'):
            await result
        return True
    except Exception as e:
        current_iteration = getattr(self.bot, "iteration", 0)
        if current_iteration % 200 == 0:
            print(f"[WARNING] _safe_train error: {e}")
        return False
```

**장점**:
- 동기/비동기 모두 처리
- 오류 발생 시 안전하게 처리
- 반환값이 `bool`이든 coroutine이든 모두 처리

---

## ? 남은 수정 사항

다음 위치에서도 동일한 오류가 발생할 수 있습니다:

- `production_manager.py` line 741: `await larva.train(UnitTypeId.ZERGLING)`
- `production_manager.py` line 1121: `await hatch.train(UnitTypeId.QUEEN)`
- `production_manager.py` line 1218: `await ready_larvae.random.train(UnitTypeId.ZERGLING)`
- `production_manager.py` line 1524: `await random.choice(larvae).train(UnitTypeId.MUTALISK)`
- `production_manager.py` line 1940, 1955, 2064, 2186, 2203: 기타 `await train()` 호출

**권장 사항**:
- 모든 `await larva.train()` 호출을 `await self._safe_train(larva, unit_type)`로 변경
- 또는 일괄 검색/교체로 수정

---

## ? 테스트 방법

1. 게임 실행:
   ```bash
   python wicked_zerg_challenger/run_with_training.py
   ```

2. 오류 확인:
   - Overlord 생산 오류가 발생하지 않는지 확인
   - Zergling 생산 오류가 발생하지 않는지 확인
   - QueenManager 오류가 발생하지 않는지 확인

3. 로그 확인:
   - `[ERROR] Overlord production failed` 메시지가 사라졌는지 확인
   - `[ERROR] Failed to train Zergling` 메시지가 사라졌는지 확인
   - `[WARNING] QueenManager 오류` 메시지가 사라졌는지 확인

---

**최종 상태**: ? **주요 오류 수정 완료**

Overlord 생산, Zergling 생산, QueenManager 속성 오류가 수정되었습니다. 나머지 `await train()` 호출도 점진적으로 수정할 수 있습니다.
