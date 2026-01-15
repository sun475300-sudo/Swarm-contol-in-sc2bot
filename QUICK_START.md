# Quick Start Guide

## ? 빠른 시작 가이드

이 프로젝트는 **실제 실행 가능한 코드**로 구성되어 있습니다. 아래 가이드를 따라 빠르게 시작할 수 있습니다.

---

## ? 사전 요구사항

1. **Python 3.10+** 설치
2. **StarCraft II** 게임 설치
3. **Git** 설치

---

## ? 5분 안에 시작하기

### 1단계: 저장소 클론
```bash
git clone https://github.com/sun475300-sudo/Swarm-control-in-sc2bot.git
cd Swarm-control-in-sc2bot
```

### 2단계: 자동 설치
**Windows:**
```powershell
.\setup.ps1
```

**Linux/macOS:**
```bash
chmod +x setup.sh
./setup.sh
```

### 3단계: 게임 실행
```bash
cd wicked_zerg_challenger
python run.py
```

게임 창이 열리며 봇이 실행됩니다! ?

---

## ? 주요 실행 명령어

### 게임 실행
```bash
# 기본 실행 (로컬 테스트)
python run.py

# 특정 맵에서 실행
python run.py --map "AbyssalReefLE"

# AI Arena 연결
python run.py --LadderServer <address> --GamePort <port>
```

### 강화학습 시작
```bash
# 통합 학습 파이프라인
cd local_training
python main_integrated.py

# 또는 배치 스크립트 사용 (Windows)
..\bat\start_training.bat
```

### 모니터링 대시보드
```bash
# FastAPI 서버 시작
cd monitoring
python dashboard_api.py

# Flask 웹 대시보드
python dashboard.py

# ngrok 터널링 포함
python start_with_ngrok.py
```

---

## ? 주요 파일 위치

| 기능 | 파일 경로 |
|------|----------|
| **메인 봇** | `wicked_zerg_challenger/wicked_zerg_bot_pro.py` |
| **실행 진입점** | `wicked_zerg_challenger/run.py` |
| **Self-Healing** | `wicked_zerg_challenger/genai_self_healing.py` |
| **강화학습** | `wicked_zerg_challenger/zerg_net.py` |
| **통합 학습** | `wicked_zerg_challenger/local_training/main_integrated.py` |
| **Monitoring API** | `wicked_zerg_challenger/monitoring/dashboard_api.py` |
| **Android 앱** | `wicked_zerg_challenger/monitoring/mobile_app_android/` |

---

## ? 실행 확인 체크리스트

- [ ] Python 3.10+ 설치됨
- [ ] StarCraft II 설치됨
- [ ] `requirements.txt` 패키지 설치됨
- [ ] 환경 변수 설정됨 (`.env` 파일)
- [ ] `python run.py` 실행 성공

---

## ? 문제 해결

### "ModuleNotFoundError: No module named 'sc2'"
```bash
pip install burnysc2
```

### "StarCraft II not found"
- Windows 레지스트리에서 자동 검색
- 또는 환경 변수 `SC2PATH` 설정

### "API key not found"
- `.env` 파일 생성
- `ENV_SETUP.md` 참조

---

## ? 다음 단계

1. [설치 가이드](SETUP.md) - 상세 설치 방법
2. [아키텍처 설명](ARCHITECTURE.md) - 시스템 구조 이해
3. [코드 구현 현황](CODE_IMPLEMENTATION_STATUS.md) - 실제 코드 상태 확인
4. [기여 가이드](CONTRIBUTING.md) - 개발 참여 방법

---

**실제 코드로 구성된 프로젝트입니다!** 바로 실행 가능합니다. ?
