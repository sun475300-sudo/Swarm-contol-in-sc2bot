# 리플레이 학습 및 게임 학습 시작 가이드

**작성 일시**: 2026년 01-13  
**가이드 범위**: 리플레이 학습 및 게임 학습 시작 방법  
**상태**: ? **학습 시작 준비 완료**

---

## ? 학습 시작 방법

### 방법 1: 배치 파일 사용 (권장)

#### 1-1. 리플레이 학습만 시작
```batch
bat\start_replay_learning.bat
```
- 리플레이에서 빌드 오더 추출 및 학습
- 학습 횟수 카운팅 자동 적용 (최소 5회)
- Bad replay 자동 제외
- **경로**: `D:\wicked_zerg_challenger\bat\start_replay_learning.bat`

#### 1-2. 게임 학습만 시작
```batch
bat\start_game_training.bat
```
- 실제 게임에서 신경망 학습
- 15차원 입력 벡터 사용
- Reinforcement Learning (REINFORCE)
- 이병렬(Rogue) 전술 시스템 포함 (맹독충 드랍, 라바 세이빙)
- **경로**: `D:\wicked_zerg_challenger\bat\start_game_training.bat`

#### 1-3. 전체 학습 파이프라인
```batch
bat\start_full_training.bat
```
- 리플레이 추출 → 리플레이 학습 → 게임 학습 → 정리
- 완전 자동화된 파이프라인
- **경로**: `D:\wicked_zerg_challenger\bat\start_full_training.bat`

---

### 방법 2: Python 직접 실행

#### 2-1. 리플레이 학습
```bash
cd local_training
python replay_build_order_learner.py
```

#### 2-2. 게임 학습
```bash
cd local_training
python main_integrated.py
```

#### 2-3. 통합 파이프라인
```bash
cd local_training
python integrated_pipeline.py --epochs 5
```

---

## ? 학습 전 준비 사항

### 1. 리플레이 파일 준비

**리플레이 위치**:
- 기본 경로: `D:\replays\replays`
- 환경 변수: `REPLAY_ARCHIVE_DIR` 또는 `REPLAY_SOURCE_DIR`

**리플레이 준비 방법**:
1. ZIP 파일 다운로드: `C:\Users\sun47\Downloads\`
2. 자동 추출: `tools\replay_lifecycle_manager.py --extract`
3. 수동 복사: `.SC2Replay` 파일을 `D:\replays\replays\`에 복사

---

### 2. 필수 패키지 설치 확인

```bash
pip install sc2reader
pip install torch
pip install numpy
```

---

### 3. 학습 설정 확인

**학습 횟수 설정**:
- 기본값: 리플레이당 최소 5회 학습 (하드 리퀴어먼트)
- 설정 파일: `local_training/scripts/replay_learning_manager.py`
- 학습 카운트 추적: `D:\replays\replays\learning_counts.json`

**신경망 설정**:
- 입력 차원: 15차원 (Self 5 + Enemy 10)
- 설정 파일: `local_training/zerg_net.py`

---

## ? 학습 프로세스

### 리플레이 학습 프로세스

1. **리플레이 추출** (`tools/replay_lifecycle_manager.py --extract`)
   - ZIP 파일에서 Zerg 리플레이 추출
   - `D:\replays\replays\`로 이동

2. **빌드 오더 학습** (`local_training/replay_build_order_learner.py`)
   - 리플레이 분석 및 빌드 오더 추출
   - 학습 횟수 카운팅 (최소 5회) - `learning_counts.json` 추적
   - Bad replay 자동 제외 (3회 이상 크래시)
   - 학습 완료 후 `completed/` 폴더로 이동
   - **실행 방법**: `bat\start_replay_learning.bat` 또는 `cd local_training && python replay_build_order_learner.py`

3. **정리 및 아카이브** (`tools/replay_lifecycle_manager.py --cleanup`)
   - 5회 이상 학습된 리플레이만 아카이브로 이동
   - 5회 미만 리플레이는 유지

---

### 게임 학습 프로세스

1. **게임 시작** (`local_training/main_integrated.py`)
   - StarCraft II 게임 실행
   - 신경망 모델 로드 또는 생성
   - 이병렬(Rogue) 전술 시스템 활성화 (맹독충 드랍, 라바 세이빙)
   - **실행 방법**: `bat\start_game_training.bat` 또는 `cd local_training && python main_integrated.py`

2. **상태 수집** (`wicked_zerg_bot_pro.py`)
   - 15차원 상태 벡터 수집
   - Self (5) + Enemy (10) 정보

3. **행동 선택** (`zerg_net.py`)
   - 신경망으로 행동 선택
   - REINFORCE 알고리즘으로 학습

4. **보상 계산 및 업데이트**
   - 게임 결과 기반 보상
   - 정책 그래디언트 업데이트

---

## ? 학습 모니터링

### 상태 파일 확인

**위치**: `stats/instance_{id}/status.json`

**내용**:
- 게임 진행 상황
- 승률
- 현재 자원 상태
- 학습 진행률

### 학습 로그 확인

**리플레이 학습 로그**: `D:\replays\replays\learning_log.txt`

**학습 상태 추적**: 
- `D:\replays\replays\learning_status.json`
- `D:\replays\replays\.learning_tracking.json`

---

## ?? 주의 사항

### 1. 리플레이 학습 횟수
- **하드 리퀴어먼트**: 리플레이당 최소 5회 학습
- 5회 미만 리플레이는 절대 이동/삭제되지 않음
- Bad replay (3회 이상 크래시)는 자동 제외

### 2. 신경망 입력 차원
- **15차원 입력**: Self (5) + Enemy (10)
- 모델 생성 시 `input_size=15` 확인

### 3. 파일 충돌 방지
- 인스턴스별 서브 디렉토리 사용 (`stats/instance_{id}/`)
- 30+ 인스턴스 동시 실행 지원

---

## ? 빠른 시작

### 최소 설정으로 시작

1. **리플레이 준비**:
   ```bash
   # ZIP 파일을 C:\Users\sun47\Downloads\에 다운로드
   # 자동 추출
   cd tools
   python replay_lifecycle_manager.py --extract
   ```

2. **리플레이 학습 시작**:
   ```bash
   # 방법 1: 배치 파일 사용 (권장)
   bat\start_replay_learning.bat
   
   # 방법 2: Python 직접 실행
   cd local_training
   python replay_build_order_learner.py
   ```

3. **게임 학습 시작**:
   ```bash
   # 방법 1: 배치 파일 사용 (권장)
   bat\start_game_training.bat
   
   # 방법 2: Python 직접 실행
   cd local_training
   python main_integrated.py
   ```

---

## ? 학습 체크리스트

### 리플레이 학습
- [ ] 리플레이 파일이 `D:\replays\replays\`에 있는지 확인
- [ ] `sc2reader` 패키지 설치 확인
- [ ] 학습 횟수 카운팅 시스템 작동 확인
- [ ] Bad replay 자동 제외 확인

### 게임 학습
- [ ] StarCraft II 경로 설정 확인 (`SC2PATH`)
- [ ] 신경망 모델 생성 확인 (`input_size=15`)
- [ ] 상태 파일 경로 확인 (`stats/instance_{id}/`)
- [ ] GPU 사용 가능 여부 확인 (선택)
- [ ] 이병렬(Rogue) 전술 시스템 활성화 확인 (`rogue_tactics` 매니저)

---

**가이드 작성일**: 2026년 01-13  
**작성자**: AI Assistant  
**상태**: ? **학습 시작 준비 완료**

---

## ? 최근 업데이트 사항

### 파일 구조 정리 완료 (2026-01-13)
- ? 모든 배치 파일이 `bat/` 폴더로 통합됨
- ? 관리 스크립트가 `tools/` 폴더로 이동됨
- ? Import 경로 수정 완료

### 이병렬(Rogue) 전술 시스템 추가 (2026-01-13)
- ? 맹독충 드랍 전술 구현
- ? 라바 세이빙 패턴 구현
- ? 점막 기반 의사결정 구현
- ? 보상 함수 개선

자세한 내용은 `ROGUE_TACTICS_IMPLEMENTATION_GUIDE.md`를 참조하세요.
