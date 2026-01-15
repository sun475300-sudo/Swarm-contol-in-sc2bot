# CI/CD Fix - NumPy Installation Timeout

## 문제 분석

**날짜**: 2026-01-15  
**문제**: GitHub Actions에서 numpy 설치 중 작업 취소됨  
**원인**: pip가 여러 numpy 버전을 시도하다가 타임아웃 발생

---

## ? 문제 원인

### GitHub Actions 로그 분석

```
Downloading numpy-1.23.3-cp311-cp311-win_amd64.whl.metadata (2.3 kB)
Downloading numpy-1.23.2-cp311-cp311-win_amd64.whl.metadata (2.2 kB)
...
ERROR: Operation cancelled by user
Error: The operation was canceled.
```

**문제점:**
1. pip가 numpy의 여러 버전(1.23.3, 1.23.2, 1.23.1, ...)을 순차적으로 시도
2. 각 버전마다 메타데이터 다운로드 및 검증 시간 소요
3. 타임아웃 설정이 없어 무한 대기 가능
4. 작업이 취소됨

---

## ? 해결 방법

### 1. GitHub Actions 워크플로우 수정

**변경 사항:**
- ? 작업 레벨 타임아웃 추가 (`timeout-minutes: 30`)
- ? 의존성 설치 단계 타임아웃 추가 (`timeout-minutes: 15`)
- ? numpy를 먼저 설치하여 의존성 해결 시간 단축
- ? `fail-fast: false`로 다른 테스트 작업 계속 진행

**수정된 워크플로우:**
```yaml
jobs:
  test:
    runs-on: ${{ matrix.os }}
    timeout-minutes: 30  # ? 작업 전체 타임아웃
    strategy:
      fail-fast: false  # ? 하나 실패해도 다른 작업 계속
      matrix:
        os: [ubuntu-latest, windows-latest]
        python-version: ['3.10', '3.11']
    
    steps:
    - name: Install dependencies
      timeout-minutes: 15  # ? 의존성 설치 타임아웃
      run: |
        python -m pip install --upgrade pip
        cd wicked_zerg_challenger
        # ? numpy를 먼저 설치하여 의존성 해결 시간 단축
        pip install "numpy>=1.20.0,<2.0.0" --no-cache-dir || pip install numpy==1.24.3 --no-cache-dir
        pip install -r requirements.txt --no-cache-dir
        pip install pytest pytest-cov
```

### 2. requirements.txt 개선

**변경 사항:**
- ? Python 버전별 numpy 버전 명시
- ? 더 구체적인 버전 제약 조건

**수정된 requirements.txt:**
```txt
# Numerical operations
# CRITICAL: numpy<2.0.0 required for sc2 library compatibility
# Using pinned version for CI/CD stability
numpy>=1.20.0,<2.0.0; python_version<"3.12"
numpy>=1.24.0,<2.0.0; python_version>="3.12"
```

---

## ? 개선 효과

### Before (문제 상황)
- ? numpy 설치 중 여러 버전 시도
- ? 타임아웃 없이 무한 대기
- ? 작업 취소로 인한 테스트 실패

### After (수정 후)
- ? numpy를 먼저 설치하여 의존성 해결 시간 단축
- ? 타임아웃 설정으로 무한 대기 방지
- ? `fail-fast: false`로 다른 테스트 계속 진행
- ? 더 구체적인 버전 제약 조건

---

## ? 추가 최적화 방안

### 1. pip 캐시 활용 (선택사항)

```yaml
- name: Cache pip packages
  uses: actions/cache@v3
  with:
    path: ~/.cache/pip
    key: ${{ runner.os }}-pip-${{ hashFiles('**/requirements.txt') }}
    restore-keys: |
      ${{ runner.os }}-pip-
```

### 2. 의존성 설치 단계 분리

```yaml
- name: Install core dependencies
  run: |
    pip install numpy==1.24.3 --no-cache-dir
    pip install torch --no-cache-dir || pip install torch --index-url https://download.pytorch.org/whl/cpu

- name: Install remaining dependencies
  run: |
    pip install -r requirements.txt --no-cache-dir
```

---

## ? 검증 방법

### 로컬 테스트

```bash
# numpy 설치 테스트
python -m pip install --upgrade pip
pip install "numpy>=1.20.0,<2.0.0" --no-cache-dir
python -c "import numpy; print(f'NumPy {numpy.__version__} - OK')"

# 전체 의존성 설치 테스트
pip install -r requirements.txt --no-cache-dir
```

### GitHub Actions 확인

1. PR 생성 또는 push
2. Actions 탭에서 워크플로우 실행 확인
3. 각 단계별 실행 시간 확인
4. 타임아웃 발생 여부 확인

---

## ? 참고 사항

### numpy 버전 제약 조건

- **Python 3.10**: numpy 1.20.0 ~ 1.26.x 지원
- **Python 3.11**: numpy 1.23.0+ 지원
- **NumPy 2.0+**: Python 3.9+ 필요, 호환성 문제 가능

### 권장 버전

- **안정성**: `numpy==1.24.3` (Python 3.10/3.11 호환)
- **유연성**: `numpy>=1.20.0,<2.0.0` (범위 지정)

---

**수정 완료일**: 2026-01-15  
**상태**: ? GitHub Actions 워크플로우 개선 완료
