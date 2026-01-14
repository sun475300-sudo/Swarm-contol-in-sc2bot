# 리플레이 빌드오더 학습 상태 리포트

**일시**: 2026-01-14  
**상태**: ? **학습 시작됨**

---

## ? 사전 확인 완료

### 1. 리플레이 디렉토리
- ? **경로**: `D:\replays\replays`
- ? **리플레이 파일 수**: 207개
- ? **디렉토리 존재**: 확인됨

### 2. 필수 패키지
- ? `sc2reader` - 설치됨
- ? 리플레이 로드 테스트: 성공

### 3. 학습 스크립트
- ? `replay_build_order_learner.py` - 준비됨
- ? Import 경로 수정 완료

---

## ? 리플레이 학습 실행 방법

### 방법 1: 배치 파일 사용 (권장)
```batch
cd D:\Swarm-contol-in-sc2bot\Swarm-contol-in-sc2bot\wicked_zerg_challenger
bat\start_replay_learning.bat
```

### 방법 2: 직접 Python 실행
```bash
cd D:\Swarm-contol-in-sc2bot\Swarm-contol-in-sc2bot\wicked_zerg_challenger\local_training\scripts
python replay_build_order_learner.py
```

---

## ? 학습 프로세스

### 단계별 진행
1. **리플레이 스캔**: `D:\replays\replays` 디렉토리에서 리플레이 파일 검색
2. **빌드오더 추출**: 각 리플레이에서 Zerg 플레이어의 빌드오더 추출
3. **타이밍 통계**: 추출된 빌드오더 타이밍 데이터 수집
4. **학습 파라미터 저장**: `learned_build_orders.json`에 저장
5. **Config 업데이트**: `config.py`에 학습된 파라미터 반영

### 학습 대상
- **최대 리플레이 수**: 100개 (기본값)
- **최소 반복 횟수**: 5회 (각 리플레이당)
- **완료된 리플레이**: `D:\replays\replays\completed`로 이동

---

## ? 학습 결과 파일

### 출력 파일
- **학습된 빌드오더**: `learned_build_orders.json`
- **학습 로그**: `learning_log.txt`
- **전략 데이터베이스**: `strategy_db.json`
- **학습 추적**: `.learning_tracking.json`
- **크래시 로그**: `crash_log.json` (오류 발생 시)

### 학습 파라미터
- `natural_expansion_supply`: 자연 확장 타이밍
- `gas_supply`: 가스 추출기 타이밍
- `spawning_pool_supply`: 산란못 타이밍
- `roach_warren_supply`: 바퀴 소굴 타이밍
- `hydralisk_den_supply`: 히드라리스크 둥지 타이밍
- `lair_supply`: 둥지 타이밍
- `hive_supply`: 군락 타이밍

---

## ?? 학습 설정

### 기본 설정
- **리플레이 디렉토리**: `D:\replays\replays`
- **완료 디렉토리**: `D:\replays\replays\completed`
- **최대 처리 리플레이**: 100개
- **최소 반복 횟수**: 5회

### 필터링
- **Zerg 플레이어만**: Zerg 플레이어가 있는 리플레이만 처리
- **Bad Replay 제외**: 3회 이상 크래시된 리플레이 제외
- **중복 처리 방지**: 이미 처리 중인 리플레이 건너뛰기

---

## ? 주의사항

1. **리플레이 형식**: `.SC2Replay` 파일만 처리
2. **Zerg 플레이어**: Zerg 플레이어가 없는 리플레이는 건너뜀
3. **크래시 복구**: 자동 크래시 복구 시스템 활성화
4. **디스크 공간**: 학습 결과 저장 공간 확인

---

## ? 문제 해결

### 빌드오더가 추출되지 않는 경우
1. 리플레이에 Zerg 플레이어가 있는지 확인
2. 리플레이 파일이 손상되지 않았는지 확인
3. 로그 파일 확인: `learning_log.txt`

### 크래시 발생 시
- 자동으로 크래시 로그에 기록
- 3회 이상 크래시된 리플레이는 "Bad Replay"로 표시
- 크래시 로그: `crash_log.json`

### 프로세스 확인
```powershell
# Python 프로세스 확인
Get-Process python*

# 학습 로그 확인
Get-Content D:\replays\replays\learning_log.txt -Tail 50 -Encoding UTF8
```

---

## ? 학습 완료 후

학습이 완료되면:
1. `learned_build_orders.json` 파일 생성
2. `config.py` 자동 업데이트
3. 완료된 리플레이는 `completed` 폴더로 이동
4. 자동 커밋 (AUTO_COMMIT_AFTER_TRAINING=true인 경우)

---

**상태**: ? **리플레이 빌드오더 학습 실행 중**
