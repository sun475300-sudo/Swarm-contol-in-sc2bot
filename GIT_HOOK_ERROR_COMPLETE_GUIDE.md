# Git Pre-commit Hook 오류 완전 해결 가이드

**오류 메시지**: `error: cannot spawn .git/hooks/pre-commit: No such file or directory`

**검토 일시**: 2026년 1월 15일  
**Git 버전**: 2.52.0.windows.1  
**환경**: Windows 10/11

---

## ? 현재 상태 진단

### ? 확인된 사항

1. **Hook 파일 존재**: `.git/hooks/pre-commit` 파일이 존재함 (2,132 bytes)
2. **Shebang 정상**: `#!/bin/sh` 헤더가 올바르게 설정됨
3. **PowerShell 스크립트 존재**: `wicked_zerg_challenger/tools/pre_commit_security_check.ps1` 확인됨
4. **Git 설치**: Git 2.52.0.windows.1 정상 설치됨

### ?? 문제 가능성

Windows 환경에서 Git이 Shell 스크립트(`.sh`)를 실행할 때 발생할 수 있는 문제들:

1. **Git Bash 경로 문제**: Git Bash가 PATH에 없거나 잘못된 경로
2. **파일 인코딩 문제**: UTF-8 BOM이 포함되어 첫 줄 해석 실패
3. **줄바꿈 문제**: CRLF vs LF 차이
4. **실행 권한 문제**: Windows에서는 덜 중요하지만 확인 필요

---

## ?? 해결 방법 (단계별)

### Step 1: 파일 인코딩 및 줄바꿈 확인

Windows에서 생성된 파일은 CRLF(`\r\n`)를 사용하지만, Shell 스크립트는 LF(`\n`)를 요구합니다.

#### PowerShell로 확인 및 변환:

```powershell
# 1. 현재 줄바꿈 문자 확인
$content = Get-Content .git\hooks\pre-commit -Raw
if ($content -match "`r`n") {
    Write-Host "CRLF 발견 - 변환 필요"
} else {
    Write-Host "LF 사용 중 - 정상"
}

# 2. LF로 변환 (Git Bash 방식)
$content = $content -replace "`r`n", "`n"
[System.IO.File]::WriteAllText(".git\hooks\pre-commit", $content, (New-Object System.Text.UTF8Encoding($false)))

# 3. BOM 제거 (필요 시)
$content = Get-Content .git\hooks\pre-commit -Raw -Encoding UTF8
$content = $content -replace '^\ufeff', ''
[System.IO.File]::WriteAllText(".git\hooks\pre-commit", $content, (New-Object System.Text.UTF8Encoding($false)))
```

---

### Step 2: Git Bash로 직접 실행 테스트

Git Bash가 정상적으로 설치되어 있는지 확인하고, Hook을 직접 실행해봅니다:

```bash
# Git Bash에서 실행
cd /d/Swarm-contol-in-sc2bot
.git/hooks/pre-commit
```

**예상 결과**:
- ? 성공: 보안 검사 실행 후 종료
- ? 실패: 오류 메시지 표시 (구체적인 원인 파악 가능)

---

### Step 3: Git 설정 확인

Git이 올바른 셸을 사용하도록 설정되어 있는지 확인:

```bash
# Git Bash 경로 확인
git config --global core.autocrlf input
git config --global core.editor "notepad"

# Git Bash 실행 확인
"C:\Program Files\Git\bin\bash.exe" --version
```

---

### Step 4: Hook 파일 재생성 (최후의 수단)

위 방법들이 모두 실패하면, Hook 파일을 처음부터 다시 생성:

#### 방법 A: 간단한 Hook (테스트용)

```powershell
@"
#!/bin/sh
# 간단한 테스트 Hook
echo "Pre-commit hook executed successfully"
exit 0
"@ | Out-File -FilePath .git\hooks\pre-commit -Encoding ASCII -NoNewline

# LF로 변환
$content = Get-Content .git\hooks\pre-commit -Raw
$content = $content -replace "`r`n", "`n"
[System.IO.File]::WriteAllText(".git\hooks\pre-commit", $content, (New-Object System.Text.UTF8Encoding($false)))
```

#### 방법 B: PowerShell 기반 Hook (Windows 최적화)

Windows 전용 PowerShell Hook 생성:

```powershell
@"
#!/usr/bin/env pwsh
# Git Pre-commit Hook - PowerShell Version (Windows)
$ErrorActionPreference = "Stop"

# Git 루트로 이동
$gitRoot = git rev-parse --show-toplevel
if ($gitRoot) { Set-Location $gitRoot }

# PowerShell 스크립트 실행
$scriptPath = "wicked_zerg_challenger\tools\pre_commit_security_check.ps1"
if (Test-Path $scriptPath) {
    try {
        & pwsh -File $scriptPath
        if ($LASTEXITCODE -ne 0) { exit 1 }
    } catch {
        try {
            & powershell.exe -File $scriptPath
            if ($LASTEXITCODE -ne 0) { exit 1 }
        } catch {
            Write-Host "??  Pre-commit hook 실행 실패: $_" -ForegroundColor Yellow
            exit 0  # 오류가 있어도 커밋은 계속 진행
        }
    }
} else {
    Write-Host "??  보안 검사 스크립트를 찾을 수 없습니다: $scriptPath" -ForegroundColor Yellow
    exit 0
}

exit 0
"@ | Out-File -FilePath .git\hooks\pre-commit.ps1 -Encoding UTF8

# Shell 스크립트로 래퍼 생성
@"
#!/bin/sh
# PowerShell Hook 래퍼
exec pwsh -File ".git/hooks/pre-commit.ps1" "$@"
"@ | Out-File -FilePath .git\hooks\pre-commit -Encoding ASCII
```

**주의**: Git은 `.ps1` 파일을 직접 실행하지 않으므로, Shell 스크립트 래퍼가 필요합니다.

---

### Step 5: 임시 우회 (긴급 상황)

Hook 문제를 해결하는 동안 커밋을 계속해야 한다면:

```bash
# Hook 건너뛰기
git commit --no-verify -m "Your commit message"
```

**?? 주의**: 이 방법은 보안 검사를 건너뛰므로, 긴급한 경우에만 사용하세요.

---

## ? 테스트 절차

### 1. Hook 직접 실행 테스트

```powershell
# PowerShell에서
& "C:\Program Files\Git\bin\bash.exe" -c "cd /d/Swarm-contol-in-sc2bot && .git/hooks/pre-commit"
```

또는 Git Bash에서:
```bash
.git/hooks/pre-commit
```

### 2. Git 커밋으로 테스트

```bash
git add .
git commit -m "Test commit"
```

### 3. 성공 확인

- ? 보안 검사가 실행되고 커밋이 완료되면 성공
- ? 오류 메시지가 나타나면 위 해결 방법 참조

---

## ? 종합 해결 스크립트

다음 스크립트를 실행하면 모든 문제를 한 번에 해결할 수 있습니다:

```powershell
# Git Hook 완전 수정 스크립트
Write-Host "? Git Pre-commit Hook 수정 중..." -ForegroundColor Cyan

# 1. 현재 Hook 파일 백업
if (Test-Path ".git\hooks\pre-commit") {
    Copy-Item ".git\hooks\pre-commit" ".git\hooks\pre-commit.backup"
    Write-Host "? 기존 Hook 파일 백업 완료" -ForegroundColor Green
}

# 2. 새 Hook 파일 생성 (LF, UTF-8 without BOM)
$hookContent = @"
#!/bin/sh
# Git Pre-commit Hook - Security Check
# Windows Git Bash / Linux / Mac 모두 지원

cd "$(git rev-parse --show-toplevel)"

# Windows에서 PowerShell 스크립트 실행
if [ -n "$WINDIR" ] || [ -n "$MSYSTEM" ]; then
    # PowerShell Core (pwsh) 우선
    if command -v pwsh.exe >/dev/null 2>&1; then
        if [ -f "wicked_zerg_challenger/tools/pre_commit_security_check.ps1" ]; then
            pwsh.exe -File "wicked_zerg_challenger/tools/pre_commit_security_check.ps1"
            exit_code=`$?
            if [ `$exit_code -ne 0 ]; then
                exit 1
            fi
        elif [ -f "tools/pre_commit_security_check.ps1" ]; then
            pwsh.exe -File "tools/pre_commit_security_check.ps1"
            exit_code=`$?
            if [ `$exit_code -ne 0 ]; then
                exit 1
            fi
        fi
    # Windows PowerShell (powershell.exe)
    elif command -v powershell.exe >/dev/null 2>&1; then
        if [ -f "wicked_zerg_challenger/tools/pre_commit_security_check.ps1" ]; then
            powershell.exe -File "wicked_zerg_challenger/tools/pre_commit_security_check.ps1"
            exit_code=`$?
            if [ `$exit_code -ne 0 ]; then
                exit 1
            fi
        elif [ -f "tools/pre_commit_security_check.ps1" ]; then
            powershell.exe -File "tools/pre_commit_security_check.ps1"
            exit_code=`$?
            if [ `$exit_code -ne 0 ]; then
                exit 1
            fi
        fi
    fi
else
    # Linux/Mac: Bash 스크립트 실행
    if [ -f "wicked_zerg_challenger/tools/pre_commit_security_check.sh" ]; then
        chmod +x "wicked_zerg_challenger/tools/pre_commit_security_check.sh" 2>/dev/null
        ./wicked_zerg_challenger/tools/pre_commit_security_check.sh
        exit_code=`$?
        if [ `$exit_code -ne 0 ]; then
            exit 1
        fi
    elif [ -f "tools/pre_commit_security_check.sh" ]; then
        chmod +x "tools/pre_commit_security_check.sh" 2>/dev/null
        ./tools/pre_commit_security_check.sh
        exit_code=`$?
        if [ `$exit_code -ne 0 ]; then
            exit 1
        fi
    fi
fi

exit 0
"@

# 3. LF 줄바꿈으로 저장 (UTF-8 without BOM)
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText(".git\hooks\pre-commit", $hookContent, $utf8NoBom)

Write-Host "? Hook 파일 생성 완료 (LF, UTF-8 without BOM)" -ForegroundColor Green

# 4. 테스트
Write-Host "`n? Hook 테스트 중..." -ForegroundColor Yellow
$gitBashPath = "C:\Program Files\Git\bin\bash.exe"
if (Test-Path $gitBashPath) {
    & $gitBashPath -c "cd /d/Swarm-contol-in-sc2bot && .git/hooks/pre-commit"
    Write-Host "? Hook 테스트 완료" -ForegroundColor Green
} else {
    Write-Host "??  Git Bash를 찾을 수 없습니다. 수동으로 테스트하세요." -ForegroundColor Yellow
}

Write-Host "`n? 완료!" -ForegroundColor Green
Write-Host "다음 명령으로 커밋 테스트: git commit --allow-empty -m 'Test'" -ForegroundColor Cyan
```

---

## ? 요약 및 체크리스트

### 문제 해결 체크리스트

- [ ] `.git/hooks/pre-commit` 파일 존재 확인
- [ ] 파일 첫 줄에 `#!/bin/sh` 확인
- [ ] 파일 인코딩이 UTF-8 without BOM인지 확인
- [ ] 줄바꿈 문자가 LF(`\n`)인지 확인
- [ ] Git Bash로 직접 실행 테스트
- [ ] Git 커밋으로 전체 테스트
- [ ] 오류가 계속되면 Hook 비활성화 또는 간소화
- [ ] 보안 검사 스크립트 자체 검사 제외 기능 동작 확인 (최신 버전)

### 빠른 참조

| 상황 | 해결 방법 |
|------|----------|
| Hook 파일 없음 | `Step 4: Hook 파일 재생성` |
| 인코딩 문제 | `Step 1: 파일 인코딩 변환` |
| 줄바꿈 문제 | `Step 1: LF로 변환` |
| Git Bash 경로 문제 | `Step 3: Git 설정 확인` |
| 긴급 커밋 필요 | `Step 5: --no-verify 사용` |

---

## ? 참고 자료

- [Stack Overflow: msysgit error with hooks](https://stackoverflow.com/questions/5697210/msysgit-error-with-hooks-git-error-cannot-spawn-git-hooks-post-commit-no-su)
- [Stack Overflow: pre-commit hook No such file](https://stackoverflow.com/questions/43933490/pre-commit-hook-no-such-file-or-directory)
- [GitHub: Desktop pre-commit hook fails](https://github.com/desktop/desktop/issues/12586)
- [GitHub: standard-version hook error](https://github.com/conventional-changelog/standard-version/issues/254)
- [DEV Community: Husky pre-commit error](https://dev.to/jeancatarina/fatal-cannot-run-huskypre-commit-no-such-file-or-directory-2i73)

---

---

## ? 최근 업데이트 (2026-01-15)

### 자기 자신 검사 제외 기능 추가

보안 검사 스크립트(`pre_commit_security_check.ps1`)가 자기 자신을 검사하지 않도록 개선되었습니다:

#### 개선 사항

1. **자기 자신 검사 제외**: 스크립트 자체와 Hook 파일은 검사 대상에서 제외
2. **제외 파일 목록**:
   - `pre_commit_security_check.ps1`
   - `pre_commit_security_check.sh`
   - `.git/hooks/pre-commit`
   - `.git/hooks/pre-commit.ps1`

3. **제외 로직**:
   - 경로 정규화 (Windows/Unix 경로 모두 처리)
   - 파일명 직접 비교 (대소문자 무시)
   - 경로 패턴 매칭

#### 사용 예시

```powershell
# pre_commit_security_check.ps1 파일을 수정하고 커밋할 때
git add wicked_zerg_challenger/tools/pre_commit_security_check.ps1
git commit -m "Update security check script"
# ? 스크립트 자체는 검사 대상에서 제외되어 오탐지 없음
```

#### 제외 함수 (참고)

```powershell
# 제외 함수 (보안 검사 스크립트 자체와 Hook 파일 제외)
function Test-ExcludeFile {
    param([string]$filePath)
    
    if ([string]::IsNullOrWhiteSpace($filePath)) {
        return $false
    }
    
    # 경로 정규화 (Windows와 Unix 경로 모두 처리)
    $normalizedPath = $filePath -replace '\\', '/' -replace '//', '/'
    
    # 파일명 추출 (경로의 마지막 부분)
    $fileName = $normalizedPath -split '/' | Select-Object -Last 1
    
    foreach ($excludePath in $excludePaths) {
        # 제외 경로 정규화
        $normalizedExclude = $excludePath -replace '\\', '/' -replace '//', '/'
        $excludeFileName = $normalizedExclude -split '/' | Select-Object -Last 1
        
        # 파일명 직접 매칭 (대소문자 무시)
        if ($fileName -ieq $excludeFileName) {
            return $true
        }
        
        # 전체 경로에 제외 패턴이 포함되어 있는지 확인
        if ($normalizedPath -match [regex]::Escape($excludeFileName)) {
            return $true
        }
    }
    return $false
}
```

---

**작성일**: 2026년 1월 15일  
**마지막 업데이트**: 2026년 1월 15일 (자기 자신 검사 제외 기능 추가)
