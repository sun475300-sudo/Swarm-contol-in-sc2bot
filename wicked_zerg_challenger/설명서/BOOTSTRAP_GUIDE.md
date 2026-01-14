# ? 하이브리드 부트스트랩 완료 - 게임 시작 가이드

## ? 현재 상태

### ? 초기화 완료 (Bootstrap Complete)

```
프로 리플레이 학습        (self_evolution.py)
    ↓
    57개 리플레이 처리 완료
    REINFORCE 학습 완료
    모델 저장: zerg_net_model.pt (21.48 KB)
    ↓
    [OK] 초기 정책 완성
    
게임 시작 준비 (main_integrated.py)
    ↓
    자동으로 감독학습 + 강화학습 병렬 실행
    게임 0-9: 프로 리플레이 감독학습
    게임 10+: 자체 게임 강화학습
```

## ? 게임 실행 명령어

### 옵션 1: 무제한 게임 (권장 - 장시간 훈련)

```bash
python main_integrated.py
```

**동작:**
- 게임을 무한정 반복 실행
- 게임 0-9: 하이브리드 감독학습
- 게임 10+: 하이브리드 강화학습
- 모델 자동 저장
- 중단: Ctrl+C

### 옵션 2: 제한된 게임 (테스트 용)

```bash
# 테스트: 15게임 실행
set MAX_GAMES=15 && python main_integrated.py

# 또는 PowerShell
$env:MAX_GAMES = 15; python main_integrated.py

# 또는 원라이너
python -c "import os; os.environ['MAX_GAMES']='15'; exec(open('main_integrated.py').read())"
```

**동작:**
- 정확히 15개 게임 실행 후 자동 종료
- 감독학습 (0-9) + 강화학습 (10-14) 확인 가능

### 옵션 3: 초기 게임만 (감독학습 검증)

```bash
# 10게임만 실행 (감독학습 단계)
set MAX_GAMES=10 && python main_integrated.py
```

**동작:**
- 게임 0-9 감독학습 실행
- 모드 전환 메시지 없음
- 프로 정책 초기화 검증

### 옵션 4: 강화학습만 (게임 10부터)

```bash
# 게임 10 이후만 실행
set MAX_GAMES=20 && python main_integrated.py
```

**동작:**
- 게임 0-9: 감독학습 (자동)
- 게임 10: PHASE SWITCH 메시지 출력
- 게임 11-19: 강화학습 (자체 게임 데이터)

## ? 예상 실행 흐름

### 게임 0 (감독학습 시작)

```
[HYBRID] Game 0/10: SUPERVISED LEARNING phase
[HYBRID] Found 57 pro-gamer replays
[ANALYZER] Extracted 20 snapshots from integrated_dark_vs_Protoss_AbyssalReefLE_game47.SC2Replay
...
[SUPERVISED] Batch training complete - Avg Loss: 1.25
[SUPERVISED] Model saved to: D:\...\models\zerg_net_model.pt

[GAME #0] Starting...
[OK] SC2 path verified
[OK] Game process started

[VICTORY/DEFEAT] Game #0 - 1W/0L (또는 0W/1L)
```

### 게임 1-9 (감독학습 계속)

```
[HYBRID] Game 1/10: SUPERVISED LEARNING phase
...similar to Game 0...
```

### 게임 10 (전환 지점) ?

```
[HYBRID] *** PHASE SWITCH: Switching to REINFORCE at game 10 ***

[HYBRID] Game 10: REINFORCEMENT LEARNING phase (self-play)
[OK] Replay analysis complete: 10 replays trained
[REINFORCE] REINFORCE training on game 10 result

[GAME #10] Starting...
[VICTORY/DEFEAT] Game #10 - ...
```

### 게임 11+ (강화학습 최적화)

```
[HYBRID] Game 11: REINFORCEMENT LEARNING phase (self-play)
[REINFORCE] REINFORCE training on game 11 result

[HYBRID] Game 12: REINFORCEMENT LEARNING phase (self-play)
...
```

## ? 모니터링 포인트

**감독학습 단계 (0-9)**
```
? [SUPERVISED] Batch training complete - Avg Loss: X.XX
  - Loss < 2.0: 정상 수렴
  - Loss 증가 추세: 과적합 가능성

? [OK] Trained on replay: NAME
  - 각 리플레이 처리 확인
  - 오류 없음 확인
```

**강화학습 단계 (10+)**
```
? [LEARN] Learning complete - Loss: X.XX, Reward: ±1.0
  - Loss 값 확인
  - Reward: +1.0 (승리), -1.0 (패배)

? [HYBRID] Model saved
  - 게임별 모델 저장 확인
```

**성능 지표**
```
[VICTORY] Game #N - MW/LL
[DEFEAT] Game #N - MW/LL
[DRAW] Game #N - MW/LL

M = 누적 승리
L = 누적 패배
```

## ? 목표 성능

| 게임 범위 | 기대 승률 | 설명 |
|---------|---------|------|
| 0-9 (감독) | 40-50% | 프로 정책 모방 |
| 10-30 | 45-55% | 강화학습 초기 |
| 31-100 | 55-70% | 누적 학습 효과 |
| 100+ | 70%+ | 안정적 고수준 플레이 |

## ?? 하이브리드 학습 설정 변경

### 감독학습 기간 조정

```python
# main_integrated.py 라인 813
hybrid_supervised_games = 10  # 기본값 → 변경

# 예: 20게임 감독학습
hybrid_supervised_games = 20
```

### 배치 크기 조정

```python
# hybrid_learning.py 라인 330
batch_size = 32  # 기본값 → 변경

# 예: GPU 메모리 많을 때
batch_size = 64
```

## ? 파일 구조

```
d:\wicked_zerg_challenger\
├─ main_integrated.py          # 게임 실행 메인 (수정됨)
├─ hybrid_learning.py          # 하이브리드 학습 모듈 (신규)
├─ zerg_net.py                 # 신경망 + SupervisedLearner (수정됨)
├─ self_evolution.py           # 오프라인 학습 (기존)
│
├─ models/
│  └─ zerg_net_model.pt        # 초기 모델 (프로 학습됨) ?
│
├─ replays/                    # 게임 리플레이 저장
│  ├─ integrated_dark_vs_*.SC2Replay
│  ├─ integrated_reynor_vs_*.SC2Replay
│  └─ integrated_serral_vs_*.SC2Replay
│
└─ logs/                       # 학습 로그
```

## ? 트러블슈팅

### "모듈을 찾을 수 없습니다" 오류

```python
ImportError: No module named 'hybrid_learning'
```

**해결:**
```bash
# 파일 확인
dir d:\wicked_zerg_challenger\hybrid_learning.py

# 경로 확인
cd d:\wicked_zerg_challenger
python -c "import hybrid_learning; print('[OK]')"
```

### "GPU 메모리 부족" 오류

```python
CUDA out of memory
```

**해결:**
```bash
# 배치 크기 감소
# hybrid_learning.py
batch_size = 16  # 32 → 16으로 감소

# 또는 CPU 모드 강제
set CUDA_VISIBLE_DEVICES=
python main_integrated.py
```

### "리플레이 파일을 찾을 수 없습니다" 오류

```
[WARNING] No pro-gamer replays found
```

**해결:**
```bash
# replays/ 폴더 확인
dir d:\wicked_zerg_challenger\replays\*.SC2Replay | wc -l

# 최소 1개 리플레이 필요
# 없으면: mkdir replays, 리플레이 파일 추가
```

## ? 상세 문서

- **하이브리드 구현**: HYBRID_LEARNING_IMPLEMENTATION.md
- **리플레이 학습**: REPLAY_LEARNING_RECOVERY_COMPLETE.md
- **오버로드 최적화**: OVERLORD_VERIFICATION_COMPLETE.md

## ? 시작 체크리스트

- ? 모델 파일 존재: zerg_net_model.pt (21.48 KB)
- ? 하이브리드 모듈 준비: hybrid_learning.py
- ? zerg_net.py 수정: SupervisedLearner 추가
- ? main_integrated.py 수정: 하이브리드 통합
- ? SC2 경로 확인: C:\Program Files (x86)\StarCraft II
- ? 리플레이 폴더: replays/ (57개 리플레이)
- ? 모델 폴더: models/ (zerg_net_model.pt)

## ? 다음 단계

**1. 첫 실행 (15게임 테스트)**

```bash
set MAX_GAMES=15 && python main_integrated.py
```

**2. 진행 상황 모니터링**

```
게임 0-9: [HYBRID] Game N/10: SUPERVISED LEARNING 메시지 확인
게임 10: [HYBRID] *** PHASE SWITCH *** 메시지 확인
게임 11-14: [HYBRID] Game N: REINFORCEMENT LEARNING 메시지 확인
```

**3. 성능 평가**

```
- 첫 9게임 승률: 40-50% 기대
- 게임 10 이후 승률: 점진적 개선 기대
- 100게임 이후: 70%+ 달성 목표
```

**4. 장시간 학습 (최적화)**

```bash
python main_integrated.py
```

→ 자동으로 게임 반복, 모델 지속 개선

---

**부트스트랩 완료**: 2026-01-11 오후
**상태**: ? READY TO START
**다음**: python main_integrated.py 실행
