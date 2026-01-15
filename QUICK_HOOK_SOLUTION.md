# Git Pre-commit Hook 빠른 해결 가이드

**오류**: `error: cannot spawn .git/hooks/pre-commit: No such file or directory`

---

## ? 생성된 파일

다음 파일들이 모두 생성되었습니다:

1. **`.git/hooks/pre-commit`** (현재 활성화)
   - Shell 스크립트 버전
   - Windows/Linux/Mac 지원

2. **`.git/hooks/pre-commit.ps1`** (PowerShell 버전)
   - PowerShell Core 지원

3. **`.git/hooks/pre-commit.bat`** (Windows Batch 버전) ? **권장**
   - Windows에서 가장 안정적
   - Git Bash 불필요

4. **`.git/hooks/pre-commit.sh.backup`** (백업)

---

## ? Windows에서 권장 설정

### 방법 1: Batch 버전 사용 (가장 간단)

```powershell
# 현재 sh 버전 백업
Copy-Item .git\hooks\pre-commit .git\hooks\pre-commit.sh.backup -Force

# Batch 버전으로 교체
Copy-Item .git\hooks\pre-commit.bat .git\hooks\pre-commit -Force
```

**장점**:
- ? Git Bash 불필요
- ? Windows 네이티브 지원
- ? 즉시 작동

**테스트**:
```powershell
git commit --allow-empty -m "Test hook"
```

---

## ? 2. Git Bash로 직접 실행 테스트

### Git Bash에서 실행

1. **Git Bash 열기**:
   - 프로젝트 폴더에서 우클릭 → "Git Bash Here"
   - 또는 시작 메뉴에서 "Git Bash" 실행

2. **프로젝트 루트로 이동**:
   ```bash
   cd /d/Swarm-contol-in-sc2bot
   ```

3. **Hook 직접 실행**:
   ```bash
   .git/hooks/pre-commit
   ```

4. **결과 확인**:
   - ? 정상: 보안 검사 실행 후 종료
   - ? 오류: 오류 메시지 표시

---

## ? 3. PowerShell 버전 Hook 사용

### 현재 활성화된 Hook 확인

```powershell
Get-Content .git\hooks\pre-commit -Head 5
```

### PowerShell 버전으로 변경

**주의**: Git은 `.ps1` 파일을 자동으로 실행하지 않을 수 있습니다.

**대신 Batch 버전 사용 권장** (위의 방법 1 참조)

---

## ? 4. Hook 비활성화 방법

### 방법 1: 파일 이름 변경 (임시)

```powershell
# Hook 비활성화
Rename-Item .git\hooks\pre-commit .git\hooks\pre-commit.disabled

# 나중에 다시 활성화
Rename-Item .git\hooks\pre-commit.disabled .git\hooks\pre-commit
```

### 방법 2: 커밋 시 Hook 건너뛰기

```powershell
# 이번 커밋만 Hook 건너뛰기
git commit --no-verify -m "Your message"
```

### 방법 3: Hook을 빈 파일로 만들기

```powershell
# Hook 비활성화 (빈 파일로)
Set-Content .git\hooks\pre-commit -Value "exit 0"
```

### 방법 4: 완전히 삭제

```powershell
# Hook 파일 삭제
Remove-Item .git\hooks\pre-commit
```

---

## ? 요약 및 권장사항

### Windows 사용자 권장 설정

```powershell
# 1. Batch 버전으로 교체 (가장 안정적)
Copy-Item .git\hooks\pre-commit.bat .git\hooks\pre-commit -Force

# 2. 테스트
git commit --allow-empty -m "Test hook"

# 3. 결과 확인
# ? 성공: 보안 검사 실행
# ? 실패: 오류 메시지 확인
```

### 오류가 계속 발생하는 경우

```powershell
# Hook 임시 비활성화
Rename-Item .git\hooks\pre-commit .git\hooks\pre-commit.disabled

# 또는 커밋 시 건너뛰기
git commit --no-verify -m "Your message"
```

---

## ? 테스트 방법

### 1. Hook 직접 실행 테스트

**Batch 버전**:
```powershell
.git\hooks\pre-commit.bat
```

**Shell 버전 (Git Bash 필요)**:
```bash
# Git Bash에서
.git/hooks/pre-commit
```

**PowerShell 버전**:
```powershell
.git\hooks\pre-commit.ps1
```

### 2. Git 커밋 테스트

```powershell
# 빈 커밋으로 테스트
git commit --allow-empty -m "Test pre-commit hook"

# 결과:
# ? 성공: "? 민감한 정보가 발견되지 않았습니다."
# ? 실패: 오류 메시지 표시
```

### 3. Hook이 작동하지 않는 경우

```powershell
# Hook 건너뛰고 커밋
git commit --no-verify -m "Skip hook for now"

# 또는 Hook 비활성화
Rename-Item .git\hooks\pre-commit .git\hooks\pre-commit.disabled
```

---

## ? 문제 해결 팁

### 오류가 발생하는 경우

1. **Batch 버전 사용** (가장 안정적)
   ```powershell
   Copy-Item .git\hooks\pre-commit.bat .git\hooks\pre-commit -Force
   ```

2. **Hook 임시 비활성화**
   ```powershell
   Rename-Item .git\hooks\pre-commit .git\hooks\pre-commit.disabled
   ```

3. **커밋 시 Hook 건너뛰기**
   ```powershell
   git commit --no-verify -m "Your message"
   ```

---

**작성일**: 2026년 1월 15일  
**권장**: Windows에서는 Batch 버전 (`.bat`) 사용  
**상태**: ? 모든 버전 생성 완료
