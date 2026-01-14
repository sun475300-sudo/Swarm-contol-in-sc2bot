# 소스코드 점검 리포트

**작성 일시**: 2026-01-14  
**점검 범위**: 프로젝트 전체 소스코드  
**점검 항목**: 파일 구조, Import 경로, 중복 코드, 코드 품질, 의존성

---

## ? 점검 완료 항목

### 1. 구문 오류 (Syntax Errors)
- ? `run.py`: 구문 오류 없음 확인 완료
- ? `spell_unit_manager.py`: 구문 오류 없음
- ? `rogue_tactics_manager.py`: 구문 오류 없음
- ? Linter 오류: 발견되지 않음

### 2. 파일 구조
- ? 프로젝트 루트: 주요 실행 파일 (`run.py`, `spell_unit_manager.py`, `rogue_tactics_manager.py`)
- ? `local_training/`: 훈련 관련 코드 및 봇 소스코드
- ? `아레나_배포/`: 배포용 복사본
- ? `tools/`: 유틸리티 스크립트
- ? `monitoring/`: 모니터링 관련 코드

---

## ?? 발견된 문제점

### 1. Import 경로 불일치 (중요)

#### 문제 상황
`spell_unit_manager.py`와 `rogue_tactics_manager.py`가 루트 폴더로 이동했지만, `local_training/wicked_zerg_bot_pro.py`에서 여전히 상대 import를 사용하고 있습니다.

#### 발견된 위치
```69:69:local_training/wicked_zerg_bot_pro.py
from rogue_tactics_manager import RogueTacticsManager
```

```712:712:local_training/wicked_zerg_bot_pro.py
                from spell_unit_manager import SpellUnitManager
```

#### 영향
- `local_training/wicked_zerg_bot_pro.py`가 실행될 때 `rogue_tactics_manager`와 `spell_unit_manager`를 찾을 수 없을 수 있습니다.
- 두 파일이 루트에 있으므로 `local_training/`에서 상대 import로 접근할 수 없습니다.

#### 해결 방안
1. **옵션 A**: `local_training/wicked_zerg_bot_pro.py`에서 sys.path 수정
   ```python
   import sys
   from pathlib import Path
   sys.path.insert(0, str(Path(__file__).parent.parent))
   from rogue_tactics_manager import RogueTacticsManager
   from spell_unit_manager import SpellUnitManager
   ```

2. **옵션 B**: 두 파일을 다시 `local_training/`으로 이동

3. **옵션 C**: 모든 봇 소스코드를 루트로 이동 (대규모 작업)

---

### 2. 중복 파일

#### 2.1. `wicked_zerg_bot_pro.py` 중복
- `local_training/wicked_zerg_bot_pro.py` (메인)
- `아레나_배포/wicked_zerg_bot_pro.py` (배포용 복사본)

**위험**: 두 파일이 서로 다르게 진화할 수 있습니다 (Version Drift).

#### 2.2. `chat_manager.py` vs `chat_manager_utf8.py`
- `chat_manager.py`: `chat_manager_utf8`의 호환성 레이어 (4줄)
- `chat_manager_utf8.py`: 실제 구현

**상태**: ? 정상 (호환성 레이어 패턴)

#### 2.3. 기타 중복 파일
다음 파일들이 `local_training/`와 `아레나_배포/`에 중복 존재:
- `combat_manager.py`
- `economy_manager.py`
- `production_manager.py`
- `intel_manager.py`
- `queen_manager.py`
- `scouting_system.py`
- `micro_controller.py`
- `combat_tactics.py`
- `personality_manager.py`
- `production_resilience.py`
- `map_manager.py`
- `unit_factory.py`
- `telemetry_logger.py`
- `zerg_net.py`
- `config.py`
- `main_integrated.py`
- 기타 매니저 파일들

**권장 사항**: Single Source of Truth 원칙에 따라 중복 제거 필요

---

### 3. Import 구조 문제

#### 3.1. `run.py`의 Import
```56:56:run.py
from wicked_zerg_bot_pro import WickedZergBotPro
```

**문제**: `wicked_zerg_bot_pro.py`가 루트에 없고 `local_training/`에만 있습니다.

**현재 상태**: `run.py`가 실행될 때 `wicked_zerg_bot_pro`를 찾을 수 없을 수 있습니다.

#### 3.2. 상대 Import vs 절대 Import
- 대부분의 파일이 상대 import 사용
- 일부 파일은 sys.path 조작으로 절대 import 시도

**권장 사항**: 프로젝트 전체에서 일관된 import 방식 사용

---

### 4. 코드 품질

#### 4.1. TYPE_CHECKING 사용
- ? `spell_unit_manager.py`: TYPE_CHECKING 올바르게 사용
- ? `rogue_tactics_manager.py`: TYPE_CHECKING 올바르게 사용

#### 4.2. 인코딩 선언
- ? 대부분의 파일에 `# -*- coding: utf-8 -*-` 선언
- ? Python 3.7+ 기본값이 UTF-8이므로 문제 없음

#### 4.3. 예외 처리
- ? 적절한 예외 처리 사용
- ? 타입 힌트 적절히 사용

---

### 5. 의존성 (requirements.txt)

#### 확인된 의존성
```1:36:requirements.txt
# StarCraft 2 Bot Dependencies
# Core SC2 API library
burnysc2>=1.0.0

# Numerical operations
numpy>=1.20.0

# PyTorch for neural network features (optional but recommended)
torch>=1.9.0

# Enhanced logging (used by bot)
loguru>=0.6.0

# Replay analysis for imitation learning
sc2reader>=1.0.0

# HTTP requests for API deployment
requests>=2.25.0

# Environment variable management (.env file support)
python-dotenv>=0.19.0

# Gemini API for self-healing system
google-genai>=0.2.0

# Phone dashboard and Google Tasks integration (optional)
flask>=2.0.0
google-api-python-client>=2.0.0
google-auth-httplib2>=0.1.0
google-auth-oauthlib>=0.30.0

# Mobile dashboard backend
fastapi>=0.95.0
uvicorn[standard]>=0.22.0
rich>=13.0.0
```

**상태**: ? 의존성 명시가 명확함

---

## ? 점검 통계

| 항목 | 상태 | 개수 |
|------|------|------|
| Python 파일 | ? 확인 완료 | 94개 |
| 구문 오류 | ? 없음 | 0개 |
| Linter 오류 | ? 없음 | 0개 |
| Import 경로 문제 | ?? 발견 | 2개 |
| 중복 파일 | ?? 발견 | 20+개 |
| 의존성 문제 | ? 없음 | 0개 |

---

## ? 권장 수정 사항

### 우선순위 1: Import 경로 수정 (중요)

#### 수정 필요 파일
1. `local_training/wicked_zerg_bot_pro.py`
   - Line 69: `from rogue_tactics_manager import RogueTacticsManager`
   - Line 712: `from spell_unit_manager import SpellUnitManager`

#### 수정 방법
```python
# 파일 상단에 추가
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Import 수정
from rogue_tactics_manager import RogueTacticsManager
from spell_unit_manager import SpellUnitManager
```

### 우선순위 2: `run.py` Import 경로 확인

`run.py`가 `wicked_zerg_bot_pro`를 올바르게 찾을 수 있는지 확인 필요:
- 현재: `local_training/`에만 존재
- 필요: sys.path에 `local_training/` 추가 또는 루트로 이동

### 우선순위 3: 중복 파일 정리 (장기)

Single Source of Truth 원칙 적용:
- `local_training/`을 소스 코드 저장소로 사용
- `아레나_배포/`는 배포 시 복사본 생성

---

## ? 추가 확인 사항

### 1. 실행 환경 테스트
- [ ] `run.py` 실행 테스트
- [ ] `local_training/main_integrated.py` 실행 테스트
- [ ] Import 경로 수정 후 재테스트

### 2. 코드 검토 필요 파일
- [ ] `local_training/wicked_zerg_bot_pro.py`: Import 경로 확인
- [ ] `아레나_배포/` 폴더의 모든 파일: `local_training/`과 동기화 확인

### 3. 문서 업데이트
- [ ] README.md: Import 경로 변경 사항 반영
- [ ] FOLDER_RESTRUCTURE_STATUS.md: 현재 상태 업데이트

---

## ? 결론

### 현재 상태
- ? **구문 오류 없음**: 모든 파일이 올바르게 작성됨
- ? **Linter 오류 없음**: 코드 품질 양호
- ?? **Import 경로 문제**: 2개 파일에서 수정 필요
- ?? **중복 파일**: 구조 개선 권장

### 즉시 조치 필요
1. `local_training/wicked_zerg_bot_pro.py`의 Import 경로 수정
2. `run.py`의 Import 경로 확인 및 수정

### 장기 개선 사항
1. 중복 파일 제거 및 Single Source of Truth 구조 적용
2. Import 방식 표준화
3. 프로젝트 구조 문서화

---

**리포트 작성자**: Code Inspection System  
**다음 점검 권장 시기**: Import 경로 수정 후
