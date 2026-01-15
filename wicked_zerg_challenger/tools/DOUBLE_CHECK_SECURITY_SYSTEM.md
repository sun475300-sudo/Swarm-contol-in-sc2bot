# 이중/삼중 보안 검사 시스템

**작성일**: 2026-01-15  
**목적**: Git 커밋 전 민감한 정보 이중/삼중 검사  
**상태**: ✅ **구축 완료**

---

## 🛡️ 보안 검사 레벨

### 1차 검사: Pre-commit Hook (자동)

**위치**: `.git/hooks/pre-commit`  
**실행 시점**: `git commit` 실행 시 **자동**  
**동작**: 민감한 정보 발견 시 **커밋 차단**

**설정 방법**:
```powershell
.\tools\setup_git_hooks.ps1
```

**특징**:
- ✅ 커밋 시 자동 실행
- ✅ 실수로 커밋하는 것을 방지
- ✅ 수동 작업 불필요

---

### 2차 검사: 수동 검사 스크립트 (권장)

**위치**: `tools/pre_commit_security_check.ps1`  
**실행 시점**: 커밋 전 **수동 실행**  
**동작**: 모든 파일 검사 후 결과 표시

**실행 방법**:
```powershell
.\tools\pre_commit_security_check.ps1
```

**특징**:
- ✅ 커밋 전 사전 확인
- ✅ 상세한 검사 결과 제공
- ✅ 문제 발견 시 파일 목록 표시

---

### 3차 검사: .gitignore (파일 추적 방지)

**위치**: `.gitignore`  
**실행 시점**: **항상** (Git이 파일을 추적하지 않음)  
**동작**: 민감한 파일 패턴 자동 제외

**포함된 패턴**:
- `**/API_KEY_*.md`
- `**/SECRET*.md`
- `**/PASSWORD*.md`
- `**/TOKEN*.md`
- `**/local.properties`
- `**/api_keys/`
- `**/secrets/`

**특징**:
- ✅ 파일 자체를 Git에서 추적하지 않음
- ✅ 실수로 `git add` 해도 추적되지 않음
- ✅ 가장 기본적인 보호 레벨

---

## 🔄 검사 프로세스

### 정상적인 커밋 흐름

```
1. 파일 수정
   ↓
2. git add .
   ↓
3. 수동 검사 실행 (권장)
   .\tools\pre_commit_security_check.ps1
   ↓
4. ✅ 검사 통과
   ↓
5. git commit -m "message"
   ↓
6. Pre-commit Hook 자동 실행
   ↓
7. ✅ 최종 검사 통과
   ↓
8. 커밋 완료 ✅
```

### 민감한 정보 발견 시

```
1. 파일 수정
   ↓
2. git add .
   ↓
3. 수동 검사 실행
   .\tools\pre_commit_security_check.ps1
   ↓
4. ❌ 민감한 정보 발견
   ↓
5. 파일 수정 (플레이스홀더로 대체)
   ↓
6. 재검사
   .\tools\pre_commit_security_check.ps1
   ↓
7. ✅ 검사 통과
   ↓
8. git commit -m "message"
   ↓
9. Pre-commit Hook 자동 실행
   ↓
10. ✅ 최종 검사 통과
   ↓
11. 커밋 완료 ✅
```

---

## 📋 커밋 전 체크리스트

### 필수 확인 사항

- [ ] **1차**: `.\tools\pre_commit_security_check.ps1` 실행
- [ ] **2차**: `git status`로 스테이징된 파일 확인
- [ ] **3차**: 민감한 파일이 `.gitignore`에 포함되어 있는지 확인
- [ ] **4차**: `git diff --cached`로 변경 내용 확인

**모든 항목이 ✅이면 안전하게 커밋할 수 있습니다.**

---

## 🔍 검사 항목 상세

### API 키 패턴

1. Google API Key: `AIzaSy[A-Za-z0-9_-]{35}`
2. OpenAI API Key: `sk-[A-Za-z0-9]{32,}`
3. Slack Token: `xox[baprs]-[0-9]{10,13}-...`
4. 일반 해시: `[0-9a-f]{32}`, `[0-9a-f]{40}`
5. 알려진 API 키: `AIzaSyBDdPWJyXs56AxeCPmqZpySFOVPjjSt_CM`

### 비밀번호/토큰 패턴

1. `password: "value"`
2. `passwd: "value"`
3. `secret: "value"`
4. `token: "value"`
5. `api_key: "value"`
6. `apikey: "value"`
7. `api_token: "value"`

### 검사 파일 확장자

- Python: `*.py`
- Kotlin/Java: `*.kt`, `*.java`
- JavaScript/TypeScript: `*.js`, `*.ts`
- 문서: `*.md`, `*.txt`
- 설정: `*.json`, `*.yaml`, `*.yml`
- 스크립트: `*.sh`, `*.ps1`, `*.bat`

---

## 🚀 빠른 시작

### 1. Git Hooks 설정 (한 번만)

```powershell
cd d:\Swarm-contol-in-sc2bot
.\wicked_zerg_challenger\tools\setup_git_hooks.ps1
```

### 2. 커밋 전 검사 (매번 실행)

```powershell
cd d:\Swarm-contol-in-sc2bot
.\wicked_zerg_challenger\tools\pre_commit_security_check.ps1
```

---

## 📊 검사 통계

### 보호 레벨

| 레벨 | 방법 | 실행 시점 | 차단 방식 |
|------|------|----------|----------|
| 1차 | Pre-commit Hook | 자동 | 커밋 차단 |
| 2차 | 수동 검사 | 수동 | 사전 확인 |
| 3차 | .gitignore | 항상 | 파일 추적 방지 |

### 검사 패턴

- **API 키 패턴**: 5개
- **비밀번호/토큰 패턴**: 7개
- **검사 파일 확장자**: 13개
- **총 검사 패턴**: 12개

---

## ⚠️ 주의사항

### False Positive (거짓 양성)

일부 패턴이 실제 키가 아닌 일반 문자열과 매칭될 수 있습니다.

**예시**:
- `password: "example"` → 검사됨 (의도된 것)
- `token: "test_token_12345"` → 검사됨 (의도된 것)

**해결**:
- 실제 키가 아닌 경우 무시하고 커밋 진행
- 또는 검사 스크립트에서 예외 패턴 추가

### 성능

대용량 파일이 많을 경우 검사 시간이 오래 걸릴 수 있습니다.

**해결**:
- 스테이징된 파일만 검사 (기본 동작)
- 필요시 특정 파일/폴더 제외

---

## 🔧 고급 설정

### 검사 패턴 추가

`tools/pre_commit_security_check.ps1` 파일 수정:

```powershell
$sensitivePatterns = @(
    # 기존 패턴들...
    
    # 새로운 패턴 추가
    "your_custom_pattern",
)
```

### 검사 파일 확장자 추가

```powershell
$fileExtensions = @(
    # 기존 확장자들...
    
    # 새로운 확장자 추가
    "*.xml",
    "*.properties",
)
```

---

## 📝 사용 예시

### 정상적인 커밋

```powershell
# 1. 파일 수정
# ... 코드 수정 ...

# 2. 스테이징
git add .

# 3. 보안 검사 (2차)
.\tools\pre_commit_security_check.ps1
# ✅ 민감한 정보가 발견되지 않았습니다.

# 4. 커밋 (1차 검사 자동 실행)
git commit -m "Update code"
# ✅ 커밋 완료
```

### 민감한 정보 발견 시

```powershell
# 1. 파일 수정
# ... 코드 수정 ...

# 2. 스테이징
git add .

# 3. 보안 검사 (2차)
.\tools\pre_commit_security_check.ps1
# ❌ 민감한 정보가 발견되었습니다!
#    파일: src/config.py
#    패턴: AIzaSy...

# 4. 파일 수정
# config.py에서 실제 API 키를 [YOUR_API_KEY]로 변경

# 5. 재검사 (2차)
.\tools\pre_commit_security_check.ps1
# ✅ 민감한 정보가 발견되지 않았습니다.

# 6. 커밋 (1차 검사 자동 실행)
git commit -m "Update code"
# ✅ 커밋 완료
```

---

## 🔗 관련 문서

- `GIT_SECURITY_CHECK_GUIDE.md` - 상세 가이드
- `COMMIT_SECURITY_CHECKLIST.md` - 커밋 전 체크리스트
- `SENSITIVE_FILES_PROTECTION.md` - 민감한 정보 보호 설정

---

**작성일**: 2026-01-15  
**상태**: ✅ **이중/삼중 검사 시스템 구축 완료**  
**보호 레벨**: 3단계 (Pre-commit Hook + 수동 검사 + .gitignore)
