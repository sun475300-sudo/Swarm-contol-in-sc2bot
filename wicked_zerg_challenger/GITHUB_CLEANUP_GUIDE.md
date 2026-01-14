# GitHub 리포지토리 정리 가이드

**작성 일시**: 2026-01-14  
**목적**: GitHub 리포지토리에서 불필요한 파일 제거 및 정리

---

## ? 현재 상태 확인

프로젝트를 확인한 결과:
- ? `.gitignore` 파일이 이미 잘 구성되어 있습니다
- ?? 일부 파일/폴더가 Git에 추적되고 있을 수 있습니다

---

## ? GitHub 정리 대상 (삭제 권장)

다음 파일/폴더들은 소스 코드가 아니거나, 보안상 위험하거나, 컴퓨터마다 달라지는 파일들입니다:

1. **? 보안 위험 파일**
   - `mobile_app/android.keystore`: 앱 서명키 (공개되면 안 됨)
   - `.env`: 서버 비밀번호 등 (`.env.example`은 제외)

2. **? 용량 낭비 & 잡동사니**
   - `local_training/venv/`: 가상환경 폴더 (파일 수천 개)
   - `__pycache__/`: Python 임시 파일
   - `backups/`: 백업 파일들
   - `*.log`: 로그 파일
   - `*.SC2Replay`: 리플레이 파일 (용량 큼)
   - `mobile_app/build/`: 빌드 결과물

---

## ? 실행 가이드: 한 번에 청소하고 올리기

아래 명령어를 **PowerShell 또는 CMD**에 순서대로 복사해서 입력하세요.

### ?? 주의사항
- **명령어를 실행하기 전에 현재 작업 내용을 커밋하세요**
- `git rm --cached`는 Git 추적에서만 제거하고 로컬 파일은 유지합니다

---

### 1단계: Git 추적에서 제거 (로컬 파일은 유지됨)

```cmd
REM 프로젝트 루트로 이동
cd /d D:\Swarm-contol-in-sc2bot\wicked_zerg_challenger

REM 가상환경 폴더 제거
git rm -r --cached local_training/venv 2>nul

REM 백업 폴더들 제거
git rm -r --cached backups 2>nul
git rm -r --cached monitoring/backups 2>nul
git rm -r --cached local_training/backups 2>nul

REM Python 캐시 파일 제거
git rm -r --cached __pycache__ 2>nul
git ls-files | findstr /i "__pycache__" | for /f "delims=" %%f in ('more') do git rm -r --cached "%%f" 2>nul

REM 보안 파일 제거 (존재하는 경우만)
git rm --cached mobile_app/android.keystore 2>nul
git rm --cached .env 2>nul

REM 로그 파일 제거
git ls-files | findstr /i "\.log$" | for /f "delims=" %%f in ('more') do git rm --cached "%%f" 2>nul

REM 리플레이 파일 제거
git ls-files | findstr /i "\.SC2Replay$" | for /f "delims=" %%f in ('more') do git rm --cached "%%f" 2>nul

REM 빌드 결과물 제거
git rm -r --cached mobile_app/build 2>nul
git rm -r --cached mobile_app/app/build 2>nul
```

---

### 2단계: .gitignore 확인 (이미 잘 구성되어 있음)

현재 `.gitignore` 파일이 이미 잘 구성되어 있습니다. 하지만 다음 항목들이 포함되어 있는지 확인하세요:

- ? `venv/`, `.venv/`, `env/`
- ? `__pycache__/`, `*.pyc`
- ? `backups/`
- ? `*.log`
- ? `*.SC2Replay`
- ? `*.keystore`
- ? `.env`
- ? `mobile_app/build/`

**.gitignore 파일 확인:**
```cmd
type .gitignore | findstr /i "venv __pycache__ backups .log .keystore .env"
```

---

### 3단계: 변경사항 저장하고 GitHub에 반영

```cmd
REM 변경사항 확인
git status

REM .gitignore 추가 (변경된 경우)
git add .gitignore

REM 변경사항 커밋
git commit -m "Clean: Remove unnecessary files from Git tracking (venv, backups, cache, logs)"

REM GitHub에 푸시
git push origin main
```

---

## ? 참고사항

### 이미 .gitignore에 포함된 항목들
현재 `.gitignore` 파일에 다음 항목들이 이미 포함되어 있습니다:
- `venv/`, `.venv/`, `env/`
- `__pycache__/`, `*.pyc`, `*.pyo`
- `backups/`
- `*.log`
- `*.SC2Replay`
- `*.keystore`
- `.env`
- `mobile_app/build/`
- `stats/`
- `telemetry_*.json`
- 기타 많은 항목들

### 왜 `git rm --cached`를 사용하나요?
- `git rm --cached`: Git 추적에서만 제거하고 로컬 파일은 유지
- `git rm`: Git 추적과 로컬 파일 모두 삭제 (위험!)
- 가상환경 폴더 등은 로컬에서 필요하지만 GitHub에는 올리면 안 되므로 `--cached` 옵션 사용

### 문제 발생 시
만약 Git 저장소에 문제가 있다면:
```cmd
REM Git 상태 확인
git status

REM 문제가 있다면 Git 저장소 재초기화 (주의: 사용 전 백업!)
REM git fsck
```

---

**작성일**: 2026-01-14  
**상태**: ? 준비 완료
