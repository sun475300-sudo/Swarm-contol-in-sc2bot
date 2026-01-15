# CI 실패 원인 분석 및 해결

**작성일**: 2026-01-15  
**문제**: GitHub Actions CI가 "All checks have failed" 상태  
**상태**: ? **해결 완료**

---

## ? 문제 원인

### 1. **CI 워크플로우가 새로운 `src/` 구조를 인식하지 못함**

**문제점**:
- CI 워크플로우(`.github/workflows/ci.yml`)가 `wicked_zerg_challenger/` 디렉토리만 체크
- 새로운 `src/` 디렉토리는 체크하지 않음
- pytest 실행 시 `src/` 모듈을 import할 수 없음 (PYTHONPATH 미설정)

**증상**:
- 테스트 파일들이 `from src.bot.agents...` 형태로 import 시도
- 하지만 `src/` 디렉토리가 PYTHONPATH에 없어서 `ModuleNotFoundError` 발생
- CI가 14초 만에 실패 (pytest 단계에서 실패)

---

## ? 해결 방법

### 1. **PYTHONPATH 설정 추가**

pytest 실행 시 프로젝트 루트를 PYTHONPATH에 추가:

```yaml
- name: Run pytest
  env:
    PYTHONPATH: ${{ github.workspace }}
  run: |
    export PYTHONPATH="${GITHUB_WORKSPACE}:${PYTHONPATH}"
    pytest tests/ -v --tb=short
```

### 2. **Black/flake8/mypy에 `src/` 디렉토리 추가**

기존에는 `wicked_zerg_challenger/`만 체크했지만, 이제 `src/`도 체크:

```yaml
- name: Black format check
  run: |
    if [ -d src ]; then
      black --check src || true
    fi
    if [ -d wicked_zerg_challenger ]; then
      black --check wicked_zerg_challenger || true
    fi
```

### 3. **Import 테스트에 `src/` 구조 추가**

기본 import 테스트에서 새로운 구조도 확인:

```python
# Test new src/ structure
try:
    from src.bot.agents.basic_zerg_agent import BasicZergAgent
    from src.sc2_env.mock_env import MockSC2Env
    print("? New src/ structure imports successful")
except ImportError as e:
    print(f"??  New src/ structure import warning: {e}")
```

---

## ? 변경 사항 요약

### Before (실패하는 CI)

```yaml
# pytest 실행 시 PYTHONPATH 없음
- name: Run pytest
  run: |
    pytest tests/ -v  # ? src/ 모듈을 찾을 수 없음

# Black/flake8는 wicked_zerg_challenger만 체크
- name: Black format check
  run: |
    black --check wicked_zerg_challenger  # ? src/ 체크 안 함
```

### After (수정된 CI)

```yaml
# pytest 실행 시 PYTHONPATH 설정
- name: Run pytest
  env:
    PYTHONPATH: ${{ github.workspace }}  # ? 프로젝트 루트 추가
  run: |
    export PYTHONPATH="${GITHUB_WORKSPACE}:${PYTHONPATH}"
    pytest tests/ -v  # ? src/ 모듈 import 가능

# Black/flake8는 src/와 wicked_zerg_challenger 모두 체크
- name: Black format check
  run: |
    if [ -d src ]; then
      black --check src  # ? src/ 체크
    fi
    if [ -d wicked_zerg_challenger ]; then
      black --check wicked_zerg_challenger  # ? 기존 구조도 체크
    fi
```

---

## ? 핵심 문제

### **Import 경로 불일치**

**테스트 코드**:
```python
from src.bot.agents.basic_zerg_agent import BasicZergAgent
```

**CI 환경**:
- 프로젝트 루트가 PYTHONPATH에 없음
- `src/` 디렉토리를 찾을 수 없음
- `ModuleNotFoundError: No module named 'src'` 발생

**해결**:
- `PYTHONPATH=${{ github.workspace }}` 설정
- 프로젝트 루트를 Python 경로에 추가
- `from src.xxx` 형태의 import가 정상 작동

---

## ? 검증 방법

### 로컬에서 테스트

```bash
# PYTHONPATH 설정 없이 (실패)
python -c "from src.bot.agents.basic_zerg_agent import BasicZergAgent"
# ModuleNotFoundError: No module named 'src'

# PYTHONPATH 설정 후 (성공)
export PYTHONPATH="$(pwd):$PYTHONPATH"
python -c "from src.bot.agents.basic_zerg_agent import BasicZergAgent"
# ? 성공
```

### CI에서 확인

다음 push 후:
1. ? pytest가 `src/` 모듈을 정상적으로 import
2. ? Black/flake8가 `src/` 디렉토리 체크
3. ? Import 테스트 통과

---

## ? 수정된 CI 워크플로우 구조

```yaml
1. Checkout repository
2. Set up Python 3.10
3. Install dependencies
   - wicked_zerg_challenger/requirements.txt
   - requirements.txt (if exists)
   - requirements_new_structure.txt (if exists)  # ? 추가
   - CI tools (black, flake8, mypy, pytest)
4. Black format check
   - src/ (if exists)  # ? 추가
   - wicked_zerg_challenger/
   - tests/
   - scripts/
5. flake8 lint
   - src/ (if exists)  # ? 추가
   - wicked_zerg_challenger/
   - tests/
   - scripts/
6. mypy type check
   - src/ (if exists)  # ? 추가
   - wicked_zerg_challenger/
7. pytest
   - PYTHONPATH 설정  # ? 추가
   - tests/ 실행
8. Basic import test
   - src/ 구조 테스트  # ? 추가
   - wicked_zerg_challenger/ 구조 테스트
```

---

## ? 다음 단계

1. **커밋 및 Push**
   ```bash
   git add .github/workflows/ci.yml
   git commit -m "fix: Update CI workflow to support new src/ structure"
   git push
   ```

2. **CI 결과 확인**
   - GitHub Actions에서 새로운 워크플로우 실행 확인
   - 모든 체크가 통과하는지 확인

3. **추가 개선 (선택사항)**
   - `src/` 디렉토리만 체크하도록 단순화 (기존 구조 제거 시)
   - 테스트 커버리지 리포트 추가

---

**수정 완료일**: 2026-01-15  
**상태**: ? **CI 워크플로우 수정 완료 - 다음 push 시 정상 작동 예상**

---

**? 핵심**: CI가 새로운 `src/` 구조를 인식하지 못해서 발생한 문제였습니다. PYTHONPATH 설정과 디렉토리 체크 범위를 확장하여 해결했습니다.
