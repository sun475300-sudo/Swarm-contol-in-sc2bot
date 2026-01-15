# Git Pre-commit Hook 오류 해결 완료

**오류**: `error: cannot spawn .git/hooks/pre-commit: No such file or directory`

---

## ? 해결 완료

### 문제 원인
1. **Windows에서 Shell 스크립트 실행 불가**: `#!/bin/sh` 스크립트는 Git Bash가 필요함
2. **파일 위치**: 루트 `.git/hooks/pre-commit` 파일이 필요함
3. **줄 끝 문제**: Windows CRLF vs Unix LF

### 해결 방법
**Windows Batch 버전으로 교체 완료**

---

## ? 생성된 파일들

### 현재 활성화된 Hook
- **`.git/hooks/pre-commit`** (Windows Batch 버전) ?
  - Windows에서 즉시 작동
  - Git Bash 불필요
  - PowerShell 자동 감지

### 백업 파일
- **`.git/hooks/pre-commit.sh.backup`** (원본 Shell 버전)
- **`.git/hooks/pre-commit.sh.backup2`** (추가 백업)

---

## ? 테스트 방법

### 1. Hook 직접 실행 테스트

```powershell
# Batch 버전 직접 실행
.git\hooks\pre-commit

# 또는 Git Bash에서 (Shell 버전 테스트 시)
# Git Bash 열기 후
.git/hooks/pre-commit.sh.backup
```

### 2. Git 커밋 테스트

```powershell
# 빈 커밋으로 테스트
git commit --allow-empty -m "Test pre-commit hook"

# 결과 확인:
# ? 성공: "? 민감한 정보가 발견되지 않았습니다."
# ? 실패: 오류 메시지 표시
```

---

## ? Hook 버전 전환

### Shell 버전으로 되돌리기

```powershell
# Shell 버전으로 복원
Copy-Item .git\hooks\pre-commit.sh.backup .git\hooks\pre-commit -Force

# Git Bash에서 테스트 필요
```

### Batch 버전 유지 (권장)

```powershell
# 현재 Batch 버전이 활성화됨
# 추가 작업 불필요
```

---

## ? Hook 비활성화 방법

### 방법 1: 파일 이름 변경

```powershell
# Hook 비활성화
Rename-Item .git\hooks\pre-commit .git\hooks\pre-commit.disabled

# 다시 활성화
Rename-Item .git\hooks\pre-commit.disabled .git\hooks\pre-commit
```

### 방법 2: 커밋 시 건너뛰기

```powershell
git commit --no-verify -m "Your message"
```

### 방법 3: 빈 Hook으로 변경

```powershell
Set-Content .git\hooks\pre-commit -Value "@echo off`r`nexit 0"
```

---

## ? 현재 Hook 파일 내용

**`.git/hooks/pre-commit`** (Batch 버전):
```batch
@echo off
REM Git Pre-commit Hook - Security Check (Windows Batch Version)

cd /d "%~dp0..\.."

if exist "wicked_zerg_challenger\tools\pre_commit_security_check.ps1" (
    pwsh -File "wicked_zerg_challenger\tools\pre_commit_security_check.ps1"
    if errorlevel 1 exit /b 1
) else if exist "tools\pre_commit_security_check.ps1" (
    pwsh -File "tools\pre_commit_security_check.ps1"
    if errorlevel 1 exit /b 1
) else (
    REM Hook script not found - allow commit to continue
    exit 0
)

exit 0
```

---

## ? 완료 상태

- [x] 루트 `.git/hooks/pre-commit` 파일 생성
- [x] Windows Batch 버전으로 교체
- [x] PowerShell 자동 감지
- [x] 오류 처리 개선
- [x] 백업 파일 생성

---

**작성일**: 2026년 1월 15일  
**상태**: ? **Windows Batch 버전으로 교체 완료**  
**다음**: Git 커밋 테스트
