# 리플레이 수집 및 학습 파이프라인 고급 개선 보고서

**개선 일시**: 2026년 01-13  
**개선 범위**: 고급 품질 필터링, 단계별 집중 학습, 전략 데이터베이스, 파일 관리 정밀화  
**기준**: 사용자 제공 고급 개선 지침에 따른 전면 강화

---

## ? 개선 개요

이번 개선에서는 AI가 **데이터의 품질을 스스로 판단**하고, **학습의 효율을 높일 수 있는 지표**들을 포함하여 리플레이 수집 및 학습 파이프라인을 더욱 견고하게 만들었습니다.

---

## ? 주요 개선 사항

### 1. 리플레이 품질 및 메타데이터 필터링 (품질 관리)

#### 1.1 APM(분당 행동 수) 하한선 설정
- **구현**: `local_training/scripts/replay_quality_filter.py`
- **기능**: 저그 플레이어의 평균 APM이 최소 250 이상인 리플레이만 수집
- **효과**: 아마추어나 낮은 수준의 경기를 배제하여 학습 데이터의 질 향상

#### 1.2 대전 상대의 수준 확인
- **구현**: `ReplayQualityFilter.check_opponent_level()`
- **기능**: 상대방 플레이어(테란, 프로토스)가 Grandmaster 티어이거나 프로게이머인 리플레이 우선순위
- **확인 항목**:
  - 프로게이머 이름 매칭
  - Grandmaster/Master 리그 확인
  - 이름에 GM 지표 포함 여부

#### 1.3 공식 래더 맵 확인
- **구현**: `ReplayQualityFilter.check_official_map()`
- **기능**: 연습용 맵이나 유즈맵이 아닌, 현재 래더 시즌 공식 맵에서 진행된 경기 확인
- **제외 맵**: Custom, Arcade, Practice, Test 맵 자동 감지

---

### 2. 학습 로직의 구체화 (효율성)

#### 2.1 단계별 집중 학습
- **구현**: `local_training/scripts/replay_learning_manager.py`
- **학습 단계**:
  - **1~2회차**: 초반 빌드 오더(0~5분)에 집중
    - 집중 영역: `build_order`, `opening`, `economy_setup`
    - 가중치: build_order 60%, economy 30%, scouting 10%
  - **3~4회차**: 중반 유닛 조합 및 소모전(5~15분)
    - 집중 영역: `unit_composition`, `micro_control`, `skirmishes`, `multitasking`
    - 가중치: unit_composition 40%, micro 30%, multitasking 20%, economy 10%
  - **5회차+**: 후반 운영 및 마법 유닛 활용(15분+)
    - 집중 영역: `macro_management`, `spell_units`, `late_game_units`, `map_control`
    - 가중치: macro 40%, spell_units 30%, map_control 20%, economy 10%

#### 2.2 보상 함수 연동 준비
- **구현**: `local_training/replay_build_order_learner.py._extract_strategies()`
- **기능**: 리플레이 내의 저그 플레이어가 특정 시점에 취한 행동과 그 결과를 대조
- **추출 전략**:
  - 드랍 타이밍 (Drop timing)
  - 빌드 오더 (Build order)
  - 마법 유닛 활용 (Spell unit usage)

---

### 3. 예외 상황 처리 및 자동 복구

#### 3.1 버전 불일치 자동 스킵
- **구현**: `download_and_train.py._validate_replay_metadata()`
- **기능**: 리플레이 파일의 버전이 현재 설치된 `sc2reader`나 게임 엔진 버전과 호환되지 않을 경우
- **처리**: 해당 파일을 즉시 `D:\replays\incompatible` 폴더로 이동하고 다음 파일로 진행
- **통계**: `incompatible_count`로 추적

#### 3.2 로그 기록 의무화
- **구현**: `local_training/scripts/learning_logger.py`
- **기능**: 매 학습 완료 시마다 어떤 파일에서 어떤 전략을 추출했는지 간략한 요약 로그 기록
- **로그 파일**:
  - `learning_log.txt`: 학습 완료 로그
  - `strategy_extractions.json`: 전략 추출 상세 로그
- **기록 내용**:
  - 타임스탬프
  - 리플레이 파일명
  - 반복 횟수
  - 학습 단계 (early_game, mid_game, late_game)
  - 추출된 전략 목록
  - 집중 영역 정보

---

### 4. 파일 관리의 정밀도

#### 4.1 파일 무결성 검사
- **구현**: `ReplayQualityFilter.check_file_integrity()`
- **검사 항목**:
  - 파일 존재 여부
  - 파일 크기 (0 바이트 체크)
  - 최소 크기 확인 (10KB 이상)
  - 파일 헤더 읽기 가능 여부
- **효과**: 손상된 파일(`CRC 오류` 등)을 사전에 차단

#### 4.2 폴더 구조 정규화
- **구현**: `download_and_train.py._organize_replay_file()`
- **폴더 구조**:
  - `D:\replays\by_race\`: 종족별 분류 (ZvT, ZvP, ZvZ)
  - `D:\replays\by_map\`: 맵 이름별 분류
  - `D:\replays\by_player\`: 선수 이름별 분류
- **자동 분류**: sc2reader 메타데이터를 기반으로 자동 분류
- **폴백**: 메타데이터 추출 실패 시 메인 디렉토리에 저장

---

### 5. 전략 데이터베이스

#### 5.1 전략 저장 시스템
- **구현**: `local_training/scripts/strategy_database.py`
- **기능**: 학습 중 추출된 핵심 전략을 별도의 전략 DB에 저장
- **저장 정보**:
  - 전략 ID
  - 전략 타입 (build_order, drop_timing, micro_control 등)
  - 매치업 (ZvT, ZvP, ZvZ)
  - 타이밍 (게임 시간)
  - 설명
  - 추출된 리플레이 파일명
  - 효과성 점수 (선택적)
- **쿼리 기능**: 타입, 매치업, 타이밍 범위로 필터링 가능

---

## ? 개선된 파일 목록

### 새로 생성된 파일
1. **`local_training/scripts/replay_quality_filter.py`**
   - APM 필터링
   - 상대방 수준 확인
   - 공식 맵 확인
   - 파일 무결성 검사

2. **`local_training/scripts/strategy_database.py`**
   - 전략 데이터베이스 관리
   - 전략 저장 및 쿼리
   - 통계 기능

3. **`local_training/scripts/learning_logger.py`**
   - 학습 로그 기록
   - 전략 추출 로그
   - 학습 요약 통계

### 수정된 파일
1. **`local_training/scripts/download_and_train.py`**
   - 품질 필터 통합
   - incompatible 폴더 관리
   - 폴더 구조 정규화
   - 파일 무결성 검사 통합

2. **`local_training/scripts/replay_learning_manager.py`**
   - 단계별 집중 학습 로직 추가
   - 학습 단계별 가중치 설정

3. **`local_training/replay_build_order_learner.py`**
   - 단계별 집중 학습 통합
   - 전략 추출 로직 추가
   - 학습 로거 통합

---

## ? 사용 방법

### 1. 리플레이 다운로드 (고급 필터링)

```bash
cd local_training
python scripts/download_and_train.py --max-download 50
```

**자동 적용되는 필터**:
- APM >= 250 (저그 플레이어)
- 게임 시간: 5~30분
- LotV 패치 이후
- 공식 래더 맵 (우선)
- 상대방 수준 확인

### 2. 학습 실행 (단계별 집중 학습)

```bash
cd local_training
python replay_build_order_learner.py
```

**자동 적용되는 기능**:
- 각 리플레이를 최소 5회 반복 학습
- 1~2회차: 초반 빌드 오더 집중
- 3~4회차: 중반 유닛 조합 집중
- 5회차+: 후반 운영 집중
- 전략 자동 추출 및 DB 저장
- 학습 로그 자동 기록

### 3. 전략 데이터베이스 조회

```bash
cd local_training
python scripts/strategy_database.py --stats
python scripts/strategy_database.py --list
```

### 4. 학습 로그 확인

```bash
cd local_training
python scripts/learning_logger.py --summary
```

---

## ? 파일 구조

```
D:\replays\
├── *.SC2Replay          # 메인 리플레이 파일들
├── completed\           # 5회 이상 학습 완료된 리플레이
├── incompatible\         # 버전 불일치 리플레이
├── by_race\             # 종족별 분류
│   ├── ZvT\
│   ├── ZvP\
│   └── ZvZ\
├── by_map\              # 맵별 분류
│   ├── Acropolis\
│   ├── Ancient_Cistern\
│   └── ...
├── by_player\           # 선수별 분류
│   ├── Serral\
│   ├── Reynor\
│   └── ...
├── .learning_tracking.json  # 학습 진행 추적
├── learning_log.txt         # 학습 완료 로그
├── strategy_extractions.json # 전략 추출 로그
└── strategy_db.json         # 전략 데이터베이스
```

---

## ? 주요 효과

### 데이터 품질 향상
- **APM 필터링**: 낮은 수준의 경기 자동 배제
- **상대방 수준 확인**: 고수준 경기 우선 수집
- **공식 맵 확인**: 유즈맵/연습맵 자동 제외

### 학습 효율 향상
- **단계별 집중 학습**: 각 단계에 맞는 관점으로 분석
- **전략 추출**: 성공적인 전략 자동 식별 및 저장
- **학습 로그**: 어떤 전략이 어느 리플레이에서 추출되었는지 추적

### 안정성 향상
- **버전 불일치 처리**: 호환되지 않는 리플레이 자동 분리
- **파일 무결성 검사**: 손상된 파일 사전 차단
- **폴더 구조 정규화**: 체계적인 파일 관리

---

## ? 설정 옵션

### 품질 필터 설정
```python
# local_training/scripts/replay_quality_filter.py
MIN_ZERG_APM = 250  # 최소 APM 요구사항
MIN_GAME_TIME_SECONDS = 300  # 최소 게임 시간 (5분)
MAX_GAME_TIME_SECONDS = 1800  # 최대 게임 시간 (30분)
```

### 학습 단계 설정
```python
# local_training/scripts/replay_learning_manager.py
min_iterations = 5  # 최소 반복 횟수
# 단계별 분배: 1-2회차(초반), 3-4회차(중반), 5회차+(후반)
```

---

## ? 검증 결과

### 품질 필터 테스트
- ? APM 필터링 정상 작동
- ? 상대방 수준 확인 정상 작동
- ? 공식 맵 확인 정상 작동
- ? 파일 무결성 검사 정상 작동

### 학습 시스템 테스트
- ? 단계별 집중 학습 정상 작동
- ? 전략 추출 정상 작동
- ? 학습 로그 기록 정상 작동
- ? 전략 DB 저장 정상 작동

### 파일 관리 테스트
- ? incompatible 폴더 이동 정상 작동
- ? 폴더 구조 정규화 정상 작동
- ? 중복 검사 정상 작동

---

**개선 완료일**: 2026년 01-13  
**작성자**: AI Assistant  
**상태**: ? **모든 고급 개선 사항 구현 완료**
