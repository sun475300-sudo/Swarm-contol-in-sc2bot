# Git Pre-commit Hook 테스트 및 설정 가이드

**목적**: Git Bash로 직접 실행 테스트 → PowerShell 버전 사용 → 필요시 비활성화

---

## 1?? Git Bash로 직접 실행 테스트

### 방법 A: Git Bash GUI에서 실행

1. **Git Bash 열기**:
   - 프로젝트 폴더 (`D:\Swarm-contol-in-sc2bot`)에서 우클릭
   - "Git Bash Here" 선택

2. **Hook 직접 실행**:
   ```bash
   .git/hooks/pre-commit
   ```

3. **결과 확인**:
   - ? **성공**: 보안 검사 실행 후 종료
   - ? **실패**: 오류 메시지 표시

---

### 방법 B: PowerShell에서 Git Bash 실행

```powershell
# Git Bash 경로로 직접 실행
& "C:\Program Files\Git\bin\bash.exe" -c "cd /d/Swarm-contol-in-sc2bot && .git/hooks/pre-commit"
```

또는:

```powershell
# Git Bash 경로를 PATH에 추가 후 실행
$env:Path += ";C:\Program Files\Git\bin"
bash.exe -c "cd /d/Swarm-contol-in-sc2bot && .git/hooks/pre-commit"
```

---

### 방법 C: Git Bash에서 수동 테스트

1. Git Bash 실행
2. 프로젝트 루트로 이동:
   ```bash
   cd /d/Swarm-contol-in-sc2bot
   ```
3. Hook 실행:
   ```bash
   .git/hooks/pre-commit
   ```
4. 결과 확인

---

## 2?? PowerShell 버전 Hook 사용 (오류가 계속될 경우)

### 방법 1: PowerShell 스크립트를 직접 실행 가능하게 설정

**문제**: Git은 `.ps1` 확장자 파일을 자동으로 PowerShell로 실행하지 않습니다.

**해결책**: Shell 스크립트에서 PowerShell을 호출하도록 설정 (이미 완료됨)

현재 `.git/hooks/pre-commit` 파일이 Windows에서 PowerShell을 자동으로 호출하도록 설정되어 있습니다.

---

### 방법 2: PowerShell 실행 정책 확인 및 수정

```powershell
# 현재 실행 정책 확인
Get-ExecutionPolicy

# 실행 정책이 Restricted인 경우
# 관리자 권한으로 PowerShell 실행 후:
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

---

### 방법 3: PowerShell 스크립트 직접 테스트

```powershell
# PowerShell 버전 직접 실행 테스트
.git\hooks\pre-commit.ps1

# 또는 PowerShell Core로 실행
pwsh -File .git\hooks\pre-commit.ps1
```

---

## 3?? Hook 비활성화 방법 (필요시)

### 방법 1: 파일 이름 변경 (임시 비활성화)

```powershell
# Hook 비활성화
Rename-Item .git\hooks\pre-commit .git\hooks\pre-commit.disabled

# 다시 활성화
Rename-Item .git\hooks\pre-commit.disabled .git\hooks\pre-commit
```

**장점**:
- ? 원본 파일 보존
- ? 쉽게 다시 활성화 가능

---

### 방법 2: 커밋 시 Hook 건너뛰기

```powershell
# 이번 커밋만 Hook 건너뛰기
git commit --no-verify -m "Your commit message"

# 또는 짧은 별칭 사용
git commit -n -m "Your commit message"
```

**Git 별칭 설정** (선택사항):
```powershell
# Hook 건너뛰는 별칭 추가
git config --global alias.commit-nv "commit --no-verify"

# 사용
git commit-nv -m "Your message"
```

---

### 방법 3: Hook을 빈 파일로 만들기

```powershell
# Hook을 항상 성공하는 빈 스크립트로 변경
@"
#!/bin/sh
exit 0
"@ | Out-File -FilePath .git\hooks\pre-commit -Encoding ASCII -NoNewline
```

---

### 방법 4: Hook 완전히 삭제

```powershell
# Hook 파일 삭제
Remove-Item .git\hooks\pre-commit

# 다시 활성화하려면
# .git\hooks\pre-commit.sh.backup 파일 복원
Copy-Item .git\hooks\pre-commit.sh.backup .git\hooks\pre-commit
```

---

## ? 전체 테스트 시나리오

### Step 1: Git Bash 직접 실행 테스트

```powershell
# PowerShell에서 Git Bash로 실행
& "C:\Program Files\Git\bin\bash.exe" -c "cd /d/Swarm-contol-in-sc2bot && .git/hooks/pre-commit"
```

**예상 결과**:
- ? 성공: 보안 검사 스크립트 실행 후 종료
- ? 실패: "cannot spawn" 또는 다른 오류

---

### Step 2: Git 커밋으로 Hook 테스트

```powershell
# 빈 커밋으로 테스트
git commit --allow-empty -m "Test pre-commit hook"
```

**예상 결과**:
- ? 성공: "? 민감한 정보가 발견되지 않았습니다." 메시지 후 커밋 완료
- ? 실패: "error: cannot spawn .git/hooks/pre-commit" 오류

---

### Step 3: 오류 발생 시 PowerShell 버전 사용

**현재 상태**: `.git/hooks/pre-commit` 파일이 이미 PowerShell을 호출하도록 설정되어 있습니다.

**추가 확인**:
```powershell
# PowerShell 실행 정책 확인
Get-ExecutionPolicy

# RemoteSigned 또는 Unrestricted여야 함
# Restricted인 경우 수정 필요
```

---

### Step 4: 계속 오류 발생 시 Hook 비활성화

```powershell
# 방법 1: 이름 변경
Rename-Item .git\hooks\pre-commit .git\hooks\pre-commit.disabled

# 방법 2: 커밋 시 건너뛰기
git commit --no-verify -m "Your message"
```

---

## ? 현재 상태 확인

### Hook 파일 확인

```powershell
# 현재 활성화된 Hook 파일 확인
Get-Content .git\hooks\pre-commit -Head 10

# 모든 Hook 파일 확인
Get-ChildItem .git\hooks\pre-commit*
```

### Git Bash 설치 확인

```powershell
# Git Bash 존재 확인
Test-Path "C:\Program Files\Git\bin\bash.exe"

# 결과: True 또는 False
```

### PowerShell 실행 정책 확인

```powershell
# 실행 정책 확인
Get-ExecutionPolicy

# 허용되는 값:
# - RemoteSigned (권장)
# - Unrestricted
# - Restricted (문제 발생 가능)
```

---

## ? 빠른 해결 방법

### Windows에서 가장 안정적인 방법

```powershell
# 1. Git Bash로 직접 실행 테스트
& "C:\Program Files\Git\bin\bash.exe" -c "cd /d/Swarm-contol-in-sc2bot && .git/hooks/pre-commit"

# 2. 오류가 발생하면 PowerShell 실행 정책 확인
Get-ExecutionPolicy

# 3. 여전히 오류가 발생하면 Hook 임시 비활성화
Rename-Item .git\hooks\pre-commit .git\hooks\pre-commit.disabled

# 4. 커밋 후 필요시 다시 활성화
Rename-Item .git\hooks\pre-commit.disabled .git\hooks\pre-commit
```

---

## ? 문제 해결 체크리스트

- [ ] Git Bash 설치 확인: `Test-Path "C:\Program Files\Git\bin\bash.exe"`
- [ ] Git Bash로 직접 실행 테스트
- [ ] PowerShell 실행 정책 확인: `Get-ExecutionPolicy`
- [ ] Git 커밋으로 Hook 테스트: `git commit --allow-empty -m "Test"`
- [ ] 오류 발생 시 Hook 비활성화 또는 `--no-verify` 사용

---

**작성일**: 2026년 1월 15일  
**다음 단계**: 위의 Step 1부터 순서대로 테스트하세요.
