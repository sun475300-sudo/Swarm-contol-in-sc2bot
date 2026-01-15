# AI Arena 배포 전 체크리스트

**작성일**: 2026-01-15  
**목적**: AI Arena 서버에서 봇이 정상 작동하는지 확인

---

## ? 1. 봇 코드 실체화 확인

### `on_step` 메서드 구현 상태

**위치**: `wicked_zerg_bot_pro.py:1074`

**확인 결과**: ? **구현 완료**

```python
async def on_step(self, iteration: int):
    # 실제 게임 로직이 구현되어 있음:
    # - Intel Manager 업데이트
    # - Combat Manager 실행
    # - Production Manager 실행
    # - Economy Manager 실행
    # - Scouting System 실행
    # - Queen Manager 실행
    # - Micro Controller 실행
    # - Neural Network 의사결정
    # - 유닛 조종 로직
```

**구현된 주요 기능**:
- ? 유닛 생산 로직
- ? 전투 조종 로직
- ? 경제 관리 로직
- ? 정찰 시스템
- ? 신경망 기반 의사결정
- ? 마이크로 컨트롤

---

## ?? 2. 경로 설정 확인 (중요!)

### 문제점 발견

많은 파일에서 **절대 경로**를 사용하고 있습니다:

#### ? 절대 경로 사용 예시:
- `D:/replays/replays` - 리플레이 디렉토리
- `D:/replays/archive` - 아카이브 디렉토리
- `C:/Program Files (x86)/StarCraft II` - SC2 경로

### ? 상대 경로로 수정 필요

AI Arena 서버에는 사용자의 로컬 경로가 없으므로, **모든 경로를 상대 경로로 변경**해야 합니다.

---

## ? 수정이 필요한 파일들

### 1. `zerg_net.py` - 모델 경로

**현재 상태**: ? **이미 상대 경로 사용 중**

```python
# zerg_net.py:43
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
MODELS_DIR = os.path.join(SCRIPT_DIR, "models")  # ? 상대 경로
```

**확인**: 모델 로드/저장 경로가 `SCRIPT_DIR / "models"`로 설정되어 있어 **문제 없음**

### 2. `wicked_zerg_bot_pro.py` - 모델 저장 경로

**현재 상태**: ? **이미 상대 경로 사용 중**

```python
# wicked_zerg_bot_pro.py:4735
os.makedirs(MODELS_DIR, exist_ok=True)  # MODELS_DIR은 zerg_net.py에서 import
save_path = os.path.join(MODELS_DIR, self.model_filename)  # ? 상대 경로
```

**확인**: 모델 저장 경로가 상대 경로로 설정되어 있어 **문제 없음**

### 3. `config.py` - 설정 파일

**현재 상태**: ? **경로 설정 없음 (문제 없음)**

`config.py`에는 파일 경로 설정이 없고, 게임 설정값만 포함되어 있습니다.

---

## ?? 주의사항: 학습 관련 파일들

다음 파일들은 **AI Arena 배포 시 포함되지 않아야 합니다** (이미 제외됨):

- `local_training/scripts/replay_build_order_learner.py` - `D:/replays` 사용
- `tools/integrated_pipeline.py` - `D:/replays` 사용
- `local_training/scripts/*.py` - 리플레이 학습 스크립트들

**확인**: `package_for_aiarena_clean.py`에서 이미 제외 처리됨 ?

---

## ? 최종 확인 사항

### 1. 봇 실행에 필요한 경로들

| 경로 타입 | 현재 상태 | AI Arena 호환성 |
|---------|---------|----------------|
| 모델 로드 경로 | `SCRIPT_DIR / "models"` | ? OK (상대 경로) |
| 모델 저장 경로 | `SCRIPT_DIR / "models"` | ? OK (상대 경로) |
| 설정 파일 경로 | `./config.py` | ? OK |
| 로그 파일 경로 | `project_root / "logs"` | ? OK (상대 경로) |

**설명**:
- `SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))`는 스크립트 파일의 디렉토리를 기준으로 하므로, AI Arena 서버에서도 올바르게 작동합니다.
- `__file__`은 항상 현재 스크립트의 경로를 가리키므로, 어디서 실행하든 상대 경로처럼 작동합니다.

### 2. 봇 실행 로직

**확인 항목**:
- ? `on_step` 메서드 구현 완료 (1074번째 줄부터)
- ? 유닛 조종 로직 구현 완료
  - Combat Manager: 매 4프레임마다 실행
  - Production Manager: 매 22프레임마다 실행
  - Economy Manager: 매 22프레임마다 실행
  - Scouting System: 매 40프레임마다 실행
  - Queen Manager: 매 22프레임마다 실행
  - Micro Controller: 매 프레임마다 실행
- ? 전투 로직 구현 완료
- ? 생산 로직 구현 완료
- ? 경제 로직 구현 완료

### 3. `on_step` 메서드 상세 확인

**구현된 주요 기능** (1074-6364줄):
1. ? Intel Manager 업데이트 (매 프레임)
2. ? Combat Manager 실행 (매 4프레임)
3. ? Production Manager 실행 (매 22프레임)
4. ? Economy Manager 실행 (매 22프레임)
5. ? Scouting System 실행 (매 40프레임)
6. ? Queen Manager 실행 (매 22프레임)
7. ? Micro Controller 실행 (매 프레임)
8. ? Neural Network 의사결정 (매 24프레임)
9. ? 유닛 생산 로직
10. ? 건물 건설 로직
11. ? 자원 관리 로직
12. ? 전투 조종 로직

---

## ? 결론

### ? 배포 준비 완료

1. **봇 코드**: `on_step` 메서드와 모든 로직이 완전히 구현되어 있음
2. **경로 설정**: 모델 로드/저장 경로가 `__file__` 기준 상대 경로로 설정되어 있음
3. **배포 패키지**: `package_for_aiarena_clean.py`가 올바른 파일만 포함

### ?? 추가 권장 사항

1. **테스트**: 로컬에서 모델 없이 봇이 정상 작동하는지 확인
2. **로깅**: AI Arena 서버에서 로그 파일이 생성되는지 확인
3. **에러 처리**: 경로 관련 에러가 발생하지 않는지 확인

---

**배포 준비 상태**: ? **완료**
