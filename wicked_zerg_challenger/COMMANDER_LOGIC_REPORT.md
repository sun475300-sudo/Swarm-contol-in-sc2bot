# Commander Bot Logic Report (지휘관 봇 로직 보고서)

**작성일**: 2026년 01월 28일
**대상 컴포넌트**: `HierarchicalRLSystem` & `StrategyManager`

---

## 1. 개요 (Overview)

"지휘관(Commander)" 로직은 WickedZergBot의 최상위 의사결정 기구입니다.
과거에는 여러 매니저가 난립하여 지휘권이 분산되었으나, 현재는 **RL Agent(두뇌)**와 **StrategyManager(실행)**의 2계층 구조로 **통합 지휘 체계(Unified Command)**를 확립했습니다.

---

## 2. 의사결정 프로세스 (Decision Making Flow)

봇의 매 프레임(Step)마다 다음과 같은 순서로 의사결정이 이루어집니다.

### A. 관측 및 상태 인식 (Observation)
1.  **Blackboard 조회**: `IntelManager`와 `EconomyManager`가 업데이트한 전장 정보를 수집합니다.
    - 적군 위치, 아군 병력 수, 자원 보유량, 현재 시간 등.
2.  **State Vector 변환**: 수집된 정보를 0과 1 사이의 숫자로 정규화(Normalization)하여 신경망 입력 벡터로 변환합니다.

### B. 전략적 판단 (Strategic Decision) - The Brain
**`HierarchicalRLSystem`**이 입력 벡터를 분석하여 다음 중 하나의 **전략 모드(StrategyMode)**를 선택합니다.
*   `ATTACK` (공격): 적의 약점이 포착되거나 병력 우위일 때.
*   `DEFEND` (방어): 적의 공격이 감지되거나 병력을 보존해야 할 때.
*   `EXPAND` (확장): 자원이 충분하고 맵 장악이 필요할 때.
*   `SCOUT` (정찰): 적의 의도를 파악해야 할 때.

> **참고**: 현재는 학습 초기 단계이므로 Epsilon-Greedy 정책에 따라 무작위 탐험(Exploration)과 모델 예측(Exploitation)을 병행합니다.

### C. 명령 실행 (Execution) - The Hands
**`StrategyManager`**는 전달받은 StrategyMode를 구체적인 전술 명령으로 변환하여 하위 매니저에게 하달합니다.

| Strategy Mode | Action Taken |
| :--- | :--- |
| **ATTACK** | `CombatManager`에게 전군 적 본진 공격 지시 / `ProductionManager`에게 공격 유닛 생산 우선순위 상향 |
| **DEFEND** | `CombatManager`에게 본진/멀티 방어선 구축 지시 / `DefenseCoordinator`에게 방어 타워 건설 요청 |
| **EXPAND** | `BuildOrderSystem`에게 부화장(Hatchery) 건설 지시 / `IntelManager`에게 안전한 멀티 지역 탐색 요청 |

---

## 3. 학습 시스템 (Learning System)

### A. 데이터 기반 지식 (Commander Knowledge)
봇은 백지상태에서 시작하지 않습니다. `commander_knowledge.json` 파일에 저장된 "선험적 지식"을 탑재하고 출격합니다.
- **초반 빌드**: 12 Pool, 16 Hatch 등 정석 빌드를 완벽하게 수행합니다.
- **유닛 비율**: 프로 리플레이 데이터(50+ 게임)에서 추출한 "황금 비율" (드론 60 : 병력 40)을 기본값으로 사용합니다.

### B. 적응형 학습 (Adaptive Learning)
게임이 진행되거나 종료될 때마다 경험을 축적합니다.
- **Reward Function (보상 함수)**:
    - 적 유닛 처치 (+), 승리 (+), 자원 낭비 (-)
    - 이 보상값을 통해 어떤 상황에서 어떤 판단이 좋았는지를 신경망(Neural Network)에 학습시킵니다.
- **Adaptive Learning Rate**: 학습 성과가 좋지 않으면 학습률을 자동으로 높여 더 과감하게 전략을 수정합니다.

---

## 4. 핵심 로직 파일 구조

*   `local_training/improved_hierarchical_rl.py`: **RL Brain 핵심 로직**. 신경망 모델과 의사결정 알고리즘(`step` 함수)이 들어있습니다.
*   `strategy/strategy_manager.py`: **명령 실행기**. RL의 추상적 명령을 구체적 API 호출로 변환합니다.
*   `data/commander_knowledge.json`: **전략 데이터베이스**. 빌드 오더와 유닛 비율 데이터가 저장됨.
*   `bot_step_integration.py`: **통합 제어**. 매 프레임마다 위의 요소들을 순서대로 호출하고 조율합니다.

---

## 5. 결론

현재 지휘관 봇은 **"데이터로 배우고, 냉철하게 판단하며, 일사불란하게 움직이는"** 시스템을 갖추었습니다.
이제 남은 것은 실전(Ladder) 경험을 통해 "언제 공격해야 이기는가"에 대한 직관(Neural Network Weights)을 날카롭게 다듬는 것뿐입니다.
