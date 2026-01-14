# 이병렬(Rogue) 선수 전술 구현 가이드

**작성 일시**: 2026년 01-13  
**작업 범위**: 이병렬 선수의 맹독충 드랍 및 후반 운영 전술 구현  
**상태**: ? **이병렬 전술 시스템 구현 완료**

---

## ? 구현 개요

이병렬(Rogue) 선수의 핵심 전술을 AI에게 학습시키기 위한 시스템을 구축했습니다.

### 핵심 전술
1. **맹독충 드랍 (Baneling Drop)**: 적 병력이 전진하는 타이밍에 드랍
2. **시야 밖 우회 기동**: 적의 시야 범위를 피해 드랍 지점까지 이동
3. **라바 세이빙**: 교전 직전 라바를 모아두었다가 드랍 후 폭발적 생산
4. **점막 기반 의사결정**: 적 병력이 점막에 닿았을 때의 타이밍 감지

---

## ? 구현 완료 사항

### 1. `RogueTacticsManager` 생성

**파일**: `local_training/rogue_tactics_manager.py`

#### 주요 기능
- **맹독충 드랍 타이밍 감지**: 적 병력이 점막에 전진 중일 때 드랍 실행
- **대군주 속업 연계**: 대군주 속업 완료 후 드랍 가능
- **시야 밖 우회 경로**: 적 시야 범위를 피하는 경로 계산
- **라바 세이빙 관리**: 교전 직전 라바 보존 및 드랍 후 폭발적 생산

#### 핵심 메서드
1. `update()`: 매 프레임 업데이트
2. `_check_overlord_speed_upgrade()`: 대군주 속업 상태 확인
3. `_detect_enemy_on_creep()`: 적 병력이 점막에 닿았는지 감지
4. `_execute_baneling_drop()`: 맹독충 드랍 실행
5. `_calculate_stealth_path()`: 시야 밖 우회 경로 계산
6. `_manage_larva_saving()`: 라바 세이빙 관리

---

### 2. `wicked_zerg_bot_pro.py` 통합

#### 추가된 내용
- `RogueTacticsManager` import 및 초기화
- `on_start()`에서 `rogue_tactics` 매니저 초기화
- `on_step()`에서 `rogue_tactics.update()` 호출
- `on_end()`에서 이병렬 전술 보상 계산

#### 보상 함수 개선
```python
# 이병렬(Rogue) 전술 보상
rogue_reward = 0.0
if self.rogue_tactics:
    # 드랍 성공 보상: +0.2
    # 적이 점막에 전진 중일 때: +0.1
    # 드랍 준비 상태: +0.05
```

---

### 3. `production_manager.py` 라바 세이빙 통합

#### 추가된 내용
- `_produce_army()` 메서드에 라바 세이빙 로직 통합
- `rogue_tactics.should_save_larva()` 체크
- 라바 세이빙 모드일 때 모든 라바 보존

---

## ? 이병렬 전술 동작 흐름

### 1. 대군주 속업 감지
```
_overlord_speed_researched = False
→ UpgradeId.OVERLORDSPEED 확인
→ 속업 완료 시 _overlord_speed_researched = True
→ 드랍 전술 활성화
```

### 2. 적 병력 점막 감지
```
적 유닛이 점막 반경(20.0) 내에 있음
→ enemy_on_creep = True
→ 적이 우리 기지 방향으로 전진 중인지 확인
→ enemy_advancing = True (3기 이상 전진 중)
```

### 3. 라바 세이빙 시작
```
enemy_on_creep && enemy_advancing
→ larva_saving_mode = True
→ 모든 라바 보존 (드랍 후 폭발적 생산 준비)
```

### 4. 맹독충 드랍 실행
```
드랍 조건 확인:
  1. 대군주 속업 완료 ?
  2. 쿨다운 경과 (30초) ?
  3. 적이 점막에 전진 중 ?
  4. 맹독충 4기 이상 준비 ?
  5. 드랍용 대군주 준비 ?

→ 맹독충을 대군주에 태우기
→ 시야 밖 우회 경로 계산
→ 적 본진/확장 기지로 이동
→ 드랍 실행
```

### 5. 드랍 후 폭발적 생산
```
드랍 완료
→ larva_saving_mode = False
→ 보존된 라바로 폭발적 병력 생산
→ Rogue식 회전력 발휘
```

---

## ? 데이터 추출 포인트

### 1. 대군주 속업 타이밍과 드랍 시점의 상관관계

**구현 위치**: `rogue_tactics_manager.py` - `_check_overlord_speed_upgrade()`

**데이터 포인트**:
- 대군주 속업 완료 시간: `overlord_speed_research_time`
- 드랍 실행 시간: `last_drop_time`
- 드랍 지연 시간: `last_drop_time - overlord_speed_research_time`

**학습 목표**: 대군주 속업 완료 후 적절한 타이밍에 드랍 실행

---

### 2. 적 병력이 점막에 닿았을 때의 타이밍 감지

**구현 위치**: `rogue_tactics_manager.py` - `_detect_enemy_on_creep()`

**데이터 포인트**:
- 적이 점막에 도달한 시간: `last_enemy_on_creep_time`
- 적이 전진 중인지 여부: `enemy_advancing`
- 점막 반경 내 적 유닛 수: `enemy_units.closer_than(20.0, main_hatch.position).amount`

**학습 목표**: 적 병력이 점막에 전진 중일 때 드랍 유닛 출발

---

### 3. 시야 밖 우회 기동 경로 탐색

**구현 위치**: `rogue_tactics_manager.py` - `_calculate_stealth_path()`

**데이터 포인트**:
- 직접 경로상 적 시야 범위 체크
- 우회 경로 waypoints 계산
- 맵 가장자리 활용

**학습 목표**: 적의 시야 범위를 피해 드랍 지점까지 안전하게 이동

---

### 4. 라바 세이빙 패턴

**구현 위치**: 
- `rogue_tactics_manager.py` - `_manage_larva_saving()`
- `production_manager.py` - `_produce_army()` (라바 세이빙 체크)

**데이터 포인트**:
- 라바 세이빙 시작 시간: `larva_save_start_time`
- 보존된 라바 수: `saved_larva_count`
- 드랍 후 폭발적 생산량

**학습 목표**: 교전 직전 라바를 모아두었다가 드랍 후 폭발적 생산

---

## ? 보상 함수 조정

### 추가된 보상 항목

1. **드랍 성공 보상**: `+0.2`
   - 조건: 드랍이 실행되었고 게임 시간 2분 이후
   - 목적: 드랍 전술 사용 장려

2. **적이 점막에 전진 중일 때**: `+0.1`
   - 조건: `enemy_on_creep && enemy_advancing`
   - 목적: 적절한 타이밍 감지 보상

3. **드랍 준비 상태**: `+0.05`
   - 조건: 대군주 속업 완료, 쿨다운 경과, 드랍 진행 중 아님
   - 목적: 드랍 준비 상태 유지 보상

---

## ? 리플레이 학습 가이드

### 추천 리플레이 소스

1. **IEM Katowice (2018, 2020, 2022)**
   - 이병렬 선수 우승 대회
   - 테란 공성 전차 라인 무너뜨리는 맹독충 드랍 정수
   - 리플레이 경로: Spawning Tool, SC2Replays

2. **HomeStory Cup (HSC)**
   - 창의적인 빌드와 운영의 경계 전술
   - 날빌과 운영의 균형

3. **WCS Global Finals**
   - 최정상급 프로토스 상대 맹독충 드랍 + 군단 숙주 혼용 전술

---

### 리플레이 분석 포인트

#### 맹독충 드랍 타이밍
- 대군주 속업 완료 시간
- 드랍 실행 시간
- 적 병력 위치 (점막 여부)
- 적 병력 전진 여부

#### 시야 밖 우회 기동
- 드랍 경로상 적 시야 범위
- 우회 경로 waypoints
- 맵 가장자리 활용 여부

#### 라바 세이빙 패턴
- 교전 직전 라바 수
- 드랍 후 생산량
- 폭발적 생산 타이밍

---

## ? 조건부 학습 로직

### 12못 올인 vs 프로토스전 후반 운영

현재 시스템은 다음 조건으로 전술을 선택할 수 있습니다:

```python
# 프로토스 상대 시
if enemy_race == EnemyRace.PROTOSS:
    # 초반: 12못 올인 가능
    if b.time < 300:  # 5분 이내
        # 올인 빌드 로직
    else:
        # 후반 운영: 맹독충 드랍 + 군단 숙주
        # Rogue 전술 활성화
```

---

## ? 다음 단계

### 추가 개선 가능 사항

1. **드랍 성공률 추적**: 드랍으로 인한 적 일꾼/병력 피해 추적
2. **드랍 타이밍 최적화**: 적 병력 위치에 따른 최적 드랍 타이밍 학습
3. **다중 드랍**: 여러 대군주로 동시 드랍
4. **드랍 후 후속 공격**: 드랍 후 정면 공격 연계

---

## ? 구현된 파일

### 새로 생성된 파일
- ? `local_training/rogue_tactics_manager.py` (420줄)

### 수정된 파일
- ? `local_training/wicked_zerg_bot_pro.py`
  - `RogueTacticsManager` import 및 초기화
  - `on_step()`에서 업데이트 호출
  - 보상 함수에 이병렬 전술 보상 추가
- ? `local_training/production_manager.py`
  - 라바 세이빙 로직 통합

---

## ? 검증 완료

### 구문 검증
- ? `rogue_tactics_manager.py` 구문 검증 통과
- ? `wicked_zerg_bot_pro.py` 구문 검증 통과
- ? `production_manager.py` 구문 검증 통과

### 로직 검증
- ? 맹독충 드랍 로직 구현 완료
- ? 대군주 속업 연계 로직 구현 완료
- ? 시야 밖 우회 경로 계산 구현 완료
- ? 라바 세이빙 패턴 구현 완료
- ? 보상 함수 조정 완료

---

## ? 이병렬 전술 학습 체크리스트

### 드랍 전술
- [x] ? 대군주 속업 완료 확인
- [x] ? 적 병력 점막 감지
- [x] ? 적 병력 전진 감지
- [x] ? 맹독충 준비 확인
- [x] ? 드랍용 대군주 준비 확인
- [x] ? 시야 밖 우회 경로 계산
- [x] ? 드랍 실행

### 라바 세이빙
- [x] ? 적이 점막에 전진 중일 때 라바 세이빙 시작
- [x] ? 드랍 완료 후 라바 세이빙 해제
- [x] ? 폭발적 생산 활성화

### 보상 함수
- [x] ? 드랍 성공 보상 (+0.2)
- [x] ? 적이 점막에 전진 중일 때 보상 (+0.1)
- [x] ? 드랍 준비 상태 보상 (+0.05)

---

**작업 완료일**: 2026년 01-13  
**작성자**: AI Assistant  
**상태**: ? **이병렬 전술 시스템 구현 완료, 구문 검증 통과**
