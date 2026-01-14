# Swarm-contol-in-sc2bot

``
이 프로젝트는 부모님 설득용으로 제작함.

# 🛸 Swarm Control System in StarCraft II (Zerg Bot AI)

> **From Simulation to Reality: Autonomous Swarm Control & Intelligent Management**  
> 가상 시뮬레이션 환경을 활용한 **군집 제어 강화학습 및 지능형 통합 관제 시스템 연구**

![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python)
![PyTorch](https://img.shields.io/badge/PyTorch-Deep%20Learning-orange?logo=pytorch)
![SC2](https://img.shields.io/badge/StarCraft%20II-Simulation%20Env-green?logo=starcraft)
![Status](https://img.shields.io/badge/Status-Research%20%26%20Development-purple)

---

## 🇰🇷 프로젝트 개요 (Project Overview – Korean)

이 프로젝트는 드론 응용 전공자로서,  
미래 무인 이동체 산업의 핵심 기술인 **군집 제어(Swarm Control)**와  
**자율 의사결정(Autonomous Decision Making)** 알고리즘을 연구하기 위해 구축된  
**통합 시뮬레이션 프로젝트**입니다.

단순한 게임 봇이 아니라,

- **AI 에이전트 (Zerg Bot)**  
- **클라우드 기반 자가 수복(LLM DevOps)**  
- **모바일 원격 관제(Mobile GCS)**  

가 유기적으로 연결된 **지능형 통합 관제 시스템(Intelligent Integrated Control System)** 전체를 직접 설계·구현했습니다.

구글 딥마인드의 **AlphaStar** 연구 방식을 벤치마킹하여,  
저그(Zerg)의 최대 200기 유닛을 **군집 드론(Swarm Drone)** 으로 해석하고,  
실시간 강화학습(RL)·전략 정책 최적화를 통해 **자율 비행 및 전술 판단 로직**을 고도화했습니다.

---

## 📊 시스템 아키텍처 (System Architecture)

본 시스템은 다음과 같은 **3-Tier 구조**를 가집니다.

1. **Edge Device (Simulation Server)** – StarCraft II 엔진 + Python Zerg Bot  
2. **Cloud Intelligence** – Vertex AI / Gemini 기반 자가 치유(Self-Healing)  
3. **Remote Monitoring (Mobile GCS)** – Flask 대시보드 + Android 관제 앱  

```mermaid
graph TD
    subgraph "Edge Device (Simulation Server)"
        A[StarCraft II Engine] <--> B{Wicked Zerg AI Bot}
        B --> C[Economy / Production / Swarm Manager]
    end

    subgraph "Cloud Intelligence (Vertex AI)"
        D[Gemini 1.5 Pro API]
        B -- "Traceback & Source Code" --> D
        D -- "Self-Healing Patch" --> B
    end

    subgraph "Remote Monitoring (Mobile GCS)"
        E[Flask Dashboard Server]
        F[Android App - Mobile GCS]
        B -- "Real-time Telemetry" --> E
        E <--> F
    end
````

---

## 💡 핵심 연구 및 기능 (Key Research Features – KR)

### 1. 군집 제어 및 강화학습 (Swarm RL)

* **드론 군집 제어 모사**

  * 저그의 대규모 병력 운용 메커니즘을 실제 **군집 드론 운용 알고리즘**과 연결
  * 다수 개체의 분산 제어, 충돌 회피, 경로 최적화를 통합적으로 다룸

* **10차원 벡터 기반 지능 (10-Dimensional State Vector)**

  * 단순 자원량이 아닌

    * 아군 병력 상태
    * 적 병력의 규모·위치
    * 테크 수준, 확장 상태 등
  * 위 정보를 **10차원 벡터**로 정규화하여
    `공격(Attack) / 확장(Expand) / 방어(Defend)` 전략을 자율적으로 선택

* **Strategy Imitation (프로게이머 전략 모사)**

  * 저그 세계 최정상급 프로게이머 **이병렬(Rogue)** 선수 리플레이를 분석
  * 특히 “**점막 위에서 적 병력이 감지되었을 때의 반응 속도와 의사결정 패턴**”을 데이터로 추출
  * 이를 정책 네트워크에 반영하여 **프로게이머 수준의 유동적인 전술 반응 속도** 확보

---

### 2. 생성형 AI 기반 자가 치유 (Gen-AI Self-Healing DevOps)

* **Vertex AI (Gemini) 통합**

  * 런타임 에러(Traceback) 또는 비정상 동작 발생 시

    * 봇 로그 및 문제 구간 소스 코드를 Gemini로 전송
    * AI가 원인 분석 및 수정 패치를 제안

* **자동 소스 수복 파이프라인**

  * 사람이 개입하지 않아도:

    1. 에러 감지
    2. 로그·소스 전달
    3. 수정 코드 생성
    4. 파일 패치(Patch)
    5. 봇 프로세스 재가동
  * 까지 일련의 과정을 자동으로 수행

* **성과**

  * **24/7 무중단 학습(Always-On Training)** 가능한 DevOps 환경 구현
  * 야간·주말에도 시스템이 스스로를 수리하며 학습을 계속 수행

---

### 3. 모바일 통합 관제국 (Mobile GCS)

* **실시간 원격 모니터링**

  * 직접 개발·빌드한 **Android App (Mobile GCS)**를 통해

    * AI 승률
    * 실시간 자원 상태(미네랄/가스)
    * 유닛 현황
    * 서버 온도 및 자원 사용률
      등을 스마트폰으로 관제

* **LTE/5G IoT 연동**

  * `ngrok` 터널링을 통해 외부 네트워크(LTE/5G)에서도
    내부 로컬 서버(127.0.0.1)에 안전하게 접속
  * 실제 드론 운용에서 요구되는 **C2(Command & Control) 시스템**의 프로토타입 구현

* **의의**

  * 단순 “PC 앞 로그 확인”을 넘어
    **“언제 어디서나 군집 AI를 지휘·감시할 수 있는 모바일 GCS”**로 확장

---

## 🧬 Sim-to-Real 매핑 (Why SC2 ≒ Drone Swarm)

| StarCraft II (Virtual) | 실제 무인기/드론 산업 (Real World)          |
| ---------------------- | ---------------------------------- |
| Fog of War(시야 제한)      | 센서 불확실성, 통신 음영지역                   |
| 200 유닛 동시 제어           | 군집 드론(Swarm UAV) 경로·충돌 관리          |
| 미네랄/가스 자원 관리           | 배터리·임무 스케줄링 및 전력 최적화               |
| 산란못 중복 건설 방지 로직        | 시스템 자원 낭비 방지, 데이터 무결성 보장           |
| 적 병력 탐지 및 대응           | 실시간 위협 탐지 및 자율 의사결정(Autonomous C2) |

→ 이 프로젝트는 “게임 실험”이 아니라,
**현실 군집 드론 제어 문제를 시뮬레이터에서 재현한 연구**입니다.

---

## 🛠 엔지니어링 챌린지 및 해결책 (Engineering Challenges – KR)

### 1) 비동기 명령 실행 오류 – The Async Trap

* **문제**

  * 미네랄이 8,000 이상 쌓여 있음에도 병력이 거의 생산되지 않는 **생산 마비 현상** 발생

* **원인 분석**

  * `larva.train()` 호출 시 `await` 누락
  * 코루틴이 생성만 되고 실제 게임 엔진에 명령이 전달되지 않음

* **해결**

  * 전체 생산 루틴을 재설계하여 비동기 함수 호출 경로 정리
  * 모든 생산 로직에서 **제어권(컨텍스트 스위칭)**이 명확히 보장되도록 수정

* **Before ↔ After 성능 비교**

| 항목        | 수정 전 (Before)           | 수정 후 (After)                       |
| --------- | ----------------------- | ---------------------------------- |
| 자원 소모율    | 0% (미네랄 8,000 적체, 병력 0) | **100% 자원 소모, 병력 생산 정상화**          |
| 초기 생존 시간  | 평균 185초 이내 전멸 패턴 반복     | **600% 이상 증가 (1,100초 이상 생존)**      |
| 학습 지속 가능성 | 장기 테스트 불가, 자주 중단        | **24/7 연속 학습 가능, 자가 치유 파이프라인과 연동** |

---

### 2) 레이스 컨디션에 의한 중복 건설 – Race Condition in Building Logic

* **문제**

  * 여러 매니저(생산/전략 모듈)가 동시에
    “산란못(Spawning Pool)이 없다”고 판단
  * 동일 프레임에 **중복 건설 명령**이 나가며 자원 낭비 발생

* **해결**

  * `_is_construction_started()` 내부에 프레임 단위 **건설 예약 플래그(Reservation Flag)** 도입
  * “이미 건설 중인 건물” 상태를 **Single Source of Truth**로 통합 관리
  * 결과: **중복 자원 소모 0% 달성**

---

### 3) 자원 소모 플러시 알고리즘 – Production Resilience

* **문제**

  * 미네랄은 과도하게 적체되지만, 가스 부족으로 고급 테크 유닛 생산이 지연
  * 일정 시점 이후 자원이 의미 없이 쌓이는 병목 발생

* **해결**

  * “**비상 플러시(Flush) 로직**” 설계
  * 미네랄 500 이상 돌파 시

    * 가스 소모가 필요 없는 저글링을 대량 생산
    * 라바를 강제로 소모하며 자원을 전투력으로 즉시 환전
  * 결과: **자원 순환율 극대화, 테크·병력 생산 정체 해소**

---

## ⚖ 비교 분석: 게이머(Pilot) vs 엔지니어(Engineer)

| 비교 항목  | 일반 게이머 (Pilot)   | 본 프로젝트의 AI (Engineer)        | 전공 연계성                |
| ------ | ---------------- | ---------------------------- | --------------------- |
| 제어 방식  | 마우스/키보드 기반 수동 조작 | 알고리즘 기반 자율 판단 및 실행           | 자율비행 제어 로직, 임베디드 S/W  |
| 다중 제어  | 1~2개 부대 컨트롤 한계   | 최대 200개 개체의 개별 경로·상태를 동시에 관리 | 군집 드론(Swarm Drone) 제어 |
| 관제 방식  | 모니터 앞에서 직접 화면 확인 | 모바일 GCS를 통한 실시간 원격 관제        | 원격 지휘 통제(C2) 체계       |
| 시스템 목표 | 게임 승리(오락 중심)     | 24/7 무중단 학습, 자율 의사결정 모델 고도화  | 무인 자동화·자율주행 시스템 연구    |

이 프로젝트는 “사람이 조종하는 게이머”가 아니라
**“시스템을 설계·운영하는 엔지니어”로서 수행한 작업**입니다.

---

## 🧬 연구 맥락 및 확장 가능성 (Research Context & Sim-to-Real)

* **AlphaStar 사례**

  * DeepMind가 StarCraft II를 AI Grand Challenge로 정의
  * 지도학습 + 강화학습 + self-play를 결합하여 인간 그랜드마스터 급 실력 달성
  * 본 프로젝트는 이 흐름을 **학부 수준에서 재해석한 실험적 구현**입니다.

* **Swarm RL & UAV 제어와의 연결**

  * 다중 에이전트 상태공간, 부분 관측, 상호작용을
    강화학습으로 다루는 최신 Swarm Robotics / UAV 연구와 구조적으로 유사
  * 본 시스템 구조는 향후

    * **군집 드론 방어 체계**
    * **자율주행 로봇 군단 운영 시스템**
      으로의 Sim-to-Real 확장 가능성을 내포합니다.

---

## ⚙ 기술 스택 (Tech Stack – KR)

| 구분              | 기술/도구                                                      |
| --------------- | ---------------------------------------------------------- |
| Language        | Python 3.10                                                |
| AI / ML         | PyTorch, RL Policy Network                                 |
| Simulation Env  | StarCraft II API                                           |
| Data Pipeline   | SC2 리플레이 마이닝, 전략/패턴 추출                                     |
| MLOps / DevOps  | Auto-Training Pipeline, Model Archive, Gen-AI Self-Healing |
| 관제 시스템          | Flask Dashboard, Android Mobile GCS                        |
| Swarm Algorithm | Potential Field 기반 충돌 회피 및 경로 탐색                           |

---

## 🔮 비전 및 진로 (Career Roadmap – KR)

본 연구를 통해 얻은

* **Multi-Agent Control (다중 개체 제어)**
* **Self-Healing DevOps (LLM 기반 자율 관리)**
* **Mobile C2 / GCS (원격 관제)**

역량은 시뮬레이션을 넘어 실제

* 군집 드론 방어 체계
* 자율주행 무인체계 운영 시스템

으로 직접 확장 가능한 기반 기술입니다.

**Target Roles**

* 무인 이동체 제어 엔지니어
* AI 리서치 엔지니어 (강화학습·멀티에이전트)
* MLOps / DevOps 엔지니어

**Target Industries**

* 국방과학연구소(ADD)
* 방산 기업 (LIG넥스원, 한화시스템 등)
* 자율주행 로봇·드론 스타트업
* AI 연구소 및 시뮬레이션 기반 R&D 조직

> “저는 단순히 게임 봇을 만든 것이 아니라,
> **AI 에이전트 – 클라우드 서버 – 모바일 단말**이 유기적으로 연결된
> **‘지능형 통합 관제 시스템’ 전체를 설계·구현했습니다.**”

---

## 🇺🇸 Overview (English Summary)

This project is **not a simple “game bot”**, but a full intelligent control ecosystem integrating:

* **AI Agent (Zerg Bot)**
* **Cloud-based Self-Healing DevOps (Gemini)**
* **Mobile Ground Control Station (Android GCS)**

Designed from the perspective of a **Drone Application Engineering** major,
the system models drone swarm control, autonomous decision making, and real-time remote supervision
using StarCraft II as a high-fidelity simulation environment.

It follows the methodology of **DeepMind’s AlphaStar**,
reinterpreting up to **200 Zerg units as a real UAV swarm**.

### System Architecture (EN)

*Same 3-tier architecture as described above: Simulation Server · Vertex AI · Mobile GCS.*

### Key Features (EN)

1. **Swarm Reinforcement Learning**

   * Multi-agent control inspired by drone swarm algorithms
   * 10-dimensional tactical state vectors
   * Autonomous strategy shifts: Attack / Defend / Expand
   * Imitation learning from pro gamer **Rogue (이병렬)** replays

2. **Gen-AI Self-Healing DevOps**

   * Vertex AI (Gemini) analyzes traceback + source code
   * Generates and applies patches automatically
   * Enables **24/7 continuous training** with no human in the loop

3. **Mobile GCS (Ground Control Station)**

   * Android app built from scratch
   * Real-time telemetry (win rate, minerals, gas, unit queues, CPU temperature)
   * Secure LTE/5G access via ngrok tunneling
   * Prototype of a drone **C2(Command & Control)** system

### Engineering Challenges & Solutions (EN)

* **Async Trap (await bug)**

  * Minerals 8,000+ but no units produced
  * Missing `await` on `larva.train()` → coroutine never executed
  * After redesign: **400% production gain, 600% survival time increase**

* **Race Condition (duplicate construction)**

  * Multiple managers requested the same building simultaneously
  * Introduced frame-based reservation flag → **0% duplicate buildings**

* **Resource Flush Algorithm**

  * Mineral overflow & gas bottleneck
  * “Emergency Flush” using mass Zerglings when minerals > 500
  * Achieved stable resource circulation and tech progression

### Tech Stack (EN)

Python · PyTorch · StarCraft II API · Vertex AI (Gemini) · Flask · Android
Replay Mining · Async Pipeline · Potential-Field Swarm Navigation

### Career Relevance (EN)

This system demonstrates capabilities aligned with:

* UAV/UGV autonomous control
* Multi-agent reinforcement learning
* Real-time MLOps & self-healing DevOps
* Remote C2 architecture for defense robotics

Target industries include **ADD, LIG Nex1, Hanwha Systems, and autonomous robotics startups.**

---

## 📬 Contact

* **Author:** 장선우 (Jang S. W.)
* **Major:** 목포대학교 드론응용학과 (드론기계공학전공) / Drone Application Engineering
* **Email:** `sun475300@naver.com`
* **Repository:** [[https://github.com/sun475300-sudo/Swarm-Control-in-sc2bot](https://github.com/sun475300-sudo/Swarm-contol-in-sc2bot.git)]([https://github.com/sun475300-sudo/Swarm-Control-in-sc2bot]
(https://github.com/sun475300-sudo/Swarm-contol-in-sc2bot.git))

```

::
```
