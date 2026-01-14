# ? API Keys 관리 폴더

**?? 중요: 이 폴더의 모든 파일은 Git에 올라가지 않습니다!**

## ? 사용 방법

### 1. API 키 파일 생성

이 폴더에 각 API 키별로 텍스트 파일을 생성하세요:

- `GEMINI_API_KEY.txt` - Google Gemini API 키
- `GOOGLE_API_KEY.txt` - Google API 키 (Gemini Self-Healing용)
- `GCP_PROJECT_ID.txt` - Google Cloud Platform 프로젝트 ID
- `GCP_CREDENTIALS.json` - GCP 서비스 계정 키 (JSON 파일)

### 2. 파일 형식

각 파일에는 **API 키만** 저장하세요 (줄바꿈 없이):

```

```

또는 마크다운 형식으로:

```markdown
# Gemini API Key

```

### 3. 코드에서 사용하기

Python 코드에서 API 키를 읽는 예시:

```python
import os
from pathlib import Path

def load_api_key(key_name: str) -> str:
    """API 키 파일에서 키를 읽어옵니다."""
    api_keys_dir = Path(__file__).parent.parent / "api_keys"
    key_file = api_keys_dir / f"{key_name}.txt"
    
    if key_file.exists():
        with open(key_file, 'r', encoding='utf-8') as f:
            # 첫 번째 줄만 읽기 (주석 제외)
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    return line
    
    # 환경 변수에서도 시도
    return os.environ.get(key_name, "")

# 사용 예시
gemini_key = load_api_key("GEMINI_API_KEY")
google_key = load_api_key("GOOGLE_API_KEY")
```

### 4. 환경 변수로 설정 (선택사항)

또는 환경 변수로 설정할 수도 있습니다:

**Windows (PowerShell)**:
```powershell
$env:GOOGLE_API_KEY = Get-Content "api_keys\GOOGLE_API_KEY.txt"
```

**Windows (CMD)**:
```cmd
set /p GOOGLE_API_KEY=<api_keys\GOOGLE_API_KEY.txt
```

**Linux/Mac**:
```bash
export GOOGLE_API_KEY=$(cat api_keys/GOOGLE_API_KEY.txt)
```

## ? 현재 필요한 API 키 목록

### 필수 키

- [ ] `GEMINI_API_KEY.txt` - Gemini AI 사용
- [ ] `GOOGLE_API_KEY.txt` - Google API 사용 (Gemini Self-Healing)

### 선택적 키

- [ ] `GCP_PROJECT_ID.txt` - Google Cloud Platform 사용 시
- [ ] `GCP_CREDENTIALS.json` - Vertex AI 사용 시

## ? 보안 주의사항

1. **절대 Git에 커밋하지 마세요!**
   - `.gitignore`에 `api_keys/` 폴더가 이미 추가되어 있습니다
   - 실수로 커밋했다면 즉시 키를 재생성하세요

2. **파일 권한 설정** (Linux/Mac):
   ```bash
   chmod 600 api_keys/*.txt
   ```

3. **백업 시 주의**:
   - API 키 파일은 암호화된 백업에만 포함하세요
   - 클라우드 백업 시 암호화 확인

4. **키 공유 금지**:
   - API 키는 개인용으로만 사용하세요
   - 팀 공유가 필요하면 환경 변수나 보안 저장소 사용

## ? API 키 발급 링크

- **Gemini API**: https://makersuite.google.com/app/apikey
- **Google Cloud**: https://console.cloud.google.com/apis/credentials
- **Vertex AI**: https://console.cloud.google.com/vertex-ai

## ? 확인 방법

Git에 올라가지 않았는지 확인:

```bash
git status
# api_keys/ 폴더가 나타나지 않아야 합니다
```

## ? 문제 해결

### 키가 작동하지 않을 때

1. 파일 인코딩 확인 (UTF-8)
2. 공백/줄바꿈 제거 확인
3. 키가 만료되지 않았는지 확인
4. 환경 변수 설정 확인

### Git에 실수로 커밋했을 때

1. 즉시 키 재생성
2. Git 히스토리에서 제거:
   ```bash
   git rm --cached api_keys/*
   git commit -m "Remove API keys from tracking"
   ```
3. `.gitignore` 확인

---

**마지막 업데이트**: 2026-01-14
