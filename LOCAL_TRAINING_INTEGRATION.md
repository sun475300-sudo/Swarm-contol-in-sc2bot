# Local Training 데이터 통합 가이드

**작성일**: 2026-01-15  
**목적**: `local_training` 폴더에서 학습한 데이터를 게임 실행 시 자동으로 사용하도록 설정

---

## ? 적용된 변경사항

### 1. 모델 로드 경로 우선순위 변경

**변경 전**:
- 모델을 `wicked_zerg_challenger/models/`에서만 로드

**변경 후**:
- **우선순위 1**: `local_training/models/` (학습된 모델)
- **우선순위 2**: `wicked_zerg_challenger/models/` (기본 위치, 하위 호환성)

**적용 파일**: `zerg_net.py`

---

### 2. 학습된 빌드 오더 로드 경로 변경

**변경 전**:
- `learned_build_orders.json`을 `config.py`와 같은 디렉토리에서만 찾음

**변경 후**:
- **우선순위 1**: `local_training/scripts/learned_build_orders.json` (학습된 데이터)
- **우선순위 2**: `learned_build_orders.json` (기본 위치, 하위 호환성)

**적용 파일**: `config.py`

---

### 3. 모델 저장 경로 변경

**변경 전**:
- 모델을 `wicked_zerg_challenger/models/`에 저장

**변경 후**:
- 모델을 `local_training/models/`에 저장 (학습과 일관성 유지)

**적용 파일**: `zerg_net.py`

---

## ? 파일 구조

### 학습 데이터 위치

```
wicked_zerg_challenger/
├── local_training/
│   ├── models/                    # ? 학습된 모델 저장 위치
│   │   └── zerg_net_model.pt     # 학습된 신경망 모델
│   └── scripts/
│       └── learned_build_orders.json  # ? 학습된 빌드 오더
│
└── models/                        # 하위 호환성 (fallback)
    └── zerg_net_model.pt          # (없으면 local_training에서 찾음)
```

---

## ? 동작 방식

### 1. 모델 로드 순서

1. **게임 실행 시**:
   ```python
   bot = WickedZergBotPro(train_mode=False)
   ```

2. **ReinforcementLearner 초기화**:
   - `local_training/models/zerg_net_model.pt` 확인
   - 존재하면 로드
   - 없으면 `models/zerg_net_model.pt` 확인
   - 없으면 새 모델 생성

3. **로드 성공 메시지**:
   ```
   [MODEL] Found trained model in local_training, using: .../local_training/models/zerg_net_model.pt
   [OK] Model loaded successfully: ... (device: cuda)
   ```

### 2. 빌드 오더 로드 순서

1. **config.py의 `get_learned_parameter()` 호출 시**:
   - `local_training/scripts/learned_build_orders.json` 확인
   - 존재하면 사용
   - 없으면 `learned_build_orders.json` 확인

2. **사용 예시**:
   ```python
   from config import get_learned_parameter
   lair_supply = get_learned_parameter("lair_supply", 12)  # 학습된 값 또는 기본값
   ```

---

## ? 테스트 방법

### 1. 모델 로드 테스트

```bash
cd wicked_zerg_challenger
python -c "from zerg_net import MODELS_DIR; print(f'MODELS_DIR: {MODELS_DIR}')"
```

**예상 출력**:
```
[MODEL] Using local_training/models/ directory: .../local_training/models
MODELS_DIR: .../local_training/models
```

### 2. 빌드 오더 로드 테스트

```bash
python -c "from config import get_learned_parameter; print(f'lair_supply: {get_learned_parameter(\"lair_supply\", 12)}')"
```

**예상 출력**:
```
lair_supply: 12  # local_training/scripts/learned_build_orders.json에서 로드됨
```

### 3. 실제 게임 실행 테스트

```bash
python run.py
```

**확인 사항**:
- 모델이 `local_training/models/`에서 로드되는지
- 학습된 빌드 오더가 적용되는지

---

## ? 학습 데이터 사용 확인

### 1. 모델 파일 확인

```bash
# local_training/models/에 모델이 있는지 확인
dir wicked_zerg_challenger\local_training\models\*.pt
```

### 2. 빌드 오더 파일 확인

```bash
# learned_build_orders.json이 있는지 확인
type wicked_zerg_challenger\local_training\scripts\learned_build_orders.json
```

### 3. 게임 실행 시 로그 확인

게임 실행 시 다음 메시지가 나타나야 함:
```
[MODEL] Found trained model in local_training, using: .../local_training/models/zerg_net_model.pt
[OK] Model loaded successfully: ... (device: cuda)
```

---

## ? 수동 설정 (필요 시)

### 모델 경로 강제 지정

```python
from zerg_net import ReinforcementLearner, ZergNet

# 특정 경로의 모델 사용
model = ZergNet(input_size=15, hidden_size=64, output_size=4)
learner = ReinforcementLearner(
    model,
    model_path="D:/path/to/custom/model.pt"
)
```

### 빌드 오더 경로 강제 지정

```python
from pathlib import Path
import json

# 특정 경로의 learned_build_orders.json 사용
custom_path = Path("D:/path/to/learned_build_orders.json")
with open(custom_path, 'r', encoding='utf-8') as f:
    learned_params = json.load(f)
```

---

## ?? 주의사항

### 1. 모델 버전 호환성

- 학습된 모델의 입력/출력 차원이 현재 코드와 일치해야 함
- 불일치 시 자동으로 새 모델 생성됨

### 2. 파일 권한

- `local_training/models/` 디렉토리에 쓰기 권한 필요
- 모델 저장 시 권한 오류 발생 가능

### 3. 병렬 실행

- 여러 인스턴스가 동시에 실행될 경우 파일 충돌 가능
- `instance_id`를 사용하여 별도 파일로 저장됨

---

## ? 검증 체크리스트

### 학습 데이터 통합 확인

- [x] 모델 로드 경로가 `local_training/models/` 우선 확인
- [x] 빌드 오더 로드 경로가 `local_training/scripts/` 우선 확인
- [x] 모델 저장 경로가 `local_training/models/`로 설정됨
- [x] 하위 호환성 유지 (기본 경로도 확인)

### 실행 테스트

- [ ] 모델이 `local_training/models/`에서 로드되는지 확인
- [ ] 학습된 빌드 오더가 적용되는지 확인
- [ ] 게임 실행 시 정상 작동하는지 확인

---

## ? 최종 상태

**적용 완료**: ? **local_training 폴더의 학습 데이터가 게임 실행 시 자동으로 사용됨**

**변경 사항**:
1. ? `zerg_net.py`: 모델 로드/저장 경로를 `local_training/models/`로 변경
2. ? `config.py`: 빌드 오더 로드 경로를 `local_training/scripts/`로 변경
3. ? 하위 호환성 유지 (기본 경로도 확인)

**다음 단계**: 게임 실행하여 학습된 데이터가 적용되는지 확인
