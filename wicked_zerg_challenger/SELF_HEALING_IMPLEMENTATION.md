# Gen-AI Self-Healing 구현 가이드

**작성 일시**: 2026-01-14  
**목적**: Gen-AI Self-Healing 기능 구현 완료  
**상태**: ? **모듈 구현 완료**

---

## ? 구현 완료 사항

### 1. Gen-AI Self-Healing 모듈 생성 ?

**파일**: `genai_self_healing.py`

**주요 기능:**
- Google Gemini API 통합
- 에러 발생 시 Traceback 및 소스 코드 분석
- Gemini가 원인 분석 및 수정 패치 제안
- 패치 제안 로그 저장 (자동 적용은 선택적)

---

## ? 사용 방법

### 1. API 키 설정

**환경 변수 설정:**
```bash
# Windows (CMD)
set GOOGLE_API_KEY=your_api_key_here
# 또는
set GEMINI_API_KEY=your_api_key_here

# Windows (PowerShell)
$env:GOOGLE_API_KEY="your_api_key_here"
# 또는
$env:GEMINI_API_KEY="your_api_key_here"

# Linux/Mac
export GOOGLE_API_KEY=your_api_key_here
# 또는
export GEMINI_API_KEY=your_api_key_here
```

**또는 `.env` 파일 사용:**
```
GOOGLE_API_KEY=your_api_key_here
```

---

### 2. 봇 코드에 통합

**`wicked_zerg_bot_pro.py`의 에러 핸들러에 추가:**

```python
# 파일 상단에 import 추가
from genai_self_healing import init_self_healing, get_self_healing

# 클래스 초기화 시 (예: __init__ 또는 on_start)
class WickedZergBotPro(BotAI):
    def __init__(self):
        # ... 기존 초기화 코드 ...
        
        # Gen-AI Self-Healing 초기화 (자동 패치 비활성화, 패치 제안만 저장)
        self.self_healing = init_self_healing(enable_auto_patch=False)
        
    async def on_step(self, iteration: int):
        try:
            # ... 기존 로직 ...
        except Exception as e:
            # 기존 에러 로깅 코드 ...
            
            # Gen-AI Self-Healing: 에러 분석 및 패치 제안
            if self.self_healing and self.self_healing.is_available():
                try:
                    context = {
                        'iteration': iteration,
                        'game_time': self.time,
                        'instance_id': getattr(self, 'instance_id', 0)
                    }
                    patch_suggestion = self.self_healing.analyze_error(e, context=context)
                    if patch_suggestion:
                        print(f"[SELF-HEALING] Patch suggestion generated: {patch_suggestion.description}")
                except Exception as healing_error:
                    # Self-healing 자체가 실패해도 봇은 계속 실행
                    logger.warning(f"[SELF-HEALING] Error analysis failed: {healing_error}")
```

---

## ?? 주의사항

### 1. 자동 패치 적용

**권장하지 않음:**
- 자동 패치는 코드를 변경하므로 위험할 수 있습니다
- 기본 설정: `enable_auto_patch=False` (패치 제안만 저장)
- 패치 제안을 로그로 저장하여 개발자가 검토 후 적용하도록 권장

**자동 패치를 활성화하려면 (권장하지 않음):**
```python
self.self_healing = init_self_healing(enable_auto_patch=True)
```

---

### 2. API 키 보안

**보안 권장사항:**
- API 키는 환경 변수나 `.env` 파일에만 저장
- Git에 API 키를 커밋하지 않도록 `.gitignore` 확인
- `.env` 파일은 `.gitignore`에 포함되어 있는지 확인

---

### 3. API 비용

**Gemini API 사용량:**
- 무료 티어: 일일 요청 수 제한 (확인 필요)
- 유료 플랜: 사용량에 따라 요금 발생
- 에러 발생 시에만 API 호출 (비용 최소화)

---

## ? 파일 구조

```
wicked_zerg_challenger/
├── genai_self_healing.py       # Gen-AI Self-Healing 모듈 (신규)
├── data/
│   └── self_healing/           # 패치 제안 로그 저장 디렉토리
│       └── patch_YYYYMMDD_HHMMSS.json
└── wicked_zerg_bot_pro.py      # 봇 메인 파일 (통합 필요)
```

---

## ? 다음 단계

### 1. 봇 코드 통합 (필수)

`wicked_zerg_bot_pro.py`의 에러 핸들러에 Gen-AI Self-Healing 코드 추가

### 2. API 키 설정 (필수)

Google Gemini API 키를 환경 변수 또는 `.env` 파일에 설정

### 3. 테스트 (선택)

에러를 발생시켜 패치 제안이 올바르게 생성되는지 확인

---

## ? 구현 상태

| 항목 | 상태 | 비고 |
|------|------|------|
| 모듈 구현 | ? 완료 | `genai_self_healing.py` |
| 봇 코드 통합 | ? 대기 | `wicked_zerg_bot_pro.py`에 추가 필요 |
| API 키 설정 | ? 대기 | 사용자 설정 필요 |
| 테스트 | ? 대기 | 통합 후 테스트 |

---

**생성 일시**: 2026-01-14  
**상태**: ? **모듈 구현 완료, 봇 코드 통합 대기**
