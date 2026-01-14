# 🎮 위키드 저그 AI (Challenger Edition)

**스타크래프트 2 저그 종족 인공지능 에이전트**

챌린저급 실력을 목표로 설계된 모듈형 저그 AI입니다.

---

## 📋 목차

1. [프로젝트 개요](#프로젝트-개요)
2. [시스템 아키텍처](#시스템-아키텍처)
3. [설치 방법](#설치-방법)
4. [실행 방법](#실행-방법)
5. [모듈 설명](#모듈-설명)
6. [핵심 기능](#핵심-기능)
7. [튜닝 가이드](#튜닝-가이드)
8. [KPI 및 로그](#kpi-및-로그)

---

## 📖 프로젝트 개요

### 목표
- 챌린저급 실력의 저그 AI 구현
- 정찰 기반 동적 빌드오더 전환
- 지능형 마이크로 컨트롤 (카이팅, 집결, 퇴각)

### 기술 스택
- **언어**: Python 3.9+
- **라이브러리**: burnysc2 (python-sc2의 유지보수 포크)
- **IDE**: PyCharm (권장)
- **설계 패턴**: Blackboard, FSM, Potential Fields

---

## 🏗️ 시스템 아키텍처

### 통합 시스템 (Integrated System)

```
┌─────────────────────────────────────────────────────────┐
│         WickedZergBotIntegrated (RL Orchestrator)        │
│         └─ Inherits from WickedZergBotPro               │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐     │
│  │   Scout     │  │  Economy   │  │ Production │     │
│  │  Manager    │  │  Manager   │  │  Manager   │     │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘     │
│         │                │                │            │
│         └────────────────┼────────────────┘            │
│                          │                             │
│              ┌───────────▼───────────┐                 │
│              │   IntelManager        │                 │
│              │   (Blackboard)        │                 │
│              └───────────┬───────────┘                 │
│                          │                             │
│  ┌───────────▼───────────┐  ┌───────────▼───────────┐ │
│  │  Combat Manager        │  │  ZergNet (RL)         │ │
│  │  + Micro Controller    │  │  + Battle Analyzer    │ │
│  └───────────────────────┘  └───────────────────────┘ │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### 핵심 파일 구조

- **메인 봇**: `wicked_zerg_bot_integrated.py` (RL 통합 오케스트레이터)
- **기본 봇**: `wicked_zerg_bot_pro.py` (상속 기반 클래스, AI Arena 엔트리 포인트용)
- **실행**: `main_integrated.py` (통합 학습), `parallel_train_integrated.py` (병렬 학습)
- **AI Arena**: `run.py` (랫더 매치 엔트리 포인트)

### Sense-Think-Act 패턴

| 단계 | 담당 | 설명 |
|------|------|------|
| **Sense** | ScoutManager | 적 유닛/건물 감지, 위협 평가 |
| **Think** | WickedZergBot | 게임 단계 결정, 라바 우선순위 |
| **Act** | 각 Manager | 건물 건설, 유닛 생산, 전투 |

---

## 📦 설치 방법

### 1. 사전 요구사항

- [ ] 스타크래프트 2 설치
- [ ] Python 3.9+ 설치
- [ ] PyCharm 설치 (권장)

### 2. 라이브러리 설치

```bash
pip install burnysc2
```

또는 requirements.txt를 사용하여 설치:

```bash
pip install -r requirements.txt
```

### 3. 맵 설정 (중요!)

1. 스타크래프트 2 설치 폴더로 이동
   - **Windows**: `C:\Program Files (x86)\StarCraft II\`
   - **Mac**: `/Applications/StarCraft II/`

2. `Maps` 폴더 생성 (없으면)

3. [AI 맵 팩 다운로드](https://github.com/Blizzard/s2client-proto#map-packs)
   - **Ladder 2019 Season 1** 권장
   - 압축 해제 후 `Maps` 폴더에 복사

---

## 🚀 실행 방법

### ⚠️ 실행 전 필수 체크리스트

#### 1. 가상환경 및 라이브러리 확인

만약 `library not found` 에러가 발생한다면:

```bash
pip install sc2 matplotlib
```

또는 requirements.txt를 사용:

```bash
pip install -r requirements.txt
```

#### 2. 창 모드 및 성능 설정 (중요!)

3개의 게임 창이 동시에 실행되므로, **전체 화면 모드**로 설정되어 있으면 화면이 깜빡이거나 겹칠 수 있습니다.

**해결 방법:**

**비디오 설정:**
1. 스타크래프트 2 실행
2. 설정 → 비디오 → **창 모드** 선택
3. 해상도를 **낮은 해상도**로 설정 (예: 1024x768 또는 1280x720)
4. **그래픽 품질: 모두 '낮음(Low)'으로 변경**
   - 텍스처 품질: 낮음
   - 모델 품질: 낮음
   - 효과 품질: 낮음
   - 조명 품질: 낮음
   - 그림자: 끄기
   - 반사: 끄기

**프레임 제한 설정 (중요!):**
- 설정 → 비디오 → **초당 프레임 제한: 30 FPS**로 설정
- 이렇게 하면 그래픽 카드 부하가 약 1/3로 줄어듭니다

**소리 설정:**
- 설정 → 사운드 → **마스터 볼륨: 0%** (선택 사항)
- 소리를 끄면 CPU 자원을 더 확보할 수 있습니다

**창 배치:**
- 3개의 창을 나란히 배치하여 보기 편하게 설정

#### 3. 관리자 권한

스타크래프트 2 실행 시 권한 문제가 발생한다면:

- **Windows**: Cursor를 **관리자 권한으로 실행**
  - Cursor 아이콘 우클릭 → "관리자 권한으로 실행"
- 그 후 터미널에서 `python main.py` 실행

### 기본 실행

```bash
python main.py
```

### 📑 터미널 로그 보는 법

명령어를 실행하면 터미널에 다음과 같은 실시간 로그가 출력됩니다:

#### 로그 태그 설명

- **`[SYSTEM]`**: 시스템 메시지
  - 프로세스 생성, 인스턴스 시작 등 시스템 레벨 정보
  - 예: `📡 [SYSTEM] Instance 0 has been dispatched. (PID: 12345)`

- **`[ID:0]`, `[ID:1]`, `[ID:2]`**: 각 인스턴스별 로그
  - 각 게임 창(인스턴스)의 현재 상황
  - 어떤 봇이 현재 Attempt(재시도) 중인지
  - 누가 Victory(승리) 했는지 실시간으로 출력

#### 로그 예시

```
📡 [SYSTEM] Instance 0 has been dispatched. (PID: 12345)
📡 [SYSTEM] Instance 1 has been dispatched. (PID: 12346)
📡 [SYSTEM] Instance 2 has been dispatched. (PID: 12347)

[ID:0] 📊 --- ATTEMPT #1 STARTING ---
[ID:1] 📊 --- ATTEMPT #1 STARTING ---
[ID:2] 📊 --- ATTEMPT #1 STARTING ---

[ID:0] 📊 Game #1 start: AbyssalReefLE
[ID:0] 📊 SERRAL vs Terran (VeryHard)
[ID:0] 📊 Stats: 0W / 0L

[ID:1] 💀 Defeat... Restarting soon. (Total: 1 Losses)
[ID:0] ✅ !!! VICTORY !!! ATTEMPT: 1
[ID:0] ✅ Total: 1W/0L
```

### 🛑 중단하고 싶을 때

학습을 멈추고 싶다면:

1. **터미널에서 `Ctrl + C`를 누르세요**
2. 3개의 프로세스가 동시에 실행 중이므로, 모든 창이 닫힐 때까지 **1~2초 정도 기다려 주세요**
3. 시스템이 모든 인스턴스를 안전하게 종료합니다

**주의**: 강제 종료(작업 관리자 등)는 권장하지 않습니다. 데이터 손실이나 모델 저장 실패가 발생할 수 있습니다.

### 통합 시스템 실행

```bash
# 통합 학습 시스템 (RL + 병렬 학습)
python main_integrated.py

# 병렬 학습 (GPU 메모리 자동 관리)
python parallel_train_integrated.py

# AI Arena 랫더 매치
python run.py --LadderServer <address> --GamePort <port> --StartPort <port>
```

### 설정 변경

`main_integrated.py` 또는 `config.py`에서 설정 변경:

```python
MAP_NAME = "AbyssalReefLE"     # 맵 이름
DIFFICULTY = Difficulty.Medium  # 난이도
ENEMY_RACE = Race.Terran       # 상대 종족
REALTIME = False               # 최대 속도 모드 (학습용)
```

### ⚡ 성능 최적화 가이드

3개의 게임 창을 동시에 실행할 때 CPU/GPU 부하를 줄이기 위한 최적화가 적용되어 있습니다.

#### 코드 레벨 최적화 (자동 적용됨)

봇의 로직이 프레임별로 최적화되어 있습니다 (`wicked_zerg_bot_integrated.py`의 `on_step` 메서드):

- **경제/생산 로직**: 8프레임마다 실행 (CPU 부하 대폭 감소)
  - `manage_gas()` - 가스 수입 극대화
  - `produce_units()` - 유닛 생산 관리
  - `manage_upgrades()` - 업그레이드 관리
- **전투 마이크로**: 2프레임마다 실행 (반응성 유지)
  - `micro_management()` - 전투 마이크로 컨트롤
- **정보 수집/전략**: 4프레임마다 실행
- **정찰**: 4프레임마다 실행
- **여왕 관리**: 8프레임마다 실행
- **카운터 전략**: 10프레임마다 실행

#### 추가 최적화 팁

**프로세스 우선순위 조절:**
- 작업 관리자에서 SC2.exe 프로세스들의 우선순위를 '낮음'으로 설정하면 시스템이 더 부드럽게 작동합니다
- Cursor나 터미널이 버벅이는 현상을 방지할 수 있습니다

**창 개수 조절:**
- `parallel_train_integrated.py`에서 GPU 메모리를 자동으로 계산하여 최적 인스턴스 수를 결정합니다
- 수동 조절이 필요하면 `NUM_INSTANCES` 변수를 수정하세요

#### 그래픽 리소스 확보 (게임 외부 설정)

**배경 프레임 제한:**
- 스타크래프트 2 설정에서 '배경 FPS 제한'을 10으로 설정하세요
- 선택되지 않은 창의 부하를 줄여줍니다

**수직 동기화 해제:**
- 지연 시간을 줄여줍니다

**터미널 집중:**
- 게임 화면을 계속 볼 필요가 없다면 창을 최소화하거나 구석에 배치하고
- 터미널 로그(`[ID:1]`, `[ID:2]`, `[ID:3]`)에만 집중하세요

---

## 📁 모듈 설명

### 핵심 시스템 파일

| 파일 | 설명 |
|------|------|
| `wicked_zerg_bot_integrated.py` | **통합 봇** (RL 오케스트레이터, 최종 버전) |
| `wicked_zerg_bot_pro.py` | **기본 봇** (상속 기반, AI Arena 엔트리 포인트용) |
| `main_integrated.py` | 통합 학습 실행 (RL + 연속 학습) |
| `parallel_train_integrated.py` | 병렬 학습 (GPU 메모리 자동 관리) |
| `run.py` | AI Arena 랫더 매치 엔트리 포인트 |

### 매니저 모듈

| 파일 | 설명 |
|------|------|
| `intel_manager.py` | 전역 지능 (Blackboard 패턴) |
| `economy_manager.py` | 경제 및 기지 관리 |
| `production_manager.py` | 유닛 생산 관리 (자율 의사결정) |
| `combat_manager.py` | 전투 및 전략 |
| `scout_manager.py` | 정찰 및 위협 평가 |
| `micro_controller.py` | 마이크로 컨트롤 (Potential Fields) |

### 강화학습 및 분석

| 파일 | 설명 |
|------|------|
| `zerg_net.py` | 신경망 모델 (ZergNet) 및 RL 학습기 |
| `battle_analyzer.py` | 전투 분석 및 보상 함수 |
| `visualize_integrated.py` | 학습 진행 상황 시각화 |
| `self_evolve.py` | 자가 진화 (하이퍼파라미터 자동 튜닝) |

### 설정 및 유틸리티

| 파일 | 설명 |
|------|------|
| `config.py` | 설정 및 상수 정의 |
| `config_loader.py` | 학습된 파라미터 로드 (`learned_config.json`) |

---

## ⚡ 핵심 기능

### 1. 정찰 기반 동적 빌드오더

```python
# 러시 감지 → 방어 모드
if self.context["enemy_rushing"]:
    self.game_phase = GamePhase.DEFENSE

# 적 확장 감지 → 공격 타이밍
if self.enemy_expanding and self.supply_army >= 30:
    return GamePhase.ATTACK
```

### 2. 전투 그룹화 및 집결

```python
# 80% 이상 집결 시 공격
gather_ratio = near_rally.amount / army.amount
self.army_gathered = gather_ratio >= 0.8
```

### 3. 우선순위 타겟팅 (Focus Fire)

```python
TARGET_PRIORITY = {
    UnitTypeId.SIEGETANK: 10,
    UnitTypeId.MEDIVAC: 9,
    UnitTypeId.MARINE: 5,
}
```

### 4. 카이팅 (Hit & Run)

```python
if ling.weapon_cooldown > 0:
    ling.move(ling.position.towards(target, -2))
else:
    ling.attack(target)
```

### 5. 손실 기반 퇴각

```python
# 손실율 50% 이상 → 퇴각
loss_ratio = 1 - (current / initial)
if loss_ratio >= 0.5:
    self._execute_retreat()
```

### 6. 가스 조절

```python
# 발업 완료 후 가스 일꾼 미네랄로 전환
if self.speed_upgrade_done and self.time < 180:
    # 가스 일꾼 1명만 남기기
```

---

## ⚙️ 튜닝 가이드

### config.py 수정

| 설정 | 기본값 | 공격적 | 수비적 |
|------|--------|--------|--------|
| `ZERGLING_ATTACK_THRESHOLD` | 20 | 15 | 30 |
| `TOTAL_ARMY_THRESHOLD` | 60 | 40 | 80 |
| `RALLY_GATHER_PERCENT` | 0.8 | 0.6 | 0.9 |
| `RETREAT_HP_PERCENT` | 0.3 | 0.2 | 0.4 |

### 상성 로직 (Counter-Build)

`config.py`의 `COUNTER_BUILD` 딕셔너리 수정:

```python
COUNTER_BUILD = {
    EnemyRace.TERRAN: {
        "early_units": [UnitTypeId.ZERGLING, UnitTypeId.BANELING],
        "mid_units": [UnitTypeId.ROACH, UnitTypeId.RAVAGER],
        ...
    },
}
```

---

## 📊 KPI 및 로그

### 측정 항목

- **첫 저글링 생산 시간**: 빌드 오더 효율성
- **서플라이 블록 횟수**: 인구수 관리 능력
- **확장 타이밍**: 경제 운영 능력

### 로그 파일

- `game_log.txt`: 게임 이벤트 로그
- `kpi_data.csv`: KPI 데이터 (CSV 형식)

### 로그 활성화

`config.py`에서 설정:

```python
LOG_CONFIG = {
    "enabled": True,
    "log_file": "game_log.txt",
    "kpi_file": "kpi_data.csv",
}
```

---

## 🔧 트러블슈팅

### MapNotFoundException

```
맵 파일이 없거나 이름이 다릅니다.
→ Maps 폴더에 맵 파일 확인
→ main.py의 MAP_NAME 수정
```

### 스타2 실행 안 됨

```
→ 배틀넷 앱 로그인 확인
→ 게임 버전 최신 업데이트
```

### 연동 실패

```
→ pip install --upgrade burnysc2 재설치
→ Python 버전 확인 (3.9+)
```

---

## 📚 참고 자료

- [burnysc2 공식 문서](https://github.com/BurnySc2/python-sc2) (python-sc2의 유지보수 포크)
- [Blizzard SC2 API](https://github.com/Blizzard/s2client-proto)
- [AlphaStar 논문](https://www.nature.com/articles/s41586-019-1724-z)

---

## � Documentation Index

For detailed information on the latest changes and workflows:

- **[📢 LATEST UPDATES](./LATEST_UPDATES.md)**: Comprehensive summary of all recent changes (v1.1).
- **[🌿 Branching Strategy](./BRANCHING_STRATEGY.md)**: Guide to the new Git workflow.
- **[🚀 Release Notes](./RELEASE_NOTES.md)**: Quick summary of version v1.1.
- **[🌐 Permanent URL Guide](./PERMANENT_URL_GUIDE.md)**: External access setup for dashboard.

---

## �📝 라이선스

MIT License

---

## 👨‍💻 개발자

**위키드 저그 AI 프로젝트**

인공지능 전공 학습 프로젝트로 개발되었습니다.
