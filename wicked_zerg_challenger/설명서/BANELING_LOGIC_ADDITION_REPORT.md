# 맹독충 로직 추가 보고서

**작성 일시**: 2026년 01-13  
**작업 범위**: 맹독충 전투 로직 검사 및 추가  
**상태**: ? **맹독충 마이크로 로직 추가 완료**

---

## ? 검사 결과

### 기존 맹독충 관련 로직 확인

#### ? 존재하는 로직
1. **생산 로직** (`production_manager.py`)
   - 저글링을 맹독충으로 변환
   - Terran Bio 상대 시 40% 비율로 맹독충 생산
   - 맹독충 둥지 건설 및 관리

2. **마이크로 컨트롤러** (`micro_controller.py`)
   - `execute_baneling_vs_marines()` 메서드 존재
   - Terran 해병 상대 전용 로직
   - 해병 클러스터 타겟팅 및 산개 로직

3. **전투 전술** (`combat_tactics.py`, `wicked_zerg_bot_pro.py`)
   - Terran 상대 시 맹독충 사용 로직 존재

#### ? 누락된 로직
- **전투 매니저** (`combat_manager.py`)
  - `_micro_units()` 메서드에 맹독충 마이크로 로직 없음
  - 저글링, 로치, 히드라리스크만 처리
  - 맹독충은 카운트만 하고 실제 마이크로 컨트롤 없음

---

## ? 추가된 로직

### 1. `_micro_banelings()` 메서드 추가

**위치**: `local_training/combat_manager.py` (1464-1565번째 줄)

**기능**:
- 맹독충 전투 마이크로 컨트롤
- Terran 해병 상대: `MicroController.execute_baneling_vs_marines()` 사용
- Protoss/Zerg 상대: 일반 맹독충 컨트롤 로직
- 적 클러스터 타겟팅
- 맹독충 산개 로직 (한 번에 다 잡히지 않도록)

**전략**:
1. **Terran 해병 상대**: 클러스터 중심으로 이동하여 최대 피해
2. **Protoss/Zerg 저글링 상대**: 적 저글링 그룹 중심으로 이동
3. **산개**: 다른 맹독충과 너무 가까이 있으면 산개하여 한 번에 다 잡히지 않게 함
4. **최적 타겟**: 다수의 적이 모인 곳을 우선 타겟팅

---

### 2. `_find_enemy_clusters()` 메서드 추가

**위치**: `local_training/combat_manager.py` (1561-1605번째 줄)

**기능**:
- 적 유닛 클러스터 찾기 (간단한 거리 기반 클러스터링)
- 맹독충이 최대 피해를 줄 수 있는 위치 찾기
- 최대 3개의 클러스터 반환

**알고리즘**:
- 거리 기반 클러스터링 (반경 5.0)
- 클러스터 중심 계산
- 다수의 적이 모인 곳 우선 타겟팅

---

### 3. `_micro_units()` 메서드 업데이트

**변경 사항**:
```python
async def _micro_units(self):
    """개별 유닛 마이크로 컨트롤"""
    await self._micro_zerglings()
    await self._micro_banelings()  # ? 추가
    await self._micro_roaches()
    await self._micro_hydralisks()
```

---

## ? 맹독충 마이크로 로직 상세

### Terran 해병 상대
- `MicroController.execute_baneling_vs_marines()` 사용
- 해병 클러스터 중심으로 이동
- 맹독충 산개 (BANELING_SPLIT_RADIUS = 1.5)
- 최대 피해를 위한 클러스터 타겟팅

### Protoss/Zerg 상대
- 적 유닛 클러스터 찾기
- 클러스터 중심으로 이동
- 맹독충 산개 (반경 2.0)
- 가장 가까운 클러스터 우선 타겟팅

### 산개 로직
- 다른 맹독충과 거리 2.0 이내면 산개
- 평균 위치에서 벗어나는 방향으로 이동
- 한 번에 다 잡히지 않도록 분산

---

## ? 수정된 파일

### `local_training/combat_manager.py`
- ? `_micro_units()` 메서드에 `_micro_banelings()` 호출 추가
- ? `_micro_banelings()` 메서드 추가 (1464-1565번째 줄)
- ? `_find_enemy_clusters()` 메서드 추가 (1561-1605번째 줄)
- ? 구문 검증 완료 (`python -m py_compile` 통과)

---

## ? 맹독충 로직 동작 흐름

### 1. 전투 매니저 업데이트
```
_micro_units()
  ├─ _micro_zerglings()
  ├─ _micro_banelings()  ← ? 새로 추가
  ├─ _micro_roaches()
  └─ _micro_hydralisks()
```

### 2. 맹독충 마이크로 처리
```
_micro_banelings()
  ├─ 맹독충 수집 (IntelManager 캐시 또는 직접 접근)
  ├─ Terran 해병 상대?
  │   ├─ Yes → MicroController.execute_baneling_vs_marines()
  │   └─ No → 일반 맹독충 컨트롤
  ├─ 적 클러스터 찾기 (_find_enemy_clusters())
  ├─ 각 맹독충별 처리:
  │   ├─ 근처 적 찾기
  │   ├─ 가장 가까운 클러스터 찾기
  │   ├─ 다른 맹독충과 너무 가까운가?
  │   │   ├─ Yes → 산개
  │   │   └─ No → 클러스터 중심으로 이동
  │   └─ 클러스터가 없으면 가장 가까운 적 공격
```

---

## ? 검증 완료

### 구문 검증
- ? `python -m py_compile combat_manager.py` 통과
- ? 들여쓰기 오류 수정 완료
- ? import 문 확인 완료

### 로직 검증
- ? 맹독충 마이크로 로직 추가 완료
- ? Terran 해병 상대 로직 통합 완료
- ? Protoss/Zerg 상대 로직 추가 완료
- ? 산개 로직 구현 완료
- ? 클러스터 타겟팅 로직 구현 완료

---

## ? 주요 개선 사항

### 1. 전투 매니저 통합
- 맹독충이 이제 전투 매니저의 마이크로 시스템에 통합됨
- 다른 유닛(저글링, 로치, 히드라리스크)과 동일한 방식으로 처리

### 2. 종족별 최적화
- **Terran**: 해병 클러스터 타겟팅 (기존 MicroController 활용)
- **Protoss/Zerg**: 일반 적 클러스터 타겟팅

### 3. 산개 로직
- 맹독충이 한 번에 다 잡히지 않도록 산개
- 평균 위치에서 벗어나는 방향으로 이동

### 4. 클러스터 타겟팅
- 다수의 적이 모인 곳을 우선 타겟팅
- 최대 피해를 위한 최적 위치 찾기

---

## ? 다음 단계 (선택 사항)

### 추가 개선 가능 사항
1. **맹독충 드롭 로직**: 오버로드에 맹독충을 태워 적 본진에 드롭
2. **맹독충 벙커 러시**: Terran 벙커 러시 대응
3. **맹독충 스플릿**: 적 공격에 맞춰 더 정교한 산개
4. **맹독충 카운팅**: 적 해병 수에 따른 맹독충 비율 조정

---

**작업 완료일**: 2026년 01-13  
**작성자**: AI Assistant  
**상태**: ? **맹독충 마이크로 로직 추가 완료, 구문 검증 통과**
