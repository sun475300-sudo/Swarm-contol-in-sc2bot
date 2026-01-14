## 리플레이 학습 시스템 점검 보고서

**작성일**: 2026년 1월 11일  
**상태**: ?? 불완전 - 리플레이 분석 모듈 누락

---

### 1. 현황 분석

#### 1.1 검토 대상 파일

| 파일 | 크기 | 상태 | 설명 |
|------|------|------|------|
| `zerg_net.py` | 732줄 | ? 완성 | 신경망 기반 강화학습 엔진 |
| `main_integrated.py` | 957줄 | ?? 부분완성 | 게임 실행 및 리플레이 처리 |
| `config.py` | - | ? 완성 | ConfigLoader (학습 파라미터) |
| `sc2/main.py` | - | ? 완성 | 게임 실행 및 리플레이 저장 |

#### 1.2 누락 파일

```
? self_evolution.py - NOT FOUND
   위치: d:\wicked_zerg_challenger\self_evolution.py (존재하지 않음)
   역할: 리플레이 분석 및 인사이트 추출
   
? extract_replay_insights.py - NOT FOUND
   위치: d:\wicked_zerg_challenger\extract_replay_insights.py (존재하지 않음)
   역할: Fallback 리플레이 분석 도구
```

---

### 2. 학습 파이프라인 분석

#### 2.1 현재 파이프라인

```
게임 실행 (sc2.main.run_game)
    ↓
    ? 게임 진행
    ↓
    ? 리플레이 저장 (replay_path)
    ↓
main_integrated.py 라인 788-796
    ↓
? self_evolution.run_self_evolution(replay_dir) - IMPORT FAIL
    ↓
? extract_replay_insights.analyze_latest_replay(replay_dir) - IMPORT FAIL
    ↓
? 리플레이 분석 중단
    ↓
? 신경망 학습 데이터 미제공
```

#### 2.2 문제점

**문제 1: 리플레이 분석 모듈 누락**
- 파일: `main_integrated.py` 라인 788-796
- 코드:
  ```python
  try:
      from self_evolution import run_self_evolution
      run_self_evolution(replay_dir)
  except ImportError:
      try:
          from extract_replay_insights import analyze_latest_replay
          analyze_latest_replay(replay_dir)
      except ImportError:
          print("[WARNING] Replay analysis modules not found, skipping analysis")
  ```
- 영향: 리플레이 분석이 건너뛰어짐 → 신경망 학습 불가

**문제 2: 학습 데이터 흐름 부재**
- 리플레이 → 분석 → 특성 추출 → 신경망 학습
- 현재: 분석 단계가 없음 → 신경망에 데이터 미제공

**문제 3: REINFORCE 학습 미구현**
- `zerg_net.py`의 `ReinforcementLearner` 클래스는 완성됨
- 하지만 실제 게임 로직에서 호출되는 부분 확인 불가
- 승리/패배 결과가 학습에 반영되는지 불명확

---

### 3. 신경망 시스템 분석

#### 3.1 아키텍처 (zerg_net.py)

**입력 특성 (5-dimension)**
```
[Minerals, Gas, Supply_Used, Drone_Count, Army_Count]
- Minerals: 0~2000 범위
- Gas: 0~2000 범위
- Supply_Used: 0~200 범위
- Drone_Count: 0~100 범위
- Army_Count: 0~200 범위
```

**출력 액션 (4-action)**
```
[ATTACK, DEFENSE, ECONOMY, TECH_FOCUS]
- Softmax를 통해 확률분포로 변환
- 최대값을 가진 액션 선택
```

**모델 구조**
```
Input (5) → FC1 (64 hidden) → ReLU → Dropout(0.2)
         → FC2 (64 hidden) → ReLU → Dropout(0.2)
         → FC3 (4 output) → Softmax
```

**학습 알고리즘: REINFORCE (Policy Gradient)**
```python
Loss = -log(prob(selected_action)) * reward

Reward 설정:
  - Victory: +1.0
  - Defeat: -1.0
  
특징:
  - 배치 처리 (최대 1000 스텝/배치)
  - GPU/CPU 자동 선택
  - 그래디언트 클리핑 (max_norm=1.0)
  - 보상 정규화 (reward scaling)
```

#### 3.2 구현 강점

? **GPU 최적화**
- CUDA 자동 감지 및 사용
- `torch.cuda.synchronize()` 명시적 동기화
- `non_blocking=True`로 비동기 전송

? **안정성**
- 파일 잠금 처리 (최대 5회 재시도)
- 모델 구조 불일치 감지 및 백업
- Device 불일치 에러 처리

? **메모리 관리**
- deque maxlen=50000으로 메모리 제한
- 배치 처리로 GPU 메모리 스파이크 방지
- 임시 파일로 원자적 저장

? **로깅**
- 상세한 디버그 정보 출력
- 에러 추적 및 재시도 로직

#### 3.3 잠재적 문제

?? **상태 정규화 누락**
- Tech Level이 제거됨 (입력 5-dimension)
- 하지만 코드는 여전히 Tech Level을 참조할 수 있음

?? **리워드 설계 단순**
- 게임 결과(승/패)만 사용
- 중간 과정 보상 없음 (sparse reward 문제)

?? **액션 선택 정책 비효율**
- argmax로 결정적 선택
- 탐색(exploration)이 없음 (모든 에피소드 동일한 액션)

---

### 4. 권장 사항

#### 4.1 우선순위 1: 리플레이 분석 모듈 복구

**필요한 기능**:
```python
# self_evolution.py (또는 유사 이름)
def run_self_evolution(replay_dir: str):
    """
    리플레이 분석 및 신경망 학습
    
    프로세스:
    1. 최신 리플레이 로드
    2. 게임 상태 추출 (minerals, gas, supply, drones, army)
    3. 액션 시퀀스 분석
    4. 승리/패배 결과 판정
    5. ReinforcementLearner.finish_episode() 호출
    """
```

#### 4.2 우선순위 2: 실제 게임 로직 통합

**확인사항**:
1. `wicked_zerg_bot_pro.py`에서 `ReinforcementLearner`가 호출되는가?
2. 매 게임 후 `finish_episode()`가 호출되는가?
3. 승리/패배 판정이 정확한가?

#### 4.3 우선순위 3: 학습 신호 개선

```python
# 현재 (sparse reward)
if game_won:
    final_reward = 1.0
else:
    final_reward = -1.0

# 개선안 (dense reward)
final_reward = (1.0 + 0.5 * win_margin_score) if game_won else -0.5
```

#### 4.4 우선순위 4: 탐색 전략 추가

```python
# 현재 (탐색 없음)
action = Action(argmax(action_probs))

# 개선안 (epsilon-greedy)
if random() < epsilon:
    action = Action(random_choice(4))
else:
    action = Action(argmax(action_probs))
```

---

### 5. 체크리스트

```
리플레이 학습 시스템 완성도 점검

[ ] 1. self_evolution.py 복구 또는 신규 생성
    - 리플레이 로드 및 분석
    - 게임 상태 추출
    - 신경망 학습 호출

[ ] 2. ReinforcementLearner 통합
    - wicked_zerg_bot_pro.py에 인스턴스 생성
    - 매 게임 후 finish_episode() 호출
    - 모델 저장 로직 확인

[ ] 3. 학습 신호 설계
    - Reward 함수 정의
    - 게임 메트릭 수집
    - Dense vs Sparse 결정

[ ] 4. 학습 루프 테스트
    - 5게임 실행
    - 모델 저장 확인
    - Loss 값 감소 확인

[ ] 5. 성능 검증
    - 10게임 이상 실행
    - Win rate 추이 모니터링
    - 신경망 행동 변화 확인
```

---

### 6. 결론

**현재 상태**: ?? 불완전

**핵심 문제**:
1. 리플레이 분석 모듈 누락 → 데이터 흐름 중단
2. 신경망 학습이 격리됨 → 실제 게임 로직 미연동

**해결책**:
1. `self_evolution.py` 복구/신규 생성
2. 신경망 학습 루프 게임 로직에 통합
3. 학습 신호 개선

**예상 복구 시간**: 2-4시간

---

**다음 단계**:
1. `self_evolution.py` 파일 검색 (git history, backup)
2. 없다면 신규 생성
3. `wicked_zerg_bot_pro.py`에서 실제 호출 확인
