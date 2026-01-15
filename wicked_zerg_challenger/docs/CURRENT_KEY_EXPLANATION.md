# ? 현재 GEMINI_API_KEY 설명

**작성일**: 2026-01-14  
**키 값**: `AIzaSyC_Ci...MIIo`

---

## ? 이 키는 무엇인가요?

### Google Gemini API 키

`AIzaSyC_Ci...MIIo`는 **Google Gemini API 키**입니다.

**형식**:
- `AIzaSy`로 시작 (Google API 키 표준 형식)
- 총 39자 길이
- Google AI Studio에서 발급받은 키

---

## ? 현재 위치

### 환경 변수에 저장됨

**위치**: `$env:GEMINI_API_KEY` (Windows PowerShell 환경 변수)

**확인 방법**:
```powershell
$env:GEMINI_API_KEY
```

**출력**:
```
AIzaSyC_Ci...MIIo
```

---

## ? 이 키의 용도

### 프로젝트에서 사용되는 곳

1. **Gemini Self-Healing 시스템**
   - 파일: `genai_self_healing.py`
   - 용도: 자동 오류 분석 및 코드 패치 생성

2. **Build-Order Gap Analyzer**
   - 파일: `local_training/strategy_audit.py`
   - 용도: 프로 게이머 데이터와 봇 성능 비교 분석

3. **메인 봇 실행**
   - 파일: `wicked_zerg_bot_pro.py`
   - 용도: Self-Healing 시스템 초기화

---

## ?? 중요: 노출 가능성

### 왜 교체가 필요한가요?

이 키는 **이전에 Git에 커밋되었을 가능성**이 있습니다:

1. **api_keys 폴더가 Git 히스토리에 있었음**
   - Git 히스토리에서 제거했지만, 키가 노출되었을 수 있음

2. **보안 위험**
   - 키가 노출되면 다른 사람이 사용할 수 있음
   - API 사용량이 증가할 수 있음
   - 비용이 발생할 수 있음

3. **즉시 조치 필요**
   - Google AI Studio에서 키 삭제
   - 새 키 발급 및 적용

---

## ? 키 교체 방법

### 1단계: 기존 키 삭제

**Google AI Studio에서**:
1. https://makersuite.google.com/app/apikey 접속
2. 키 목록에서 `AIzaSyC_Ci...MIIo` 찾기
3. "Delete" 또는 "삭제" 클릭

### 2단계: 새 키 발급

1. Google AI Studio에서 "Create API Key" 클릭
2. 새 키 생성 및 복사

### 3단계: 새 키 적용

```powershell
# secrets/ 폴더에 저장 (권장)
echo "YOUR_NEW_API_KEY" > secrets\gemini_api.txt

# 환경 변수에서 기존 키 제거
Remove-Item Env:\GEMINI_API_KEY
```

---

## ? 키 형식 정보

### Google API 키 형식

```
AIzaSy[알파벳/숫자/특수문자 35자]
```

**현재 키 분석**:
- ? `AIzaSy`로 시작 (올바른 형식)
- ? 길이: 39자 (정상)
- ? Google API 키 표준 형식 준수

**예시**:
```
YOUR_API_KEY_HERE  ← 환경 변수에서 로드
```
```

---

## ? 키 상태 요약

| 항목 | 값 |
|------|-----|
| **키 이름** | GEMINI_API_KEY |
| **키 값** | `AIzaSyC_Ci...MIIo` |
| **저장 위치** | 환경 변수 (`$env:GEMINI_API_KEY`) |
| **형식** | ? 올바름 (Google API 키) |
| **상태** | ?? **노출 가능성 있음 - 교체 필요** |
| **용도** | Gemini Self-Healing, Gap Analyzer |

---

## ? 즉시 조치 체크리스트

- [ ] Google AI Studio에서 기존 키 삭제
- [ ] 새 API 키 발급
- [ ] `secrets/gemini_api.txt`에 새 키 저장
- [ ] 환경 변수에서 기존 키 제거
- [ ] 새 키로 테스트

---

## ? 관련 문서

- **키 교체 가이드**: `docs/API_KEY_ROTATION_GUIDE.md`
- **모든 키 상태**: `docs/ALL_API_KEYS_STATUS.md`
- **키 형식 가이드**: `docs/GEMINI_API_KEY_FORMAT.md`

---

**마지막 업데이트**: 2026-01-14
