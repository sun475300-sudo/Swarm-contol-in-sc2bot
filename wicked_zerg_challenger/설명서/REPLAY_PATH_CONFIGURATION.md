# 리플레이 경로 및 훈련 결과 저장 경로 설정

**작성 일시**: 2026년 01-13  
**상태**: ✅ **설정 완료**

---

## 📋 경로 설정

### 리플레이 파일 경로
- **경로**: `D:\replays\replays`
- **설명**: 모든 저그 프로게이머의 리플레이 파일이 저장된 디렉토리
- **우선순위**: 최우선 (환경 변수보다 우선)

### 훈련 결과 저장 경로
- **경로**: `D:\replays\archive\training_YYYYMMDD_HHMMSS\`
- **설명**: 훈련 후 생성되는 JSON 파일들이 저장되는 디렉토리
- **형식**: `training_20260113_085621` (날짜_시간 형식)
- **파일**: `learned_build_orders.json`

### 완료된 리플레이 파일 경로
- **경로**: `D:\replays\replays\completed`
- **설명**: 리플레이 학습이 완료된 파일(5회 이상 학습)이 이동되는 디렉토리
- **조건**: 최소 5회 학습 완료 시 자동 이동

---

## ✅ 수정된 파일

### 1. `local_training/replay_build_order_learner.py`

#### `__init__()` 메서드
- ✅ `D:\replays\replays`를 최우선 경로로 설정
- ✅ 환경 변수 `REPLAY_ARCHIVE_DIR`보다 우선

#### `save_learned_parameters()` 메서드
- ✅ 출력 경로를 `D:\replays\archive\training_YYYYMMDD_HHMMSS\learned_build_orders.json` 형식으로 변경
- ✅ 타임스탬프 기반 디렉토리 자동 생성
- ✅ `replay_directory` 필드 추가 (원본 리플레이 경로 기록)

### 2. `local_training/integrated_pipeline.py`

#### `main()` 함수
- ✅ `D:\replays\replays`를 최우선 소스 경로로 설정
- ✅ 환경 변수 `REPLAY_SOURCE_DIR`보다 우선
- ✅ 완료된 리플레이를 `D:\replays\replays\completed`로 이동

---

## 📝 경로 우선순위

### 리플레이 파일 경로 (`replay_build_order_learner.py`)
1. ✅ **`D:\replays\replays`** (최우선 - 모든 저그 프로게이머 리플레이)
2. 환경 변수 `REPLAY_ARCHIVE_DIR`
3. `replays_archive` (상대 경로)
4. 기타 일반 경로

### 훈련 결과 저장 경로
- **자동 생성**: `D:\replays\archive\training_YYYYMMDD_HHMMSS\`
- **파일명**: `learned_build_orders.json`
- **예시**: `D:\replays\archive\training_20260113_085621\learned_build_orders.json`

### 완료된 리플레이 파일 경로
- **경로**: `D:\replays\replays\completed`
- **조건**: 최소 5회 학습 완료 시 자동 이동
- **예시**: `D:\replays\replays\completed\replay_001.SC2Replay`

---

## 🔍 JSON 파일 구조

```json
{
  "learned_parameters": {
    "spawning_pool_cost": 200.0,
    "roach_warren_cost": 150.0,
    ...
  },
  "source_replays": 100,
  "replay_directory": "D:\\replays\\replays",
  "build_orders": [...]
}
```

---

## 📊 사용 예시

### 리플레이 학습 실행
```python
from replay_build_order_learner import ReplayBuildOrderExtractor

# 자동으로 D:\replays\replays 경로 사용
extractor = ReplayBuildOrderExtractor()
learned_params = extractor.learn_from_replays(max_replays=100)

# 자동으로 D:\replays\archive\training_YYYYMMDD_HHMMSS\ 경로에 저장
extractor.save_learned_parameters(learned_params)
```

### 결과 확인
```bash
# 훈련 결과 디렉토리 확인
dir D:\replays\archive\training_20260113_085621

# JSON 파일 확인
type D:\replays\archive\training_20260113_085621\learned_build_orders.json
```

---

## ✅ 검증 체크리스트

- [x] ✅ 리플레이 경로가 `D:\replays\replays`로 설정됨
- [x] ✅ 훈련 결과가 `D:\replays\archive\training_YYYYMMDD_HHMMSS\` 형식으로 저장됨
- [x] ✅ 완료된 리플레이가 `D:\replays\replays\completed`로 이동됨
- [x] ✅ 타임스탬프 기반 디렉토리 자동 생성
- [x] ✅ JSON 파일에 원본 리플레이 경로 기록
- [x] ✅ 기존 코드와의 호환성 유지 (로컬 `learned_build_orders.json`도 저장)

---

**검토 완료일**: 2026년 01-13  
**작성자**: AI Assistant  
**상태**: ✅ **설정 완료**
