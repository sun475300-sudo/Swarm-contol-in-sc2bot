# Git Pre-commit Hook 오류 해결 가이드

**오류 메시지**: `error: cannot spawn .git/hooks/pre-commit: No such file or directory`

---

## ? 문제 원인

### 1. 파일 위치 문제
- **Git은 루트 저장소의 `.git/hooks/pre-commit`을 찾습니다**
- 잘못된 위치: `wicked_zerg_challenger/.git/hooks/pre-commit` ?
- 올바른 위치: `.git/hooks/pre-commit` (프로젝트 루트) ?

### 2. Windows에서 Shell 스크립트 실행 문제
- Windows에서 `#!/bin/sh`는 Git Bash가 필요합니다
- 일반 cmd나 PowerShell에서는 `sh.exe`를 찾을 수 없습니다
- `core.autocrlf` 설정으로 인한 줄 끝(CRLF vs LF) 문제 가능

### 3. 실행 권한 문제
- Windows에서는 파일 실행 권한이 다르게 작동합니다
- Git이 파일을 실행 가능한 것으로 인식하지 못할 수 있습니다

---

## ? 해결 방법

### 방법 1: 올바른 위치에 파일 생성 (완료)

이미 루트 `.git/hooks/pre-commit` 파일을 생성했습니다.

**확인 방법**:
```powershell
Test-Path .git\hooks\pre-commit
```

**결과**: `True` (파일 존재)

---

### 방법 2: Git Bash 사용 확인

**확인**:
```powershell
where.exe sh.exe
```

**Git Bash 위치**:
- 일반적으로: `C:\Program Files\Git\bin\sh.exe`
- 또는: `C:\Program Files (x86)\Git\bin\sh.exe`

**PATH에 Git Bash 추가**:
```powershell
$env:Path += ";C:\Program Files\Git\bin"
```

---

### 방법 3: 줄 끝(Line Endings) 수정

Windows에서 파일을 편집할 때 CRLF(`\r\n`)가 추가될 수 있습니다.
Git은 LF(`\n`)만 필요합니다.

**확인**:
```powershell
# 파일의 줄 끝 확인
Get-Content .git\hooks\pre-commit -Raw | Format-Hex | Select-Object -First 20
```

**수정** (필요한 경우):
```powershell
# LF로 변환
$content = Get-Content .git\hooks\pre-commit -Raw
$content = $content -replace "`r`n", "`n"
Set-Content .git\hooks\pre-commit -Value $content -NoNewline
```

---

### 방법 4: PowerShell 기반 Hook 사용 (권장)

Windows에서는 PowerShell 스크립트를 직접 사용하는 것이 더 안정적입니다.

**생성할 파일**: `.git/hooks/pre-commit.ps1`

```powershell
# .git/hooks/pre-commit.ps1
cd (git rev-parse --show-toplevel)

if (Test-Path "wicked_zerg_challenger/tools/pre_commit_security_check.ps1") {
    & pwsh -File "wicked_zerg_challenger/tools/pre_commit_security_check.ps1"
    if ($LASTEXITCODE -ne 0) {
        exit 1
    }
}

exit 0
```

**그리고 `.git/config`에 추가**:
```ini
[core]
    hooksPath = .git/hooks
```

---

## ? 테스트 방법

### 1. Hook 파일 존재 확인
```powershell
Test-Path .git\hooks\pre-commit
```

### 2. Hook 파일 내용 확인
```powershell
Get-Content .git\hooks\pre-commit -Head 10
```

### 3. Git Bash에서 직접 실행 테스트
```bash
# Git Bash에서 실행
.git/hooks/pre-commit
```

### 4. 실제 커밋 테스트
```powershell
# 테스트 커밋
git commit --allow-empty -m "Test commit"
```

---

## ? 현재 상태

? **해결 완료**:
- 루트 `.git/hooks/pre-commit` 파일 생성 완료
- Windows/Linux 모두 지원하는 스크립트로 작성
- `pwsh` 또는 `powershell.exe` 모두 지원

**다음 단계**:
1. `git commit --allow-empty -m "Test"` 로 테스트
2. 오류가 계속되면 Git Bash 설치 확인
3. 필요시 PowerShell 버전 사용

---

## ? 추가 문제 해결

### Git Bash가 없는 경우

**옵션 1**: Git Bash 설치
- https://git-scm.com/downloads

**옵션 2**: PowerShell Hook 사용
- 위의 "방법 4" 참조

**옵션 3**: Hook 비활성화 (임시)
```powershell
Rename-Item .git\hooks\pre-commit .git\hooks\pre-commit.disabled
```

---

**작성일**: 2026년 1월 15일  
**상태**: ? 루트 `.git/hooks/pre-commit` 파일 생성 완료
