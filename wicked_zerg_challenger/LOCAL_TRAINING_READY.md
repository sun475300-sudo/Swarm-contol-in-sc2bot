# 로컬 트레이닝 시작 준비 완료

**작성일**: 2026-01-16

## 준비 상태

로컬 트레이닝 시작 스크립트가 준비되었습니다.

### 생성된 파일

1. **`bat/start_local_training.bat`**: 로컬 트레이닝 시작 배치 스크립트
2. **`LOCAL_TRAINING_START.md`**: 상세 실행 가이드

## 실행 방법

### 배치 스크립트 사용 (권장)
```bash
cd D:\Swarm-contol-in-sc2bot\wicked_zerg_challenger
bat\start_local_training.bat
```

### 직접 실행
```bash
cd D:\Swarm-contol-in-sc2bot\wicked_zerg_challenger
python run_with_training.py
```

## 트레이닝 로직

### 통합 트레이닝 시스템
- **단일 인스턴스 모드**: 한 번에 1개 게임 실행
- **시각 모드**: 게임 창 표시 (모니터링 가능)
- **로컬 모니터링 서버**: 자동 시작 (포트 8001)
- **백그라운드 학습**: 리플레이 분석 및 모델 학습

### 주요 기능
1. 연속 게임 실행 (무한 또는 제한)
2. 랜덤 맵/상대 종족/난이도 선택
3. 적응형 난이도 조정
4. 실시간 모니터링 (웹/앱)
5. 자동 모델 저장

## 환경 변수 (선택적)

```bash
set INSTANCE_ID=0
set NUM_INSTANCES=1
set SHOW_WINDOW=true
set MAX_GAMES=0  # 0 = 무한
set TORCH_NUM_THREADS=12
```

## 모니터링

- **웹 대시보드**: http://localhost:8001/ui
- **API 문서**: http://localhost:8001/docs
- **게임 상태**: http://localhost:8001/api/game-state
- **학습 진행률**: http://localhost:8001/api/learning-progress

## 참고 사항

- 일부 파일에 인덴테이션 문제가 있을 수 있습니다
- 실행 전 스타일 통일화 권장:
  ```bash
  python tools/apply_code_style.py --all
  ```
- SC2PATH 환경 변수가 설정되어 있어야 합니다

## 출력 파일

- **모델**: `local_training/models/zerg_net_model.pt`
- **리플레이**: `replays/` 폴더
- **통계**: `data/training_stats.json`
- **로그**: `logs/training_log.log`
