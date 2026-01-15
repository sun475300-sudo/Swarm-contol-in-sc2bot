# Git 커밋 전 보안 검사 시스템

**작성일**: 2026-01-15  
**목적**: 커밋 전 민감한 정보 이중/삼중 검사  
**상태**: ✅ **구축 완료**

---

## 🚀 빠른 시작

### 커밋 전 필수 실행 (권장)

```powershell
# 프로젝트 루트에서 실행
.\tools\double_check_before_commit.ps1
```

이 스크립트는 **이중 검사**를 수행합니다:
1. **1차**: 스테이징된 파일 검사
2. **2차**: 전체 프로젝트 검사 (선택적)

---

## 📋 사용 가능한 스크립트

### 1. `double_check_before_commit.ps1` (권장) ⭐

**기능**: 이중 검사 (스테이징된 파일 + 전체 프로젝트)

**사용법**:
```powershell
.\tools\double_check_before_commit.ps1
```

**특징**:
- ✅ 1차: 스테이징된 파일 자동 검사
- ✅ 2차: 전체 프로젝트 검사 (선택적)
- ✅ 상세한 검사 결과 제공

---

### 2. `pre_commit_security_check.ps1`

**기능**: 기본 검사 (스테이징된 파일 또는 전체 파일)

**사용법**:
```powershell
.\tools\pre_commit_security_check.ps1
```

**특징**:
- ✅ 스테이징된 파일 검사
- ✅ 빠른 실행
- ✅ Pre-commit hook에서 사용

---

### 3. `setup_git_hooks.ps1`

**기능**: Git Pre-commit Hook 설정

**사용법**:
```powershell
.\tools\setup_git_hooks.ps1
```

**특징**:
- ✅ 한 번만 실행하면 됨
- ✅ `git commit` 시 자동 검사
- ✅ 민감한 정보 발견 시 커밋 차단

---

## 🔄 권장 워크플로우

### 매번 커밋 전

```powershell
# 1. 파일 수정
# ... 코드 수정 ...

# 2. 스테이징
git add .

# 3. 이중 검사 (필수)
.\tools\double_check_before_commit.ps1

# 4. 검사 통과 시 커밋
git commit -m "Your commit message"
```

---

## 🛡️ 보안 검사 레벨

### 1차: Pre-commit Hook (자동)

- **위치**: `.git/hooks/pre-commit`
- **실행**: `git commit` 시 자동
- **동작**: 민감한 정보 발견 시 커밋 차단

### 2차: 수동 검사 (권장)

- **스크립트**: `double_check_before_commit.ps1`
- **실행**: 커밋 전 수동 실행
- **동작**: 이중 검사 (스테이징된 파일 + 전체 프로젝트)

### 3차: .gitignore (파일 추적 방지)

- **위치**: `.gitignore`
- **실행**: 항상
- **동작**: 민감한 파일 패턴 자동 제외

---

## 📝 체크리스트

### 커밋 전 필수 확인

- [ ] `.\tools\double_check_before_commit.ps1` 실행
- [ ] 1차 검사 통과 확인
- [ ] 2차 검사 실행 (선택적, 권장)
- [ ] 모든 검사 통과 확인
- [ ] `git commit` 실행

---

## 🔗 관련 문서

- `DOUBLE_CHECK_SECURITY_SYSTEM.md` - 이중/삼중 검사 시스템 상세
- `COMMIT_SECURITY_CHECKLIST.md` - 커밋 전 체크리스트
- `GIT_SECURITY_CHECK_GUIDE.md` - 상세 가이드

---

**작성일**: 2026-01-15  
**상태**: ✅ **이중/삼중 검사 시스템 구축 완료**  
**권장 사용법**: 커밋 전 `double_check_before_commit.ps1` 실행
