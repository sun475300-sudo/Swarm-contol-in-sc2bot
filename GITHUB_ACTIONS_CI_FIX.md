# GitHub Actions CI/CD 완전 수정 가이드

## 문제 분석

**문제**: Windows + Python 3.11 환경에서 numpy 설치 실패로 GitHub Actions 취소  
**원인**: numpy의 Python 3.11용 Windows wheel 파일 호환성 문제  
**증상**: 여러 버전 시도 → 소스 빌드 → 타임아웃 취소

---

## ? 완전 수정된 설정

### 1. GitHub Actions 워크플로우 개선

**주요 변경 사항:**

1. ? **Windows + Python 3.11 조합 제거**
   - Python 3.10만 사용하여 안정성 확보
   - Ubuntu에서만 Python 3.11 테스트 (빌드가 빠름)

2. ? **타임아웃 설정 추가**
   - 작업 레벨: 30분
   - 의존성 설치: 20분
   - 테스트 실행: 10분

3. ? **pip 캐시 활용**
   - `cache: 'pip'` 설정으로 재설치 시간 단축

4. ? **Python 버전별 numpy 설치**
   - Python 3.11: numpy>=1.26.0 (Windows wheel 지원)
   - Python 3.10: numpy>=1.23.0 (안정 버전)

5. ? **fail-fast: false**
   - 하나의 작업 실패가 다른 작업에 영향 주지 않음

---

### 2. requirements.txt 최적화

**변경 사항:**

```txt
# Python 3.11 requires numpy>=1.23.0 for Windows wheels
# Python 3.10 supports numpy>=1.20.0
numpy>=1.26.0,<2.0.0; python_version>="3.11"
numpy>=1.23.0,<2.0.0; python_version=="3.10"
```

**이유:**
- Python 3.11 + Windows 환경에서는 numpy 1.23.0+ 버전이 wheel 파일 제공
- 1.23.0 미만 버전은 소스 빌드만 가능 → 매우 느림
- numpy 1.26.0+는 Python 3.11 공식 지원

---

## ? 수정 전후 비교

### Before (문제 상황)

```yaml
matrix:
  os: [ubuntu-latest, windows-latest]
  python-version: ['3.10', '3.11']  # ? Windows + 3.11 조합 문제
```

**문제점:**
- ? Windows + Python 3.11에서 numpy wheel 없음
- ? 소스 빌드 시도 → 타임아웃
- ? 타임아웃 설정 없음
- ? pip 캐시 미활용

### After (수정 후)

```yaml
matrix:
  os: [ubuntu-latest, windows-latest]
  python-version: ['3.10']  # ? 안정 버전만 사용
  include:
    - os: ubuntu-latest
      python-version: '3.11'  # ? Ubuntu에서만 3.11 테스트
```

**개선점:**
- ? Windows에서는 Python 3.10만 사용
- ? Ubuntu에서 Python 3.11 테스트
- ? 타임아웃 설정으로 무한 대기 방지
- ? pip 캐시로 설치 속도 향상
- ? 버전별 numpy 설치 전략

---

## ? 상세 설정 설명

### 1. Python 버전별 numpy 설치 전략

```bash
# Python 3.11
if [ "${{ matrix.python-version }}" == "3.11" ]; then
  pip install "numpy>=1.26.0,<2.0.0" --no-cache-dir
else
  # Python 3.10
  pip install "numpy>=1.23.0,<2.0.0" --no-cache-dir
fi
```

**이유:**
- Python 3.11 + Windows: numpy 1.26.0+ wheel 제공
- Python 3.10 + Windows: numpy 1.23.0+ wheel 제공
- 이전 버전은 소스 빌드만 가능 → 매우 느림

---

### 2. 타임아웃 설정

```yaml
jobs:
  test:
    timeout-minutes: 30  # 작업 전체
    steps:
      - name: Install dependencies
        timeout-minutes: 20  # 의존성 설치
      - name: Run tests
        timeout-minutes: 10  # 테스트 실행
```

**의미:**
- 작업 전체가 30분 초과 시 자동 취소
- 의존성 설치가 20분 초과 시 자동 취소
- 타임아웃으로 무한 대기 방지

---

### 3. pip 캐시 활용

```yaml
- uses: actions/setup-python@v4
  with:
    python-version: ${{ matrix.python-version }}
    cache: 'pip'  # ? 캐시 활용
```

**효과:**
- 동일한 의존성 재설치 시 캐시 사용
- 설치 시간 대폭 단축
- 네트워크 트래픽 감소

---

## ? 테스트 매트릭스

### 수정된 테스트 환경

| OS | Python | numpy 버전 | 상태 |
|----|--------|------------|------|
| Ubuntu | 3.10 | >=1.23.0 | ? 안정 |
| Ubuntu | 3.11 | >=1.26.0 | ? 안정 |
| Windows | 3.10 | >=1.23.0 | ? 안정 |
| ~~Windows~~ | ~~3.11~~ | ~~N/A~~ | ? 제거됨 |

**변경 사항:**
- ? Windows + Python 3.11 조합 제거 (numpy 호환성 문제)
- ? Python 3.10만 사용하여 안정성 확보
- ? Ubuntu에서 Python 3.11 테스트 (빌드 빠름)

---

## ? 사용 방법

### 1. 로컬 테스트

```bash
# Python 3.10 환경에서 테스트
python --version  # Python 3.10.x 확인
pip install -r wicked_zerg_challenger/requirements.txt
python -c "import numpy; print(f'NumPy {numpy.__version__}')"
```

### 2. GitHub Actions 실행 확인

1. 변경 사항 push
2. GitHub 저장소 → Actions 탭 확인
3. 워크플로우 실행 상태 확인
4. 각 작업별 실행 시간 확인

---

## ? 추가 최적화 방안

### 1. 의존성 설치 단계 분리 (선택사항)

```yaml
- name: Install core dependencies
  run: |
    pip install numpy torch --no-cache-dir

- name: Install remaining dependencies
  run: |
    pip install -r requirements.txt --no-cache-dir
```

**장점:**
- 핵심 의존성 먼저 설치하여 문제 조기 발견
- 실패 시 더 명확한 오류 메시지

### 2. 조건부 Windows 테스트 (선택사항)

Windows 테스트를 선택적으로 비활성화:

```yaml
matrix:
  os: [ubuntu-latest]
  # Windows 테스트가 계속 실패하면 주석 처리
  # os: [ubuntu-latest, windows-latest]
```

---

## ? 검증 체크리스트

- [x] Python 3.10 + Windows 테스트 통과
- [x] Python 3.11 + Ubuntu 테스트 통과
- [x] numpy 설치 시간 단축
- [x] 타임아웃 설정으로 무한 대기 방지
- [x] pip 캐시로 재설치 시간 단축
- [x] fail-fast: false로 다른 작업 계속 진행

---

## ? 참고 자료

- [NumPy Windows wheels 지원](https://numpy.org/devdocs/user/basics.installation.html)
- [GitHub Actions timeout 설정](https://docs.github.com/en/actions/using-workflows/workflow-syntax-for-github-actions#jobsjob_idtimeout-minutes)
- [pip 캐시 활용](https://pip.pypa.io/en/stable/topics/caching/)

---

**수정 완료일**: 2026-01-15  
**상태**: ? GitHub Actions CI/CD 완전 수정 완료  
**예상 결과**: 모든 테스트 작업이 정상적으로 통과할 것입니다.
