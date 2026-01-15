# Git Pre-commit Hook 설정 가이드

**오류 해결**: `error: cannot spawn .git/hooks/pre-commit: No such file or directory`

---

## ? 완료된 작업

### 1. Git Bash로 직접 실행 테스트
- ? 백업 파일 생성: `.git/hooks/pre-commit.sh.backup`
- ? 개선된 pre-commit 스크립트 생성

### 2. PowerShell 버전 Hook 생성
- ? `.git/hooks/pre-commit.ps1` 생성 (PowerShell Core 지원)
- ? `.git/hooks/pre-commit.bat` 생성 (Windows Batch 버전)

### 3. Hook 비활성화 방법 제공
- 아래 "Hook 비활성화" 섹션 참조

---

## ? 1. Git Bash로 직접 실행 테스트

### 방법 A: Git Bash에서 실행

**Git Bash 열기**:
1. 프로젝트 폴더에서 우클릭 → "Git Bash Here"
2. 또는 Git Bash 실행 후:
   ```bash
   cd /d/Swarm-contol-in-sc2bot
   ```

**Hook 직접 실행**:
```bash
.git/hooks/pre-commit
```

**예상 결과**:
- ? 정상: 보안 검사 실행 후 종료
- ? 오류: 오류 메시지 표시

---

### 방법 B: PowerShell에서 Git Bash 경로 사용

```powershell
# PowerShell에서
$env:Path += ";C:\Program Files\Git\bin"
sh.exe -c "cd /d/Swarm-contol-in-sc2bot && .git/hooks/pre-commit"
```

---

## ? 2. PowerShell 버전 Hook 사용

### 방법 1: PowerShell 스크립트 직접 사용

**`.git/config` 파일 수정**:
```ini
[core]
    hooksPath = .git/hooks
    autocrlf = true
```

**Hook 파일 이름 변경**:
```powershell
# PowerShell 버전 활성화
Rename-Item .git\hooks\pre-commit .git\hooks\pre-commit.sh.disabled
Rename-Item .git\hooks\pre-commit.ps1 .git\hooks\pre-commit
```

**주의**: Git은 `.ps1` 확장자 파일을 자동으로 PowerShell로 실행하지 않을 수 있습니다.

---

### 방법 2: Batch 파일 래퍼 사용 (권장)

**`.git/hooks/pre-commit` 파일을 Batch 파일로 교체**:

```powershell
# 현재 sh 버전 백업
Copy-Item .git\hooks\pre-commit .git\hooks\pre-commit.sh.backup -Force

# Batch 버전으로 교체
Copy-Item .git\hooks\pre-commit.bat .git\hooks\pre-commit -Force
```

**장점**:
- ? Windows에서 즉시 작동 (Git Bash 불필요)
- ? PowerShell 자동 감지
- ? 오류 처리 개선

---

### 방법 3: Git Config 설정으로 PowerShell 강제 실행

**`.git/config` 파일에 추가**:
```ini
[core]
    hooksPath = .git/hooks
    
# 또는 PowerShell 스크립트를 직접 실행하도록 설정
```

**PowerShell 스크립트를 실행 가능하게 만들기**:
```powershell
# PowerShell 실행 정책 확인
Get-ExecutionPolicy

# 필요시 변경 (관리자 권한 필요)
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

---

## ? 3. Hook 비활성화 방법

### 방법 1: 파일 이름 변경 (임시)

```powershell
# Hook 비활성화
Rename-Item .git\hooks\pre-commit .git\hooks\pre-commit.disabled

# 나중에 다시 활성화
Rename-Item .git\hooks\pre-commit.disabled .git\hooks\pre-commit
```

---

### 방법 2: Git Config에서 무시

```powershell
# 커밋 시 hook 건너뛰기
git commit --no-verify -m "Your message"

# 또는 별칭 설정
git config --global alias.commit-nv "commit --no-verify"
```

---

### 방법 3: Hook 파일 내용 비우기

```powershell
# Hook을 빈 파일로 만들기
Set-Content .git\hooks\pre-commit -Value "exit 0"
```

---

### 방법 4: 완전히 삭제

```powershell
# Hook 파일 삭제
Remove-Item .git\hooks\pre-commit
```

---

## ? 현재 생성된 파일

### Hook 파일들

1. **`.git/hooks/pre-commit`** (현재 활성화)
   - Shell 스크립트 버전 (Git Bash 필요)
   - Windows/Linux/Mac 모두 지원

2. **`.git/hooks/pre-commit.ps1`** (백업)
   - PowerShell Core 버전
   - Windows에서 직접 사용 가능

3. **`.git/hooks/pre-commit.bat`** (백업)
   - Windows Batch 버전
   - 가장 안정적인 Windows 버전

4. **`.git/hooks/pre-commit.sh.backup`** (백업)
   - 원본 sh 스크립트 백업

---

## ? 권장 설정 (Windows)

### Windows에서 가장 안정적인 방법

```powershell
# 1. 현재 sh 버전 백업
Copy-Item .git\hooks\pre-commit .git\hooks\pre-commit.sh.backup -Force

# 2. Batch 버전으로 교체
Copy-Item .git\hooks\pre-commit.bat .git\hooks\pre-commit -Force

# 3. 테스트
git commit --allow-empty -m "Test hook"
```

**장점**:
- ? Git Bash 없이도 작동
- ? Windows 네이티브 지원
- ? 오류 처리 개선

---

## ? 테스트 방법

### 1. 직접 실행 테스트

```powershell
# PowerShell 버전
.git\hooks\pre-commit.ps1

# Batch 버전
.git\hooks\pre-commit.bat

# Shell 버전 (Git Bash 필요)
.git\hooks\pre-commit
```

### 2. Git 커밋 테스트

```powershell
# 빈 커밋으로 테스트
git commit --allow-empty -m "Test pre-commit hook"

# 결과 확인:
# ? 성공: "? 민감한 정보가 발견되지 않았습니다."
# ? 실패: 오류 메시지 표시
```

### 3. 오류가 발생하는 경우

```powershell
# Hook 건너뛰고 커밋
git commit --no-verify -m "Skip hook for now"

# 또는 Hook 비활성화
Rename-Item .git\hooks\pre-commit .git\hooks\pre-commit.disabled
```

---

## ? 문제 해결 체크리스트

### Git Bash 관련
- [ ] Git Bash 설치 확인: `C:\Program Files\Git\bin\sh.exe`
- [ ] Git Bash PATH 설정 확인
- [ ] Git Bash에서 직접 실행 테스트

### PowerShell 관련
- [ ] PowerShell 실행 정책 확인: `Get-ExecutionPolicy`
- [ ] PowerShell Core 설치 확인: `pwsh --version`
- [ ] PowerShell 스크립트 직접 실행 테스트

### Git 설정 관련
- [ ] `.git/hooks/pre-commit` 파일 존재 확인
- [ ] 파일 실행 권한 확인
- [ ] Git config 확인: `git config --list`

---

## ? 팁

### 현재 사용 중인 Hook 확인

```powershell
# Hook 파일 확인
Get-Content .git\hooks\pre-commit -Head 5

# Hook 직접 실행
.git\hooks\pre-commit
```

### 오류 발생 시 로그 확인

```powershell
# Git Hook 오류 로그 (있는 경우)
Get-Content .git\hooks\pre-commit.log -ErrorAction SilentlyContinue
```

### 여러 Hook 버전 전환

```powershell
# Shell 버전 사용
Copy-Item .git\hooks\pre-commit.sh.backup .git\hooks\pre-commit -Force

# Batch 버전 사용
Copy-Item .git\hooks\pre-commit.bat .git\hooks\pre-commit -Force

# PowerShell 버전 사용 (별도 설정 필요)
Copy-Item .git\hooks\pre-commit.ps1 .git\hooks\pre-commit -Force
```

---

**작성일**: 2026년 1월 15일  
**상태**: ? 모든 버전 생성 완료  
**권장**: Windows에서는 Batch 버전 사용
