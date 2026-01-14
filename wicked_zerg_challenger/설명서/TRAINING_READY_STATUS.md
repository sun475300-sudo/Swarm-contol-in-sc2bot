# 학습 시작 준비 상태 확인

**작성 일시**: 2026년 01-13  
**확인 범위**: 리플레이 학습 및 게임 학습 시작 준비 상태  
**상태**: ? **학습 시작 준비 완료**

---

## ? 학습 시스템 준비 완료 확인

### 1. ? 리플레이 학습 시스템

#### 핵심 기능 구현 완료
- ? 학습 횟수 카운팅 하드 리퀴어먼트 (최소 5회)
- ? Bad replay 자동 제외 (3회 이상 크래시)
- ? 중복 처리 방지 (in_progress 추적)
- ? Stale session 자동 복구 (1시간 이상)

#### 파일 위치
- ? `local_training/replay_build_order_learner.py` - 메인 학습 스크립트
- ? `local_training/scripts/replay_learning_manager.py` - 학습 반복 추적
- ? `local_training/scripts/learning_status_manager.py` - 하드 리퀴어먼트 강제
- ? `local_training/scripts/replay_crash_handler.py` - 크래시 처리

#### 리플레이 경로
- 기본 경로: `D:\replays\replays\`
- 환경 변수: `REPLAY_ARCHIVE_DIR` 또는 `REPLAY_SOURCE_DIR`
- 자동 경로 감지: `replay_build_order_learner.py`에서 자동 감지

---

### 2. ? 게임 학습 시스템

#### 핵심 기능 구현 완료
- ? 15차원 입력 벡터 (Self 5 + Enemy 10)
- ? 신경망 모델 (`ZergNet`, `input_size=15`)
- ? REINFORCE 알고리즘
- ? 인스턴스별 서브 디렉토리 (파일 충돌 방지)

#### 파일 위치
- ? `local_training/main_integrated.py` - 메인 게임 학습 스크립트
- ? `local_training/zerg_net.py` - 신경망 모델
- ? `local_training/wicked_zerg_bot_pro.py` - 봇 메인 로직

#### 상태 파일 경로
- 인스턴스별: `stats/instance_{id}/status.json`
- 쓰기 주기: 16프레임마다 (30+ 인스턴스)

---

### 3. ? 학습 시작 스크립트

#### 배치 파일 생성 완료
- ? `bat/start_replay_learning.bat` - 리플레이 학습 시작
- ? `bat/start_game_training.bat` - 게임 학습 시작
- ? `bat/start_full_training.bat` - 전체 파이프라인

#### 실행 방법
```batch
# 리플레이 학습만
bat\start_replay_learning.bat

# 게임 학습만
bat\start_game_training.bat

# 전체 파이프라인
bat\start_full_training.bat
```

---

## ? 학습 시작 전 체크리스트

### 필수 준비 사항
- [ ] 리플레이 파일 준비 (`D:\replays\replays\` 또는 환경 변수 설정)
- [ ] `sc2reader` 패키지 설치 확인 (`pip install sc2reader`)
- [ ] `torch` 패키지 설치 확인 (`pip install torch`)
- [ ] StarCraft II 경로 설정 확인 (`SC2PATH` 환경 변수)

### 선택 준비 사항
- [ ] GPU 사용 가능 여부 확인 (선택)
- [ ] 모니터링 대시보드 실행 (선택)

---

## ? 학습 시작 방법

### 방법 1: 배치 파일 사용 (권장)

#### 리플레이 학습 시작
```batch
bat\start_replay_learning.bat
```

#### 게임 학습 시작
```batch
bat\start_game_training.bat
```

#### 전체 파이프라인
```batch
bat\start_full_training.bat
```

---

### 방법 2: Python 직접 실행

#### 리플레이 학습
```bash
cd local_training
python replay_build_order_learner.py
```

#### 게임 학습
```bash
cd local_training
python main_integrated.py
```

---

## ? 학습 프로세스

### 리플레이 학습 프로세스

1. **리플레이 추출** (선택)
   ```bash
   cd tools
   python replay_lifecycle_manager.py --extract
   ```

2. **빌드 오더 학습**
   ```bash
   cd local_training
   python replay_build_order_learner.py
   ```
   - 리플레이 분석 및 빌드 오더 추출
   - 학습 횟수 카운팅 (최소 5회)
   - Bad replay 자동 제외
   - 학습 완료 후 `completed/` 폴더로 이동

3. **정리 및 아카이브** (선택)
   ```bash
   cd tools
   python replay_lifecycle_manager.py --cleanup
   ```
   - 5회 이상 학습된 리플레이만 아카이브로 이동

---

### 게임 학습 프로세스

1. **게임 시작**
   ```bash
   cd local_training
   python main_integrated.py
   ```
   - StarCraft II 게임 실행
   - 신경망 모델 로드 또는 생성

2. **학습 진행**
   - 15차원 상태 벡터 수집
   - 신경망으로 행동 선택
   - REINFORCE 알고리즘으로 학습
   - 상태 파일 업데이트 (`stats/instance_{id}/status.json`)

---

## ? 학습 모니터링

### 리플레이 학습 모니터링

**학습 로그**: `D:\replays\replays\learning_log.txt`

**학습 상태 파일**:
- `D:\replays\replays\learning_status.json` - 하드 리퀴어먼트 추적
- `D:\replays\replays\.learning_tracking.json` - 학습 반복 추적
- `D:\replays\replays\crash_log.json` - 크래시 추적

### 게임 학습 모니터링

**상태 파일**: `stats/instance_{id}/status.json`

**내용**:
- 게임 진행 상황
- 승률
- 현재 자원 상태
- 학습 진행률

---

## ? 준비 완료 상태

### 시스템 준비
- ? 학습 횟수 카운팅 하드 리퀴어먼트 구현
- ? 15차원 신경망 입력 구현
- ? Bad replay 자동 제외 구현
- ? 파일 충돌 방지 구현
- ? 학습 시작 스크립트 생성

### 문서 준비
- ? `설명서/TRAINING_START_GUIDE.md` - 상세 학습 시작 가이드
- ? `설명서/QUICK_START_TRAINING.md` - 빠른 시작 가이드
- ? `설명서/TRAINING_READY_STATUS.md` - 준비 상태 확인 (이 문서)

---

**준비 완료일**: 2026년 01-13  
**작성자**: AI Assistant  
**상태**: ? **학습 시작 준비 완료**
