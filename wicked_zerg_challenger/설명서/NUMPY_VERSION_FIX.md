# NumPy 버전 불일치 해결 가이드

**작성 일시**: 2026년 01-13  
**문제**: Python 3.10 환경에서 Python 3.12용 NumPy가 설치됨  
**상태**: ?? **수동 해결 필요**

---

## ? 문제 분석

### 발생한 에러

```
ImportError:
IMPORTANT: PLEASE READ THIS FOR ADVICE ON HOW TO SOLVE THIS ISSUE!

Importing the numpy C-extensions failed. This error can happen for
many reasons, often due to issues with your setup or how NumPy was
installed.
The following compiled module files exist, but seem incompatible
with with either python 'cpython-310' or the platform 'win32':

  * _multiarray_umath.cp312-win_amd64.lib
  * _multiarray_umath.cp312-win_amd64.pyd

Please note and check the following:

  * The Python version is: Python 3.10 from "C:\Users\sun47\AppData\Local\Programs\Python\Python310\python.exe"
  * The NumPy version is: "2.4.1"
```

---

## ? 원인 분석

### 주요 원인

1. **Python 버전 불일치**
   - 현재 Python 버전: **3.10**
   - NumPy가 컴파일된 버전: **3.12** (`cp312-win_amd64`)
   - NumPy의 C 확장 모듈이 Python 3.12용으로 컴파일되어 Python 3.10에서 실행 불가

2. **가상 환경 손상**
   - 가상 환경(`.venv`)에 잘못된 버전의 NumPy가 설치됨
   - 다른 Python 버전에서 설치된 패키지가 혼재

3. **패키지 캐시 문제**
   - pip 캐시에 잘못된 버전의 NumPy가 저장됨

---

## ? 해결 방법

### 방법 1: NumPy 재설치 (권장)

**단계별 해결**:

1. **가상 환경 활성화**:
   ```powershell
   cd D:\wicked_zerg_challenger
   .venv\Scripts\Activate.ps1
   ```

2. **NumPy 완전 제거**:
   ```powershell
   pip uninstall numpy -y
   ```

3. **pip 캐시 정리**:
   ```powershell
   pip cache purge
   ```

4. **NumPy 재설치 (Python 3.10 호환 버전)**:
   ```powershell
   pip install numpy==1.24.3 --no-cache-dir
   ```
   또는 최신 Python 3.10 호환 버전:
   ```powershell
   pip install "numpy>=1.20.0,<2.0.0" --no-cache-dir
   ```

5. **설치 확인**:
   ```powershell
   python -c "import numpy; print(numpy.__version__)"
   ```

### 방법 2: 가상 환경 재생성 (완전 해결)

**단계별 해결**:

1. **기존 가상 환경 삭제**:
   ```powershell
   cd D:\wicked_zerg_challenger
   Remove-Item -Recurse -Force .venv
   ```

2. **새 가상 환경 생성**:
   ```powershell
   python -m venv .venv
   ```

3. **가상 환경 활성화**:
   ```powershell
   .venv\Scripts\Activate.ps1
   ```

4. **pip 업그레이드**:
   ```powershell
   python -m pip install --upgrade pip
   ```

5. **의존성 재설치**:
   ```powershell
   pip install -r requirements.txt --no-cache-dir
   ```

6. **NumPy 버전 확인**:
   ```powershell
   python -c "import numpy; print(f'NumPy {numpy.__version__} - OK')"
   ```

---

## ? 자동화 스크립트

### Windows PowerShell 스크립트

**파일**: `bat\fix_numpy.bat`

```batch
@echo off
REM NumPy 버전 불일치 해결 스크립트

echo.
echo ================================
echo NUMPY VERSION FIX
echo ================================
echo.

cd /d D:\wicked_zerg_challenger

echo [STEP 1] Activating virtual environment...
call .venv\Scripts\activate.bat

echo [STEP 2] Uninstalling NumPy...
pip uninstall numpy -y

echo [STEP 3] Clearing pip cache...
pip cache purge

echo [STEP 4] Reinstalling NumPy (Python 3.10 compatible)...
pip install "numpy>=1.20.0,<2.0.0" --no-cache-dir

echo [STEP 5] Verifying installation...
python -c "import numpy; print(f'NumPy {numpy.__version__} - OK')"

if errorlevel 1 (
    echo [ERROR] NumPy installation failed!
    pause
    exit /b 1
)

echo.
echo ================================
echo NUMPY FIX COMPLETE
echo ================================
echo.

pause
```

---

## ? 권장 해결 순서

### 즉시 해결 (빠른 방법)

1. **NumPy 재설치**:
   ```powershell
   cd D:\wicked_zerg_challenger
   .venv\Scripts\Activate.ps1
   pip uninstall numpy -y
   pip cache purge
   pip install "numpy>=1.20.0,<2.0.0" --no-cache-dir
   ```

2. **테스트**:
   ```powershell
   python -c "import numpy; print('OK')"
   ```

3. **게임 학습 재시도**:
   ```powershell
   bat\start_game_training.bat
   ```

### 완전 해결 (권장 방법)

1. **가상 환경 재생성** (위의 "방법 2" 참조)
2. **모든 의존성 재설치**
3. **전체 테스트 실행**

---

## ?? 주의 사항

### NumPy 버전 제약

- **Python 3.10**: NumPy 1.20.0 ~ 1.26.x 권장
- **NumPy 2.0+**: Python 3.9+ 필요하지만, 일부 환경에서 호환성 문제 발생 가능
- **권장 버전**: `numpy>=1.20.0,<2.0.0` (Python 3.10과 가장 안정적)

### 가상 환경 관리

- 가상 환경은 Python 버전별로 분리되어야 합니다
- 다른 Python 버전에서 설치한 패키지를 공유하지 마세요
- 프로젝트별로 독립적인 가상 환경을 유지하세요

---

## ? 문제 해결 체크리스트

- [ ] 가상 환경이 Python 3.10용으로 생성되었는지 확인
- [ ] NumPy가 완전히 제거되었는지 확인 (`pip list | findstr numpy`)
- [ ] pip 캐시가 정리되었는지 확인
- [ ] NumPy가 올바른 버전으로 재설치되었는지 확인
- [ ] `python -c "import numpy"` 테스트 통과
- [ ] 게임 학습이 정상적으로 시작되는지 확인

---

**작성일**: 2026년 01-13  
**작성자**: AI Assistant  
**상태**: ?? **수동 해결 필요** (스크립트 제공됨)
