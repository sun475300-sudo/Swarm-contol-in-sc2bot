# 학습 실행 요약

**작성 일시**: 2026년 01-13  
**실행 상태**: ? **학습 시작 준비 완료**  
**리플레이 파일**: 206개 확인

---

## ? 준비 완료 상태

### 리플레이 파일 확인
- ? 리플레이 디렉토리: `D:\replays\replays\`
- ? 리플레이 파일 수: **206개**
- ? 학습 시작 가능 상태

### 학습 시스템 확인
- ? 학습 횟수 카운팅 시스템 구현 완료
- ? 15차원 신경망 입력 구현 완료
- ? Bad replay 자동 제외 구현 완료
- ? 파일 충돌 방지 구현 완료

---

## ? 학습 시작 방법

### 방법 1: 배치 파일 사용 (가장 간단)

#### 리플레이 학습 시작
```batch
bat\start_replay_learning.bat
```

#### 게임 학습 시작
```batch
bat\start_game_training.bat
```

#### 전체 파이프라인 (자동화)
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

1. **리플레이 분석**
   - 206개 리플레이 파일 분석
   - Zerg 플레이어 빌드 오더 추출
   - 게임 시간, APM, 티어 검증

2. **학습 횟수 카운팅**
   - 각 리플레이당 최소 5회 학습 (하드 리퀴어먼트)
   - `learning_status.json`으로 추적
   - 5회 미만 리플레이는 유지

3. **Bad Replay 제외**
   - 3회 이상 크래시 리플레이 자동 제외
   - `crash_log.json`으로 추적

4. **학습 완료 처리**
   - 5회 이상 학습된 리플레이는 `completed/` 폴더로 이동
   - 학습된 파라미터 저장

---

### 게임 학습 프로세스

1. **게임 시작**
   - StarCraft II 게임 실행
   - 신경망 모델 로드 또는 생성 (15차원 입력)

2. **상태 수집**
   - 15차원 상태 벡터 수집
   - Self (5): Minerals, Gas, Supply, Workers, Army
   - Enemy (10): Army Count, Tech Level, Threat Level, Unit Diversity, Scout Coverage, Main Distance, Expansion Count, Resource Estimate, Upgrade Count, Air/Ground Ratio

3. **행동 선택 및 학습**
   - 신경망으로 행동 선택
   - REINFORCE 알고리즘으로 학습
   - 정책 그래디언트 업데이트

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

## ? 학습 시작 명령어

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

**준비 완료일**: 2026년 01-13  
**작성자**: AI Assistant  
**상태**: ? **206개 리플레이 파일 확인, 학습 시작 준비 완료**
