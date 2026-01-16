# 로컬 트레이닝 시작 가이드

**작성일**: 2026-01-16

## 실행 방법

### 방법 1: 배치 스크립트 사용 (권장)
```bash
cd D:\Swarm-contol-in-sc2bot\wicked_zerg_challenger
bat\start_local_training.bat
```

### 방법 2: 직접 실행
```bash
cd D:\Swarm-contol-in-sc2bot\wicked_zerg_challenger
python run_with_training.py
```

또는 통합 시스템 사용:
```bash
python local_training/main_integrated.py
```

## 트레이닝 설정

### 환경 변수 (선택적)
- `INSTANCE_ID`: 인스턴스 ID (기본: 0)
- `NUM_INSTANCES`: 인스턴스 수 (기본: 1, 단일 게임 모드)
- `SHOW_WINDOW`: 게임 창 표시 (기본: true)
- `MAX_GAMES`: 최대 게임 수 (기본: 0 = 무한)
- `TORCH_NUM_THREADS`: PyTorch 스레드 수 (기본: 12)

### 트레이닝 모드

1. **단일 인스턴스 모드**
   - 한 번에 1개 게임 실행
   - 게임 창 표시 (모니터링 가능)
   - 이전 게임이 완전히 종료된 후 다음 게임 시작

2. **모니터링 서버 자동 시작**
   - 로컬 모니터링 서버 자동 시작 (포트 8001)
   - 웹/앱에서 실시간 모니터링 가능
   - 서버 URL: http://localhost:8001
   - API 문서: http://localhost:8001/docs

3. **백그라운드 학습**
   - 리플레이 분석 및 모델 학습이 백그라운드에서 실행
   - 병렬 워커 사용 (최대 2개)

## 트레이닝 프로세스

1. **게임 실행**
   - 랜덤 맵, 상대 종족, 난이도 선택
   - 봇이 학습 모드로 게임 실행
   - 게임 결과 저장 (승/패)

2. **데이터 수집**
   - 게임 상태, 전투 통계, 학습 진행률 수집
   - 리플레이 파일 저장

3. **백그라운드 처리**
   - 리플레이 분석
   - 모델 학습 및 업데이트
   - 학습된 파라미터 저장

4. **연속 학습**
   - 최대 게임 수에 도달할 때까지 반복
   - 또는 Ctrl+C로 중단

## 출력 파일

- **모델**: `local_training/models/zerg_net_model.pt`
- **리플레이**: `replays/` 폴더
- **통계**: `data/training_stats.json`
- **로그**: `logs/training_log.log`

## 모니터링

- **웹 대시보드**: http://localhost:8001/ui
- **API 문서**: http://localhost:8001/docs
- **게임 상태**: http://localhost:8001/api/game-state
- **학습 진행률**: http://localhost:8001/api/learning-progress

## 중단 방법

- `Ctrl+C`를 눌러 안전하게 중단
- 현재 게임이 종료된 후 트레이닝 루프가 중단됨
- 모니터링 서버도 자동으로 종료됨

## 참고 사항

- SC2PATH 환경 변수가 설정되어 있어야 합니다
- 게임 창이 표시되므로 모니터링이 가능합니다
- 모니터링 서버가 자동으로 시작되므로 웹/앱에서 실시간 확인 가능합니다
