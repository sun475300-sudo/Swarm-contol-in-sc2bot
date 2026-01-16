# 리플레이 데이터 비교분석 시작 가이드

## 실행 방법

### 배치 스크립트 사용 (권장)
```bash
cd D:\Swarm-contol-in-sc2bot\wicked_zerg_challenger
bat\start_replay_comparison.bat
```

### 직접 실행
```bash
cd D:\Swarm-contol-in-sc2bot\wicked_zerg_challenger
python tools/compare_pro_vs_training_replays.py
```

## 분석 내용

이 도구는 다음과 같은 비교 분석을 수행합니다:

1. **프로 게이머 리플레이 데이터 로드**
   - 경로: `D:\replays\replays`
   - 프로 게이머 Zerg 리플레이 분석

2. **훈련 리플레이 데이터 로드**
   - `training_stats.json`
   - `build_order_comparison_history.json`
   - `learned_build_orders.json`

3. **비교 분석 항목**
   - 빌드오더 타이밍 비교
   - 성능 분석
   - 전략 차이점 분석

4. **리포트 생성**
   - 출력 경로: `local_training/comparison_reports/`
   - 상세 비교 리포트 (JSON + 텍스트)

## 결과 파일

비교 분석이 완료되면 다음 파일들이 생성됩니다:

- `comparison_reports/comparison_YYYYMMDD_HHMMSS.json`
- `comparison_reports/report_YYYYMMDD_HHMMSS.txt`

## 참고 사항

- 프로 리플레이 디렉토리와 훈련 데이터가 있어야 합니다
- 비교 분석은 시간이 걸릴 수 있습니다 (리플레이 개수에 따라)
