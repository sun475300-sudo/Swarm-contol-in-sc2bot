# 빌드오더 학습 시작 가이드

## 상태

리플레이 빌드오더 학습 스크립트에 인덴테이션 문제가 있어 실행 전 수정이 필요합니다.

## 실행 방법

### 배치 스크립트 사용
```bash
cd D:\Swarm-contol-in-sc2bot\wicked_zerg_challenger
bat\start_build_order_learning.bat
```

### 직접 실행
```bash
cd D:\Swarm-contol-in-sc2bot\wicked_zerg_challenger\local_training\scripts
python replay_build_order_learner.py
```

## 인덴테이션 문제 해결

파일의 인덴테이션 문제를 먼저 수정해야 합니다:

```bash
cd D:\Swarm-contol-in-sc2bot\wicked_zerg_challenger
python tools/apply_code_style.py --file local_training/scripts/replay_build_order_learner.py
```

또는 전체 파일 수정:

```bash
python tools/apply_code_style.py --all
```

## 필요한 패키지

- `sc2reader`: 리플레이 파일 파싱
  ```bash
  pip install sc2reader
  ```

## 리플레이 디렉토리

- 기본 경로: `D:\replays\replays`
- 프로 게이머 Zerg 리플레이 파일 (`*.SC2Replay`)이 있어야 합니다

## 학습 프로세스

1. 리플레이 파일 스캔
2. 각 리플레이에서 빌드오더 추출
3. 학습된 파라미터를 `learned_build_orders.json`에 저장
4. `config.py`에 자동 반영

## 결과

- `learned_build_orders.json`: 학습된 빌드오더 파라미터
- `strategy_db.json`: 전략 데이터베이스
- 학습된 파라미터는 자동으로 `production_manager.py`에서 사용됩니다
