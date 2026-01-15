# Git Pre-commit Hook 오류 해결 완료

**오류**: `error: cannot spawn .git/hooks/pre-commit: No such file or directory`

---

## ? 원인 분석

### 문제 1: 파일 위치
- Git은 **루트 저장소의 `.git/hooks/pre-commit`**을 찾습니다
- ? 잘못된 위치: `wicked_zerg_challenger/.git/hooks/pre-commit`
- ? 올바른 위치: `.git/hooks/pre-commit` (프로젝트 루트)

### 문제 2: Windows에서 Shell 스크립트 실행
- Windows에서 `#!/bin/sh`는 **Git Bash**가 필요합니다
- Git Bash가 PATH에 없거나 제대로 설정되지 않으면 실행 불가
- `sh.exe`를 찾을 수 없으면 오류 발생

### 문제 3: 줄 끝(Line Endings)
- Windows에서 CRLF(`\r\n`) 사용
- Git hooks는 LF(`\n`)만 필요
- 줄 끝 문제로 실행 실패 가능

---

## ? 해결 방법

### 현재 상태
? **루트 `.git/hooks/pre-commit` 파일 생성 완료**

**파일 위치**: `D:\Swarm-contol-in-sc2bot\.git\hooks\pre-commit`

**내용**: Windows/Linux/Mac 모두 지원하는 스크립트

---

## ? 테스트 및 확인

### 1. 파일 존재 확인
```powershell
Test-Path .git\hooks\pre-commit
# 결과: True
```

### 2. Git Bash 설치 확인
```powershell
Test-Path "C:\Program Files\Git\bin\sh.exe"
# 결과: True 또는 False
```

### 3. 직접 실행 테스트 (Git Bash에서)
```bash
# Git Bash 열기
# 프로젝트 루트로 이동
cd /d/Swarm-contol-in-sc2bot

# Hook 직접 실행
.git/hooks/pre-commit
```

---

## ? 추가 해결 방법

### 방법 1: Git Bash PATH에 추가

**PowerShell에서**:
```powershell
$env:Path += ";C:\Program Files\Git\bin"
```

**영구적으로 추가**:
```powershell
[Environment]::SetEnvironmentVariable(
    "Path",
    $env:Path + ";C:\Program Files\Git\bin",
    "User"
)
```

### 방법 2: PowerShell 기반 Hook 사용

`.git/hooks/pre-commit.ps1` 생성:
```powershell
cd (git rev-parse --show-toplevel)

if (Test-Path "wicked_zerg_challenger/tools/pre_commit_security_check.ps1") {
    & pwsh -File "wicked_zerg_challenger/tools/pre_commit_security_check.ps1"
    if ($LASTEXITCODE -ne 0) {
        exit 1
    }
}

exit 0
```

그리고 `.git/config`에 추가:
```ini
[core]
    hooksPath = .git/hooks
```

### 방법 3: Hook 임시 비활성화

```powershell
Rename-Item .git\hooks\pre-commit .git\hooks\pre-commit.disabled
```

---

## ? 현재 설정 상태

### ? 완료된 작업
1. ? 루트 `.git/hooks/pre-commit` 파일 생성
2. ? Windows/Linux/Mac 모두 지원하는 스크립트 작성
3. ? PowerShell 및 Bash 스크립트 경로 모두 지원

### ?? 추가 확인 필요
1. Git Bash 설치 확인
2. Git Bash PATH 설정 확인
3. 실제 커밋 테스트

---

## ? 다음 단계

### 1. Git Bash 설치 확인
- https://git-scm.com/downloads
- 설치 시 "Git Bash Here" 옵션 선택

### 2. 테스트 커밋
```powershell
git commit --allow-empty -m "Test hook"
```

### 3. 오류가 계속되면
- PowerShell 버전 hook 사용 (위의 방법 2)
- 또는 Hook 비활성화 (위의 방법 3)

---

## ? 참고사항

### Git Hook 실행 순서
1. Git이 `.git/hooks/pre-commit` 파일 찾기
2. 파일 실행 권한 확인
3. Shebang (`#!/bin/sh`) 읽기
4. 해당 인터프리터로 스크립트 실행

### Windows에서 문제가 발생하는 경우
- Git Bash가 PATH에 없음
- 파일 인코딩 문제 (UTF-8 BOM)
- 줄 끝 문제 (CRLF vs LF)
- 실행 권한 문제

**해결**: PowerShell 기반 hook 사용 권장

---

**작성일**: 2026년 1월 15일  
**상태**: ? 루트 `.git/hooks/pre-commit` 파일 생성 완료  
**다음**: Git Bash 설치 확인 및 테스트
