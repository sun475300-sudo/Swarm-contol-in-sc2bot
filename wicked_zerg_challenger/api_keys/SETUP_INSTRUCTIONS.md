# ? API Keys 설정 가이드

## 빠른 시작 (3단계)

### 1단계: 예시 파일 복사

```powershell
# Windows
cd api_keys
copy GEMINI_API_KEY.txt.example GEMINI_API_KEY.txt
copy GOOGLE_API_KEY.txt.example GOOGLE_API_KEY.txt
```

```bash
# Linux/Mac
cd api_keys
cp GEMINI_API_KEY.txt.example GEMINI_API_KEY.txt
cp GOOGLE_API_KEY.txt.example GOOGLE_API_KEY.txt
```

### 2단계: 실제 키 입력

생성한 파일을 열고 `YOUR_API_KEY_HERE`를 실제 API 키로 교체하세요.

**GEMINI_API_KEY.txt**:
```
YOUR_API_KEY_HERE
```

### 3단계: 확인

```bash
# Git에 올라가지 않는지 확인
git status api_keys/
# GEMINI_API_KEY.txt는 나타나지 않아야 합니다
```

## ? 완료!

이제 코드에서 API 키를 사용할 수 있습니다:

```python
from tools.load_api_key import get_gemini_api_key

api_key = get_gemini_api_key()
```

## ? 더 자세한 정보

- **상세 가이드**: `api_keys/README.md`
- **관리 가이드**: `docs/API_KEYS_MANAGEMENT.md`
