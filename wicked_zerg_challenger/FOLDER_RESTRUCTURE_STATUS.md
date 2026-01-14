# 폴더 구조 재정리 작업 상태

**작성 일시**: 2026-01-14  
**작업 목표**: Single Source of Truth 원칙에 따라 루트 폴더와 `local_training/` 폴더 역할 분리

---

## ✅ 완료된 작업

### 1. 핵심 파일 루트 이동
- ✅ `spell_unit_manager.py`: `local_training/` → 루트로 이동 완료
- ✅ `rogue_tactics_manager.py`: `local_training/` → 루트로 이동 완료

---

## ⚠️ 현재 상황 및 문제점

### 현재 구조
- **루트 폴더**: 봇 소스코드 **없음** (단, 방금 이동한 2개 파일 제외)
- **`local_training/` 폴더**: **모든 봇 소스코드** 존재
  - `wicked_zerg_bot_pro.py`
  - 모든 `*_manager.py` 파일들
  - `zerg_net.py`, `config.py` 등
- **`아레나_배포/` 폴더**: 배포용 복사본 존재 (중복)

### 발견된 문제점
1. **Version Drift 위험**: `local_training/`과 `아레나_배포/`의 코드가 서로 다르게 진화 가능
2. **Import 경로 불일치**: 
   - `local_training/wicked_zerg_bot_pro.py`에서 `spell_unit_manager`, `rogue_tactics_manager`를 상대 import
   - 두 파일이 루트로 이동했으므로 import 경로 수정 필요
3. **중복 코드 존재**: 같은 파일이 여러 위치에 존재

---

## 📋 다음 단계 작업 목록

### 단계 2: `local_training/`에서 중복 파일 제거 (대규모 작업)
**주의**: 현재 루트에 봇 소스코드가 없으므로, 이 작업을 수행하려면 먼저 **모든 봇 소스코드를 루트로 이동**해야 합니다.

#### 이동 필요 파일 (루트로)
- `wicked_zerg_bot_pro.py`
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
- 기타 매니저 파일들

#### `local_training/`에 남겨둘 파일 (훈련 스크립트)
- `main_integrated.py` (훈련 실행 스크립트)
- `build_order_learner.py` (빌드 오더 학습기)
- `curriculum_manager.py` (커리큘럼 학습)
- `scripts/` 폴더 전체 (훈련 관련 스크립트)
- `data/`, `models/`, `logs/` 폴더

### 단계 3: Import 경로 수정
훈련 스크립트들이 루트 폴더의 파일을 import하도록 수정:
```python
# 수정 전
from wicked_zerg_bot_pro import WickedZergBotPro
from combat_manager import CombatManager

# 수정 후
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from wicked_zerg_bot_pro import WickedZergBotPro
from combat_manager import CombatManager
```

---

## 🤔 결정 필요 사항

현재 상태에서 다음 단계를 진행하려면:

**옵션 A**: 모든 봇 소스코드를 루트로 이동 후 중복 제거
- 작업량: 대규모 (20+ 파일 이동 + 수십 개 import 수정)
- 장점: 완전한 Single Source of Truth 구조 달성
- 단점: 작업량이 많고, 모든 import 경로 수정 필요

**옵션 B**: 현재 상태 유지 (이미 이동한 2개 파일만 루트에)
- 작업량: 최소 (import 경로만 수정)
- 장점: 빠른 완료
- 단점: 여전히 Version Drift 위험 존재

**옵션 C**: 점진적 접근 (먼저 import 경로만 수정, 전체 이동은 별도 작업으로)
- 작업량: 중간 (import 경로 수정)
- 장점: 단계적 접근, 위험 최소화
- 단점: 완전한 구조 개선은 별도 작업 필요

---

## 📝 참고 사항

- 모든 봇 소스코드를 루트로 이동하면 `local_training/`은 순수 훈련 스크립트와 데이터만 남게 됩니다
- `아레나_배포/` 폴더는 배포용이므로 별도 관리가 필요할 수 있습니다
- Import 경로 수정 시 모든 파일의 의존성을 확인해야 합니다
