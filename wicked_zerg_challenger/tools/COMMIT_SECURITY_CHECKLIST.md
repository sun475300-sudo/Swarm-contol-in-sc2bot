# Git 커밋 전 보안 체크리스트

**작성일**: 2026-01-15  
**목적**: 커밋 전 필수 보안 확인 사항  
**사용법**: 커밋 전 반드시 확인

---

## 🔒 커밋 전 필수 체크리스트

### ✅ 1단계: 자동 검사 실행

```powershell
# 커밋 전 수동 검사 (권장)
.\tools\pre_commit_security_check.ps1
```

**결과 확인**:
- ✅ "민감한 정보가 발견되지 않았습니다" → 다음 단계로 진행
- ❌ "민감한 정보가 발견되었습니다" → 파일 수정 후 재검사

---

### ✅ 2단계: Git 상태 확인

```powershell
# 스테이징된 파일 확인
git status

# 스테이징된 파일 내용 확인
git diff --cached
```

**확인 사항**:
- [ ] 민감한 정보가 포함된 파일이 스테이징되지 않았는지 확인
- [ ] `.gitignore`에 포함된 파일이 실수로 추가되지 않았는지 확인

---

### ✅ 3단계: 수동 검색 (추가 확인)

```powershell
# API 키 검색
Select-String -Path "**/*" -Pattern "AIzaSy" -Recurse | Select-Object -First 10

# 비밀번호/토큰 검색
Select-String -Path "**/*" -Pattern "password|secret|token" -Recurse -CaseSensitive:$false | Select-Object -First 10
```

**확인 사항**:
- [ ] 검색 결과가 비어있거나 플레이스홀더만 있는지 확인
- [ ] 실제 키/비밀번호가 포함되지 않았는지 확인

---

### ✅ 4단계: .gitignore 확인

```powershell
# .gitignore에 포함된 파일이 스테이징되지 않았는지 확인
git ls-files | Select-String -Pattern "api_key|secret|password|token|local.properties"
```

**확인 사항**:
- [ ] 결과가 비어있어야 함 (추적되지 않음)
- [ ] 민감한 파일이 Git에 추가되지 않았는지 확인

---

## 🚨 발견 시 조치

### 민감한 정보 발견 시

1. **파일 수정**:
   ```powershell
   # 파일에서 실제 키 제거
   # 플레이스홀더로 대체: [YOUR_API_KEY], [API_KEY]
   ```

2. **Git 캐시에서 제거** (이미 스테이징된 경우):
   ```powershell
   git reset HEAD <파일경로>
   ```

3. **재검사**:
   ```powershell
   .\tools\pre_commit_security_check.ps1
   ```

4. **커밋**:
   ```powershell
   git commit -m "Your commit message"
   ```

---

## 📋 빠른 체크리스트

커밋 전 **반드시** 확인:

- [ ] `.\tools\pre_commit_security_check.ps1` 실행 ✅
- [ ] 검사 결과 확인 (민감한 정보 없음) ✅
- [ ] `git status`로 스테이징된 파일 확인 ✅
- [ ] 민감한 파일이 포함되지 않았는지 확인 ✅
- [ ] `.gitignore`에 포함된 파일이 추가되지 않았는지 확인 ✅

**모든 항목이 ✅이면 안전하게 커밋할 수 있습니다.**

---

## 🔧 Git Hooks 설정 (한 번만)

```powershell
# Git Hooks 자동 설정
.\tools\setup_git_hooks.ps1
```

이 명령어를 실행하면 `git commit` 시 자동으로 검사가 실행됩니다.

---

## 📝 예시 워크플로우

### 정상적인 커밋

```powershell
# 1. 파일 수정
# ... 코드 수정 ...

# 2. 스테이징
git add .

# 3. 보안 검사
.\tools\pre_commit_security_check.ps1
# ✅ 민감한 정보가 발견되지 않았습니다.

# 4. 커밋
git commit -m "Update code"
```

### 민감한 정보 발견 시

```powershell
# 1. 파일 수정
# ... 코드 수정 ...

# 2. 스테이징
git add .

# 3. 보안 검사
.\tools\pre_commit_security_check.ps1
# ❌ 민감한 정보가 발견되었습니다!
#    파일: src/config.py
#    패턴: AIzaSy...

# 4. 파일 수정
# config.py에서 실제 API 키를 [YOUR_API_KEY]로 변경

# 5. 재검사
.\tools\pre_commit_security_check.ps1
# ✅ 민감한 정보가 발견되지 않았습니다.

# 6. 커밋
git commit -m "Update code"
```

---

## 🎯 검사 레벨

### 1차: Pre-commit Hook (자동)

- **위치**: `.git/hooks/pre-commit`
- **실행 시점**: `git commit` 실행 시 자동
- **동작**: 민감한 정보 발견 시 커밋 차단

### 2차: 수동 검사 (권장)

- **위치**: `tools/pre_commit_security_check.ps1`
- **실행 시점**: 커밋 전 수동 실행
- **동작**: 모든 파일 검사 후 결과 표시

### 3차: .gitignore (파일 추적 방지)

- **위치**: `.gitignore`
- **실행 시점**: 항상 (Git이 파일을 추적하지 않음)
- **동작**: 민감한 파일 패턴 자동 제외

---

## 📊 검사 통계

### 검사 패턴

- **API 키 패턴**: 5개
- **비밀번호/토큰 패턴**: 4개
- **검사 파일 확장자**: 13개

### 보호 레벨

- **1차 (Pre-commit Hook)**: 자동 차단 ✅
- **2차 (수동 검사)**: 사전 확인 ✅
- **3차 (.gitignore)**: 파일 추적 방지 ✅

---

## 🔗 관련 문서

- `GIT_SECURITY_CHECK_GUIDE.md` - 상세 가이드
- `SENSITIVE_FILES_PROTECTION.md` - 민감한 정보 보호 설정
- `SECURITY_AUDIT_FINAL_VERIFICATION.md` - 보안 감사 최종 확인

---

**작성일**: 2026-01-15  
**상태**: ✅ **이중/삼중 검사 시스템 구축 완료**  
**사용법**: 커밋 전 반드시 체크리스트 확인
