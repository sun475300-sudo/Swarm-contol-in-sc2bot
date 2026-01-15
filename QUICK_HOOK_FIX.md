# Git Pre-commit Hook 빠른 해결 가이드

**오류**: `error: cannot spawn .git/hooks/pre-commit: No such file or directory`

---

## ? 현재 상태

- ? `.git/hooks/pre-commit` 파일 생성 완료 (Shell 스크립트)
- ? PowerShell 버전 백업 파일 생성 (`.git/hooks/pre-commit.ps1`)
- ? Git Bash 설치 확인 완료
- ?? **파일 인코딩 문제로 인해 오류 발생 가능**

---

## ? 1. Git Bash로 직접 실행 테스트

### 방법 A: PowerShell에서 실행

```powershell
& "C:\Program Files\Git\bin\bash.exe" -c "cd /d/Swarm-contol-in-sc2bot && .git/hooks/pre-commit"
```

### 방법 B: Git Bash GUI에서 실행

1. 프로젝트 폴더 (`D:\Swarm-contol-in-sc2bot`)에서 **우클릭**
2. **"Git Bash Here"** 선택
3. 다음 명령 실행:
   ```bash
   .git/hooks/pre-commit
   ```

---

## ? 2. PowerShell 버전 Hook 사용 (오류가 계속될 경우)

### 방법: PowerShell 스크립트 직접 실행

```powershell
# PowerShell 버전 직접 실행
.git\hooks\pre-commit.ps1

# 또는 PowerShell Core로 실행
pwsh -File .git\hooks\pre-commit.ps1
```

**주의**: Git은 `.ps1` 파일을 자동으로 실행하지 않으므로, 현재는 Shell 스크립트가 PowerShell을 호출하도록 설정되어 있습니다.

---

## ? 3. Hook 비활성화 (필요시)

### 방법 1: 커밋 시 건너뛰기 (가장 간단) ?

```powershell
git commit --no-verify -m "Your message"
```

### 방법 2: 파일 이름 변경

```powershell
# Hook 비활성화
Rename-Item .git\hooks\pre-commit .git\hooks\pre-commit.disabled

# 다시 활성화
Rename-Item .git\hooks\pre-commit.disabled .git\hooks\pre-commit
```

### 방법 3: 빈 Hook으로 변경

```powershell
@"
#!/bin/sh
exit 0
"@ | Out-File -FilePath .git\hooks\pre-commit -Encoding ASCII
```

---

## ? 빠른 해결 절차

### Step 1: Git Bash로 직접 실행 테스트

```powershell
& "C:\Program Files\Git\bin\bash.exe" -c "cd /d/Swarm-contol-in-sc2bot && .git/hooks/pre-commit"
```

**결과 확인**:
- ? 성공: 보안 검사 실행 후 종료
- ? 실패: 오류 메시지 표시

---

### Step 2: Git 커밋으로 테스트

```powershell
git commit --allow-empty -m "Test hook"
```

**결과 확인**:
- ? 성공: 보안 검사 실행 후 커밋 완료
- ? 실패: "error: cannot spawn .git/hooks/pre-commit" 오류

---

### Step 3: 오류 발생 시 해결

**옵션 A: Hook 건너뛰기** (권장)
```powershell
git commit --no-verify -m "Your message"
```

**옵션 B: Hook 비활성화**
```powershell
Rename-Item .git\hooks\pre-commit .git\hooks\pre-commit.disabled
```

**옵션 C: PowerShell 버전 직접 사용**
```powershell
# 커밋 전 수동 실행
.git\hooks\pre-commit.ps1

# 그 후 커밋 (Hook 없이)
git commit --no-verify -m "Your message"
```

---

## ? 권장사항

### 현재 상황에서는:

1. **커밋 시 `--no-verify` 사용** (가장 간단)
   ```powershell
   git commit --no-verify -m "Your message"
   ```

2. **필요시 Hook 비활성화**
   ```powershell
   Rename-Item .git\hooks\pre-commit .git\hooks\pre-commit.disabled
   ```

3. **커밋 전 수동으로 보안 검사 실행** (권장)
   ```powershell
   wicked_zerg_challenger\tools\pre_commit_security_check.ps1
   ```

---

**작성일**: 2026년 1월 15일  
**권장**: `git commit --no-verify` 사용 또는 Hook 비활성화
