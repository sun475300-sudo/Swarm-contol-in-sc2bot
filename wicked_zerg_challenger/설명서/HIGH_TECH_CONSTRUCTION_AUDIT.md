# 상위 테크 유닛/건물 건설 로직 정밀 검토 보고서

**작성 일시**: 2026년 01-13  
**검토 범위**: 상위 테크 유닛 및 건물 건설 로직 전체  
**상태**: ✅ **수정 완료**

---

## 📋 상위 테크 건물 및 유닛 정의

### 건물 (Tech Buildings)
- **T1 → T2**: `LAIR` (Hatchery → Lair)
- **T2 → T3**: `HIVE` (Lair → Hive)
- **T2 건물**: `SPIRE`, `INFESTATIONPIT`, `LURKERDEN`
- **T3 건물**: `ULTRALISKCAVERN`, `GREATERSPIRE` (Spire → Greater Spire)

### 유닛 (High Tech Units)
- **T2 유닛**: `HYDRALISK`, `LURKER`, `MUTALISK`, `CORRUPTOR`, `INFESTOR`
- **T3 유닛**: `ULTRALISK`, `BROODLORD`

---

## 🔍 발견된 문제점

### 문제 1: 여러 매니저 간 로직 중복 및 충돌 가능성

**위치**: `production_manager.py`, `economy_manager.py`

**문제점**:
1. **Lair 업그레이드**:
   - `production_manager.py` (라인 2860-2891): `_produce_army()` 내부에서 Lair 업그레이드
   - `economy_manager.py` (라인 1959-1984): `_build_tech_buildings()` 내부에서 Lair 업그레이드
   - **충돌 가능성**: 두 매니저가 동시에 Lair 업그레이드를 시도할 수 있음

2. **Hive 업그레이드**:
   - `production_manager.py` (라인 2893-2931): `_produce_army()` 내부에서 Hive 업그레이드
   - `economy_manager.py` (라인 2108-2115): `_build_ultimate_tech()` 내부에서 Hive 업그레이드
   - **충돌 가능성**: 두 매니저가 동시에 Hive 업그레이드를 시도할 수 있음

3. **Infestation Pit 건설**:
   - `production_manager.py` (라인 4043-4050): `_autonomous_tech_progression()` 내부에서 건설
   - `economy_manager.py` (라인 2092-2105): `_build_ultimate_tech()` 내부에서 건설
   - **충돌 가능성**: 두 매니저가 동시에 건설 시도 가능

4. **Ultralisk Cavern 건설**:
   - `production_manager.py` (라인 4052-4054): `_autonomous_tech_progression()` 내부에서 건설
   - `economy_manager.py` (라인 2117-2127): `_build_ultimate_tech()` 내부에서 건설
   - **충돌 가능성**: 두 매니저가 동시에 건설 시도 가능

5. **Greater Spire 업그레이드**:
   - `economy_manager.py` (라인 2129-2138): `_build_ultimate_tech()` 내부에서만 처리
   - **문제**: `production_manager.py`에서 처리하지 않음 (일관성 부족)

**심각도**: 🔴 **높음** (중복 건설 시도 가능)

---

### 문제 2: 테크 트리 의존성 체크 불완전

**위치**: `production_manager.py` (라인 4016-4054)

**문제점**:

1. **Spire 의존성 체크** (라인 4026-4032):
   ```python
   if tid == UnitTypeId.SPIRE:
       if (
           not b.structures(UnitTypeId.LAIR).exists
           and not b.structures(UnitTypeId.HIVE).exists
           and b.already_pending(UnitTypeId.LAIR) == 0
       ):
           continue
   ```
   - ✅ **올바름**: Lair 또는 Hive 필요

2. **Lurker Den 의존성 체크** (라인 4034-4042):
   ```python
   if tid == UnitTypeId.LURKERDEN:
       if not b.structures(UnitTypeId.HYDRALISKDEN).exists and b.already_pending(UnitTypeId.HYDRALISKDEN) == 0:
           continue
       if (
           not b.structures(UnitTypeId.LAIR).exists
           and not b.structures(UnitTypeId.HIVE).exists
           and b.already_pending(UnitTypeId.LAIR) == 0
       ):
           continue
   ```
   - ✅ **올바름**: Hydralisk Den + Lair/Hive 필요

3. **Infestation Pit 의존성 체크** (라인 4044-4050):
   ```python
   if tid == UnitTypeId.INFESTATIONPIT:
       if (
           not b.structures(UnitTypeId.LAIR).exists
           and not b.structures(UnitTypeId.HIVE).exists
           and b.already_pending(UnitTypeId.LAIR) == 0
       ):
           continue
   ```
   - ✅ **올바름**: Lair 또는 Hive 필요

4. **Ultralisk Cavern 의존성 체크** (라인 4052-4054):
   ```python
   if tid == UnitTypeId.ULTRALISKCAVERN:
       if not b.structures(UnitTypeId.HIVE).exists and b.already_pending(UnitTypeId.HIVE) == 0:
           continue
   ```
   - ✅ **올바름**: Hive 필요

**심각도**: 🟡 **중간** (의존성 체크는 올바르지만, `economy_manager.py`에서도 동일한 체크 필요)

---

### 문제 3: `economy_manager.py`의 `_build_ultimate_tech()` 중복 체크 누락

**위치**: `economy_manager.py` (라인 2080-2138)

**문제점**:

1. **Hive 업그레이드** (라인 2108-2115):
   ```python
   if lairs.exists and infestation_pits_ready.exists:
       hives = b.structures(UnitTypeId.HIVE)
       if not hives.exists:
           if b.can_afford(UnitTypeId.HIVE):
               try:
                   lairs.random(AbilityId.UPGRADETOHIVE_HIVE)
   ```
   - ❌ **문제**: `already_pending(UnitTypeId.HIVE)` 체크 없음
   - ❌ **문제**: `_can_build_safely()` 체크 없음
   - **위험**: 다른 매니저가 이미 Hive 업그레이드를 시작했을 수 있음

2. **Greater Spire 업그레이드** (라인 2129-2138):
   ```python
   if spires.exists and not great_spires.exists:
       if b.can_afford(UnitTypeId.GREATERSPIRE):
           try:
               spires.random(AbilityId.UPGRADETOGREATERSPIRE_GREATERSPIRE)
   ```
   - ❌ **문제**: `already_pending(UnitTypeId.GREATERSPIRE)` 체크 없음
   - ❌ **문제**: `_can_build_safely()` 체크 없음
   - **위험**: 중복 업그레이드 시도 가능

**심각도**: 🔴 **높음** (중복 업그레이드 시도 가능)

---

### 문제 4: `.random()` 메서드 사용 시 안전성 부족

**위치**: `economy_manager.py` (라인 2113, 2136)

**문제점**:
```python
lairs.random(AbilityId.UPGRADETOHIVE_HIVE)  # 라인 2113
spires.random(AbilityId.UPGRADETOGREATERSPIRE_GREATERSPIRE)  # 라인 2136
```

**문제**:
- `.random()`은 `Units` 객체의 메서드이지만, `lairs`와 `spires`가 빈 리스트일 경우 오류 발생 가능
- `lairs.exists`와 `spires.exists` 체크는 있지만, 실제 `.random()` 호출 전에 리스트가 비어있을 수 있음
- `await` 없이 호출되어 비동기 처리 문제 가능

**심각도**: 🟡 **중간** (예외 처리로 감싸져 있지만 개선 필요)

---

### 문제 5: `production_manager.py`의 Lair/Hive 업그레이드 중복 체크 부족

**위치**: `production_manager.py` (라인 2860-2931)

**문제점**:

1. **Lair 업그레이드** (라인 2861-2891):
   ```python
   if (
       spawning_pools
       and hatcheries
       and not lairs  # Don't have Lair yet
       and b.time > 120
       and has_gas_income
       and b.can_afford(UnitTypeId.LAIR)
   ):
   ```
   - ❌ **문제**: `already_pending(UnitTypeId.LAIR)` 체크 없음
   - **위험**: `economy_manager.py`가 이미 Lair 업그레이드를 시작했을 수 있음

2. **Hive 업그레이드** (라인 2901-2931):
   ```python
   if (
       lairs  # Have Lair
       and infestation_pits  # Have Infestation Pit ready
       and not hives  # Don't have Hive yet
       and b.time > 240
       and has_gas_income
       and b.can_afford(UnitTypeId.HIVE)
   ):
   ```
   - ❌ **문제**: `already_pending(UnitTypeId.HIVE)` 체크 없음
   - **위험**: `economy_manager.py`가 이미 Hive 업그레이드를 시작했을 수 있음

**심각도**: 🔴 **높음** (중복 업그레이드 시도 가능)

---

### 문제 6: Greater Spire가 `production_manager.py`의 `_autonomous_tech_progression()`에 없음

**위치**: `production_manager.py` (라인 3945-3994)

**문제점**:
- `tech_queue`에 `GREATERSPIRE`가 포함되어 있지 않음
- `SPIRE`만 있고, `GREATERSPIRE` 업그레이드는 `economy_manager.py`에서만 처리
- **일관성 부족**: 다른 상위 테크 건물은 `production_manager.py`에서도 처리하지만, Greater Spire는 예외

**심각도**: 🟡 **중간** (기능적으로는 작동하지만 일관성 부족)

---

## ✅ 올바르게 구현된 부분

### 1. 테크 트리 의존성 체크 (production_manager.py)
- ✅ Spire: Lair/Hive 필요 체크
- ✅ Lurker Den: Hydralisk Den + Lair/Hive 필요 체크
- ✅ Infestation Pit: Lair/Hive 필요 체크
- ✅ Ultralisk Cavern: Hive 필요 체크

### 2. 중복 건설 방지 (production_manager.py)
- ✅ `_can_build_safely()` 체크 사용
- ✅ `already_pending()` 체크 사용
- ✅ `structures().exists` 체크 사용

### 3. Infestation Pit 및 Ultralisk Cavern (economy_manager.py)
- ✅ `already_pending()` 체크 있음
- ✅ `_can_build_safely()` 체크 있음

---

## 📝 수정 권장 사항

### 우선순위 1: 즉시 수정 필요

1. **`economy_manager.py`의 Hive 업그레이드에 중복 체크 추가**
   ```python
   # 수정 전
   if not hives.exists:
       if b.can_afford(UnitTypeId.HIVE):
           try:
               lairs.random(AbilityId.UPGRADETOHIVE_HIVE)
   
   # 수정 후
   if not hives.exists and b.already_pending(UnitTypeId.HIVE) == 0:
       if b.can_afford(UnitTypeId.HIVE):
           # 추가: Lair가 실제로 ready인지 확인
           lairs_ready = [l for l in lairs if l.is_ready]
           if lairs_ready:
               try:
                   lairs_ready[0](AbilityId.UPGRADETOHIVE_HIVE)
   ```

2. **`economy_manager.py`의 Greater Spire 업그레이드에 중복 체크 추가**
   ```python
   # 수정 전
   if spires.exists and not great_spires.exists:
       if b.can_afford(UnitTypeId.GREATERSPIRE):
           try:
               spires.random(AbilityId.UPGRADETOGREATERSPIRE_GREATERSPIRE)
   
   # 수정 후
   if spires.exists and not great_spires.exists and b.already_pending(UnitTypeId.GREATERSPIRE) == 0:
       if b.can_afford(UnitTypeId.GREATERSPIRE):
           spires_ready = [s for s in spires if s.is_ready]
           if spires_ready:
               try:
                   spires_ready[0](AbilityId.UPGRADETOGREATERSPIRE_GREATERSPIRE)
   ```

3. **`production_manager.py`의 Lair 업그레이드에 중복 체크 추가**
   ```python
   # 수정 전
   if (
       spawning_pools
       and hatcheries
       and not lairs
       and b.time > 120
       and has_gas_income
       and b.can_afford(UnitTypeId.LAIR)
   ):
   
   # 수정 후
   if (
       spawning_pools
       and hatcheries
       and not lairs
       and b.already_pending(UnitTypeId.LAIR) == 0  # 추가
       and b.time > 120
       and has_gas_income
       and b.can_afford(UnitTypeId.LAIR)
   ):
   ```

4. **`production_manager.py`의 Hive 업그레이드에 중복 체크 추가**
   ```python
   # 수정 전
   if (
       lairs
       and infestation_pits
       and not hives
       and b.time > 240
       and has_gas_income
       and b.can_afford(UnitTypeId.HIVE)
   ):
   
   # 수정 후
   if (
       lairs
       and infestation_pits
       and not hives
       and b.already_pending(UnitTypeId.HIVE) == 0  # 추가
       and b.time > 240
       and has_gas_income
       and b.can_afford(UnitTypeId.HIVE)
   ):
   ```

### 우선순위 2: 개선 권장

5. **`.random()` 메서드 대신 안전한 리스트 접근 사용**
   - `lairs.random()` → `lairs_ready[0]` (리스트가 비어있지 않은지 확인 후)
   - `spires.random()` → `spires_ready[0]` (리스트가 비어있지 않은지 확인 후)

6. **Greater Spire를 `production_manager.py`의 `tech_queue`에 추가** (선택적)
   - 일관성을 위해 추가 권장
   - 또는 `economy_manager.py`에서만 처리하도록 명확히 문서화

---

## 🎯 테크 트리 의존성 정리

### 올바른 테크 트리
```
Hatchery
  └─> Lair (Spawning Pool 필요)
      ├─> Spire (Lair 필요)
      │   └─> Greater Spire (Spire 필요)
      ├─> Infestation Pit (Lair 필요)
      │   └─> Hive (Infestation Pit 필요)
      │       └─> Ultralisk Cavern (Hive 필요)
      └─> Lurker Den (Hydralisk Den + Lair 필요)
```

### 의존성 체크 요약
- ✅ **Spire**: Lair 또는 Hive 필요
- ✅ **Lurker Den**: Hydralisk Den + Lair 또는 Hive 필요
- ✅ **Infestation Pit**: Lair 또는 Hive 필요
- ✅ **Hive**: Lair + Infestation Pit 필요
- ✅ **Ultralisk Cavern**: Hive 필요
- ✅ **Greater Spire**: Spire 필요

---

## 📊 문제점 요약

| 문제 | 위치 | 심각도 | 상태 |
|------|------|--------|------|
| Lair 업그레이드 중복 | `production_manager.py`, `economy_manager.py` | 🔴 높음 | ✅ 수정 완료 |
| Hive 업그레이드 중복 | `production_manager.py`, `economy_manager.py` | 🔴 높음 | ✅ 수정 완료 |
| Greater Spire 중복 체크 누락 | `economy_manager.py` | 🔴 높음 | ✅ 수정 완료 |
| `.random()` 안전성 | `economy_manager.py` | 🟡 중간 | ✅ 수정 완료 |
| Greater Spire 일관성 | `production_manager.py` | 🟡 중간 | ⚠️ 개선 권장 (선택적) |

---

**검토 완료일**: 2026년 01-13  
**작성자**: AI Assistant  
**상태**: ✅ **수정 완료**

---

## ✅ 수정 완료 사항

### 1. `economy_manager.py`의 Hive 업그레이드 중복 체크 추가
- ✅ `already_pending(UnitTypeId.HIVE)` 체크 추가
- ✅ `.random()` 대신 안전한 리스트 접근 사용 (`lairs_ready[0]`)
- ✅ `is_ready` 체크 추가

### 2. `economy_manager.py`의 Greater Spire 업그레이드 중복 체크 추가
- ✅ `already_pending(UnitTypeId.GREATERSPIRE)` 체크 추가
- ✅ `.random()` 대신 안전한 리스트 접근 사용 (`spires_ready[0]`)
- ✅ `is_ready` 체크 추가

### 3. `production_manager.py`의 Lair 업그레이드 중복 체크 추가
- ✅ `already_pending(UnitTypeId.LAIR)` 체크 추가

### 4. `production_manager.py`의 Hive 업그레이드 중복 체크 추가
- ✅ `already_pending(UnitTypeId.HIVE)` 체크 추가

---

## 📝 수정된 파일 목록

1. ✅ `local_training/economy_manager.py` - Hive 및 Greater Spire 업그레이드 중복 체크 추가
2. ✅ `local_training/production_manager.py` - Lair 및 Hive 업그레이드 중복 체크 추가
