# 리플레이 학습 시작 가이드

## 실행 방법

### 방법 1: 배치 스크립트 사용 (권장)
```bash
cd D:\Swarm-contol-in-sc2bot\wicked_zerg_challenger
bat\start_replay_learning.bat
```

### 방법 2: 직접 실행
```bash
cd D:\Swarm-contol-in-sc2bot\wicked_zerg_challenger\local_training\scripts
python replay_build_order_learner.py
```

## 주요 사항

1. **리플레이 디렉토리**: `D:\replays\replays`
   - 프로 게이머 Zerg 리플레이 파일들이 있어야 합니다
   - 파일 형식: `*.SC2Replay`

2. **학습 프로세스**:
   - 각 리플레이를 5회 분석 (조기/중반/후반 게임)
   - 빌드 오더 학습 및 파라미터 추출
   - 학습된 데이터는 `learned_build_orders.json`에 저장

3. **실시간 진행 상황**:
   - 진행 상황이 실시간으로 표시됩니다
   - `Processing replay X/100...` 형태로 진행률 표시

## 필요한 패키지

- `sc2reader`: 리플레이 파일 파싱
  ```bash
  pip install sc2reader
  ```

## 참고 사항

- 학습이 완료된 리플레이(5회 이상 분석)는 자동으로 `completed` 폴더로 이동됩니다
- 학습 결과는 `local_training/scripts/learned_build_orders.json`에 저장됩니다
- 학습된 파라미터는 자동으로 `config.py`에 반영됩니다

## 문제 해결

### 인덴테이션 에러가 발생할 경우
파일에 인덴테이션 문제가 있을 수 있습니다. 다음 명령으로 스타일을 통일하세요:
```bash
python tools/apply_code_style.py --file local_training/scripts/replay_build_order_learner.py
```

### 리플레이 파일을 찾을 수 없을 경우
- `D:\replays\replays` 경로에 리플레이 파일이 있는지 확인
- 환경 변수 `REPLAY_ARCHIVE_DIR`을 설정하여 다른 경로 지정 가능
