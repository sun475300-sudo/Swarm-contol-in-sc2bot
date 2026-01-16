# 민감 정보 보안 설정 완료

**작성일**: 2026-01-16

## 개요

민감 정보(API 키, 비밀번호, 토큰 등)가 Git에 커밋되지 않도록 보안 설정을 강화했습니다.

## 설정 완료 항목

### 1. `.gitignore` 강화 ?

다음 패턴이 추가되었습니다:
- API 키 파일: `**/*_api_key*.txt`, `**/*api_key*.*`
- 비밀번호 파일: `**/*password*.txt`, `**/*secret*.txt`
- 토큰 파일: `**/*token*.txt`
- 인증서 파일: `*.key`, `*.pem`, `*.p12`, `*.pfx`
- 환경 변수 파일: `.env`, `.env.local`
- 설정 파일: `**/*config.local*`

### 2. Pre-commit Hook 추가 ?

`.git/hooks/pre-commit` 훅이 생성되어 커밋 전에 민감 정보를 자동으로 검사합니다.

**검사 항목:**
- Manus AI API Key 패턴
- AWS Access Key
- Google API Key
- GitHub Personal Access Token
- Slack Token
- Stripe Secret Key
- Private Keys
- 코드 내 하드코딩된 비밀번호/API 키

### 3. 민감 정보 검사 도구 ?

`tools/check_sensitive_info.py` 도구를 사용하여 수동으로 검사할 수 있습니다.

## 사용 방법

### Pre-commit Hook 자동 검사

커밋할 때 자동으로 민감 정보를 검사합니다:

```bash
git add .
git commit -m "Update code"
```

**민감 정보가 발견되면:**
```
[ERROR] Sensitive information detected in: some_file.py
  Pattern: sk-[A-Za-z0-9_-]{48,}
? Commit rejected: Sensitive information detected
```

### 수동 검사

```bash
cd wicked_zerg_challenger
python tools/check_sensitive_info.py
```

또는 특정 경로 검사:

```bash
python tools/check_sensitive_info.py --path monitoring/
```

## 보안 체크리스트

### ? 완료된 항목

1. `.gitignore`에 API 키 패턴 추가
2. `.gitignore`에 비밀번호/토큰 패턴 추가
3. `.gitignore`에 인증서 파일 패턴 추가
4. Pre-commit hook 추가
5. 민감 정보 검사 도구 생성
6. 문서에서 실제 API 키 제거

### ?? 확인 필요 항목

1. **이미 커밋된 민감 정보 확인**
   ```bash
   git log --all --full-history --source -- "*api_key*" "*secret*" "*password*"
   ```

2. **Git 캐시에서 민감 파일 제거** (이미 커밋된 경우)
   ```bash
   git rm --cached monitoring/api_keys/manus_ai_api_key.txt
   git commit -m "Remove sensitive file from Git"
   ```

3. **이미 커밋된 민감 정보 제거** (Git 히스토리 정리)
   - `git filter-branch` 또는 `git-filter-repo` 사용
   - **주의**: 히스토리를 다시 작성하므로 협업 시 신중히 진행

## 현재 보호되는 파일

다음 파일들은 Git에서 자동으로 제외됩니다:

- `monitoring/api_keys/manus_ai_api_key.txt`
- `**/api_keys/**/*.txt`
- `**/secrets/**/*`
- `.env`, `.env.local`
- `*.key`, `*.pem`
- 모든 `*_api_key*` 패턴 파일

## 문제 해결

### Pre-commit Hook이 작동하지 않는 경우

1. **파일 권한 확인** (Linux/Mac):
   ```bash
   chmod +x .git/hooks/pre-commit
   ```

2. **Windows에서 실행**:
   ```bash
   # Git Bash에서 실행하거나
   bash .git/hooks/pre-commit
   ```

### Hook 검사를 일시적으로 건너뛰기 (비권장)

```bash
git commit --no-verify -m "Emergency commit"
```

**?? 경고**: 이 방법은 민감 정보가 커밋될 수 있으므로 사용하지 마세요.

## API 키 사용 권장 사항

### ? 권장 방법

1. **파일에서 자동 로드**:
   ```python
   from monitoring.manus_ai_client import create_client_from_env
   client = create_client_from_env()  # 자동으로 파일에서 로드
   ```

2. **환경 변수 사용**:
   ```bash
   export MANUS_AI_API_KEY=your-key
   ```

### ? 피해야 할 방법

1. **코드에 하드코딩**:
   ```python
   api_key = "sk-..."  # ? 절대 하지 마세요!
   ```

2. **문서에 실제 키 포함**:
   ```markdown
   API_KEY=sk-...  # ? 실제 키를 문서에 포함하지 마세요
   ```

## 참고

- Pre-commit hook: `.git/hooks/pre-commit`
- 민감 정보 검사 도구: `tools/check_sensitive_info.py`
- API 키 설정 가이드: `MANUS_AI_API_KEY_SETUP.md`

## 다음 단계

1. ? `.gitignore` 강화 완료
2. ? Pre-commit hook 추가 완료
3. ? 검사 도구 생성 완료
4. ? 이미 커밋된 민감 정보 확인 및 제거 (필요 시)

**보안 관련 문의**: 민감 정보가 발견되면 즉시 재생성하고 Git 히스토리를 정리하세요.
