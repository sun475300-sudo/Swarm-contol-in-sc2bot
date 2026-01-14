# README 자동 생성 가이드

**작성 일시**: 2026년 01-13  
**목적**: README 파일 자동 생성 스크립트 사용법  
**상태**: ✅ **구현 완료**

---

## 🎯 개요

`generate_readme.py` 스크립트를 사용하여 한국어/영어 README 파일을 자동으로 생성할 수 있습니다.

---

## 🚀 사용 방법

### 기본 사용법

#### 영어 버전만 생성 (기본값)
```cmd
python generate_readme.py
```
→ `README.md` 파일 생성

#### 한국어 버전만 생성
```cmd
python generate_readme.py --lang ko
```
→ `README_ko.md` 파일 생성

#### 둘 다 생성 (권장)
```cmd
python generate_readme.py --lang both
```
→ `README.md`와 `README_ko.md` 모두 생성

---

## ⚙️ 고급 옵션

### 작성자 정보 변경

이름이나 이메일을 변경하려면:

```cmd
python generate_readme.py --lang both --ko-name "장성원" --en-name "Jang S.W." --email "myemail@example.com"
```

---

## 📋 생성되는 파일

### README.md (영어)
- 프로젝트 개요 (영어)
- 시스템 아키텍처
- 핵심 기능 설명
- 기술 스택
- 연락처 정보

### README_ko.md (한국어)
- 프로젝트 개요 (한국어)
- 부모님을 위한 요약 설명
- 시스템 아키텍처
- 핵심 기능 설명
- 엔지니어링 트러블슈팅
- 기술 스택
- 진로 연계성
- 연락처 정보

---

## 🔧 스크립트 수정

README 내용을 변경하려면:

1. `generate_readme.py` 파일 열기
2. `README_KO` 또는 `README_EN` 변수 내의 텍스트 수정
3. 스크립트 실행:
   ```cmd
   python generate_readme.py --lang both
   ```

---

## 📁 파일 위치

- **스크립트**: `generate_readme.py` (프로젝트 루트)
- **생성 파일**: 
  - `README.md` (프로젝트 루트)
  - `README_ko.md` (프로젝트 루트)

---

## ✅ 확인

스크립트 실행 후:
- `[OK] Wrote: README.md` 메시지 확인
- `[OK] Wrote: README_ko.md` 메시지 확인 (--lang both 사용 시)
- 생성된 파일이 프로젝트 루트에 있는지 확인

---

## 💡 팁

### 자동 커밋과 함께 사용

훈련 종료 후 자동 커밋 시 README도 함께 업데이트하려면:

```cmd
python generate_readme.py --lang both
bat\auto_commit_after_training.bat
```

또는 배치 파일에 통합:
```batch
python generate_readme.py --lang both
python tools\auto_commit_after_training.py
```

---

**작성일**: 2026년 01-13  
**상태**: ✅ **구현 완료**
