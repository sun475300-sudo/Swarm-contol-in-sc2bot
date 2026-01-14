# local_training/ 폴더 정리 요약

**작업 일시**: 2026-01-14  
**작업 내용**: `local_training/` 내 봇 소스코드 파일 정리 및 import 경로 수정

---

## ? 완료된 작업

### 1. `main_integrated.py` import 경로 수정
- **파일**: `local_training/main_integrated.py`
- **수정 내용**: 루트 폴더의 봇을 참조하도록 sys.path 추가
- **상태**: ? 완료

```python
# 추가된 코드 (Line 222-225)
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from wicked_zerg_bot_pro import WickedZergBotPro as WickedZergBotIntegrated
```

---

## ?? 주의사항

### 루트 폴더에 봇 소스코드가 필요함
`main_integrated.py`가 루트 폴더의 `wicked_zerg_bot_pro`를 import하도록 수정했으므로, 루트 폴더에 봇 소스코드 파일들이 있어야 합니다.

현재 상태:
- `spell_unit_manager.py`: ? 루트에 있음
- `rogue_tactics_manager.py`: ? 루트에 있음
- `wicked_zerg_bot_pro.py`: ? 루트에 있는지 확인 필요

---

## ? 다음 단계

1. **루트 폴더에 봇 소스코드 확인**
   - `wicked_zerg_bot_pro.py`가 루트에 있는지 확인
   - 없으면 `local_training/`의 파일을 루트로 이동 필요

2. **`local_training/`의 봇 소스코드 파일 삭제** (루트로 이동 후)
   - 삭제 대상: `wicked_zerg_bot_pro.py`, `combat_manager.py`, `economy_manager.py` 등
   - 유지 대상: `main_integrated.py`, `build_order_learner.py`, `curriculum_manager.py`, `scripts/`

3. **기타 스크립트 import 경로 수정** (필요 시)
   - `local_training/scripts/` 내 스크립트들 확인

---

**작업 상태**: import 경로 수정 완료, 루트 폴더 확인 필요
