# 빠른 학습 시작 가이드

**작성 일시**: 2026년 01-13  
**가이드 범위**: 리플레이 학습 및 게임 학습 빠른 시작  
**상태**: ? **학습 시작 준비 완료**

---

## ? 빠른 시작 (3단계)

### 1단계: 리플레이 준비

**방법 A: ZIP 파일에서 자동 추출** (권장)
```batch
cd tools
python replay_lifecycle_manager.py --extract
```
- ZIP 파일 위치: `C:\Users\sun47\Downloads\`
- 추출 위치: `D:\replays\replays\`

**방법 B: 수동 복사**
- `.SC2Replay` 파일을 `D:\replays\replays\`에 복사

---

### 2단계: 리플레이 학습 시작

**방법 A: 배치 파일 사용** (가장 간단)
```batch
bat\start_replay_learning.bat
```

**방법 B: Python 직접 실행**
```bash
cd local_training
python replay_build_order_learner.py
```

**학습 프로세스**:
1. 리플레이 분석 및 빌드 오더 추출
2. 학습 횟수 카운팅 (최소 5회 강제)
3. Bad replay 자동 제외 (3회 이상 크래시)
4. 학습 완료 후 `completed/` 폴더로 이동

---

### 3단계: 게임 학습 시작

**방법 A: 배치 파일 사용**
```batch
bat\start_game_training.bat
```

**방법 B: Python 직접 실행**
```bash
cd local_training
python main_integrated.py
```

**학습 프로세스**:
1. StarCraft II 게임 실행
2. 15차원 상태 벡터 수집 (Self 5 + Enemy 10)
3. 신경망으로 행동 선택
4. REINFORCE 알고리즘으로 학습

---

## ? 전체 파이프라인 (자동화)

**한 번에 모든 단계 실행**:
```batch
bat\start_full_training.bat
```

**실행 순서**:
1. 리플레이 추출 (`replay_lifecycle_manager.py --extract`)
2. 리플레이 학습 (`replay_build_order_learner.py`)
3. 게임 학습 (`main_integrated.py`)
4. 정리 및 아카이브 (`replay_lifecycle_manager.py --cleanup`)

---

## ?? 학습 설정

### 리플레이 학습 설정

**학습 횟수**: 리플레이당 최소 5회 (하드 리퀴어먼트)
- 설정 파일: `local_training/scripts/replay_learning_manager.py`
- 추적 파일: `D:\replays\replays\learning_status.json`

**리플레이 경로**:
- 기본: `D:\replays\replays\`
- 환경 변수: `REPLAY_ARCHIVE_DIR` 또는 `REPLAY_SOURCE_DIR`

### 게임 학습 설정

**신경망 입력**: 15차원 (Self 5 + Enemy 10)
- 설정 파일: `local_training/zerg_net.py`
- 모델 저장: `local_training/models/zerg_net_model.pt`

**상태 파일 경로**:
- 인스턴스별: `stats/instance_{id}/status.json`
- 쓰기 주기: 16프레임마다 (30+ 인스턴스)

---

## ? 학습 모니터링

### 리플레이 학습 상태 확인

**학습 로그**: `D:\replays\replays\learning_log.txt`

**학습 상태 파일**:
- `D:\replays\replays\learning_status.json` - 하드 리퀴어먼트 추적
- `D:\replays\replays\.learning_tracking.json` - 학습 반복 추적

### 게임 학습 상태 확인

**상태 파일**: `stats/instance_{id}/status.json`

**내용**:
- 게임 진행 상황
- 승률
- 현재 자원 상태
- 학습 진행률

---

## ?? 주의 사항

### 리플레이 학습
- ? 리플레이당 최소 5회 학습 강제
- ? 5회 미만 리플레이는 절대 이동/삭제되지 않음
- ? Bad replay (3회 이상 크래시) 자동 제외
- ? 중복 처리 방지 (in_progress 추적)

### 게임 학습
- ? 15차원 입력 벡터 사용
- ? 인스턴스별 서브 디렉토리로 파일 충돌 방지
- ? 30+ 인스턴스 동시 실행 지원

---

## ? 학습 시작 명령어 요약

### 리플레이 학습만
```batch
bat\start_replay_learning.bat
```

### 게임 학습만
```batch
bat\start_game_training.bat
```

### 전체 파이프라인
```batch
bat\start_full_training.bat
```

---

**가이드 작성일**: 2026년 01-13  
**작성자**: AI Assistant  
**상태**: ? **학습 시작 준비 완료**
