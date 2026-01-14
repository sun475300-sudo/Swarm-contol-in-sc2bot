# 자동 커밋 설정 가이드

**작성 일시**: 2026년 01-13  
**목적**: 훈련 종료 후 자동 커밋 시스템 설정  
**상태**: ✅ **구현 완료**

---

## 🎯 개요

훈련이 종료되면 자동으로 변경사항을 커밋하고 GitHub 저장소에 푸시합니다.

**대상 저장소**: https://github.com/sun475300-sudo/Swarm-Control-in-sc2bot.git

---

## ⚙️ 초기 설정

### 1. 원격 저장소 확인

현재 원격 저장소 확인:
```cmd
git remote -v
```

### 2. 원격 저장소 변경 (필요 시)

현재 저장소가 다른 경우:
```cmd
git remote remove origin
git remote add origin https://github.com/sun475300-sudo/Swarm-Control-in-sc2bot.git
```

### 3. 자동 커밋 스크립트가 자동으로 설정

스크립트가 실행되면 자동으로 원격 저장소를 확인하고 필요시 설정합니다.

---

## 🚀 사용 방법

### 방법 1: 배치 파일 사용 (자동)

#### 리플레이 학습 후 자동 커밋
```cmd
bat\start_replay_learning.bat
```

훈련이 완료되면 자동으로 커밋됩니다.

#### 전체 파이프라인 후 자동 커밋
```cmd
bat\start_full_training.bat
```

모든 단계가 완료되면 자동으로 커밋됩니다.

---

### 방법 2: 수동 실행

#### 훈련 종료 후 수동 커밋
```cmd
bat\auto_commit_after_training.bat
```

또는 Python 스크립트 직접 실행:
```cmd
python tools\auto_commit_after_training.py
```

---

## 📋 자동 커밋 동작

### 커밋되는 파일
- 모델 파일 (`local_training/models/*.pt`) - `.gitignore`에 의해 제외될 수 있음
- 학습 데이터 (`data/build_orders/*.json`)
- 설정 파일 (`*.json`, `*.md`)
- 코드 변경사항 (`*.py`)
- 기타 변경된 모든 파일

### 커밋 메시지 형식
```
Training completed - Auto commit

Timestamp: 2026-01-13 15:30:45

Changes:
- Model files: 2
- Code files: 15
- Config/Doc files: 8
- Total files: 25

Training session completed successfully.
```

---

## ⚙️ 환경 변수 제어

### 자동 커밋 비활성화
```cmd
set AUTO_COMMIT_AFTER_TRAINING=false
bat\start_replay_learning.bat
```

### 자동 커밋 활성화 (기본값)
```cmd
set AUTO_COMMIT_AFTER_TRAINING=true
bat\start_replay_learning.bat
```

---

## 🔧 원격 저장소 자동 설정

스크립트가 자동으로:
1. 현재 원격 저장소 확인
2. 올바른 저장소가 아니면 자동으로 변경
3. `origin`으로 설정

**저장소 URL**: `https://github.com/sun475300-sudo/Swarm-Control-in-sc2bot.git`

---

## 📊 커밋 프로세스

1. **변경사항 확인**
   - `git status`로 변경된 파일 확인

2. **스테이징**
   - `git add -A`로 모든 변경사항 스테이징

3. **커밋**
   - 자동 생성된 커밋 메시지로 커밋

4. **푸시**
   - 현재 브랜치를 `origin`에 푸시

---

## ⚠️ 주의사항

### Git 저장소 확인
- 프로젝트가 Git 저장소인지 확인됩니다
- Git이 설치되어 있어야 합니다

### 인증
- GitHub 인증이 필요할 수 있습니다
- Personal Access Token 또는 SSH 키 설정 필요

### 충돌 처리
- 원격 저장소와 충돌이 있으면 자동 커밋이 실패할 수 있습니다
- 수동으로 해결 후 다시 실행하세요

### .gitignore
- 모델 파일(`*.pt`)은 `.gitignore`에 의해 제외될 수 있습니다
- 필요시 `.gitignore`를 수정하세요

---

## 🔍 문제 해결

### "Not a git repository" 오류
```cmd
git init
git remote add origin https://github.com/sun475300-sudo/Swarm-Control-in-sc2bot.git
```

### "Failed to push" 오류
```cmd
# 수동으로 푸시
git push -u origin main
```

### 인증 오류
- GitHub Personal Access Token 설정
- 또는 SSH 키 설정

### 원격 저장소 URL 확인
```cmd
git remote -v
```

올바른 URL이 아니면:
```cmd
git remote set-url origin https://github.com/sun475300-sudo/Swarm-Control-in-sc2bot.git
```

---

## 📁 관련 파일

- `tools/auto_commit_after_training.py` - 자동 커밋 스크립트
- `bat/auto_commit_after_training.bat` - 배치 파일 래퍼
- `bat/start_replay_learning.bat` - 리플레이 학습 (자동 커밋 포함)
- `bat/start_full_training.bat` - 전체 파이프라인 (자동 커밋 포함)

---

## ✅ 확인

자동 커밋이 성공하면:
- GitHub 저장소에 변경사항이 반영됩니다
- 커밋 메시지에 훈련 완료 시간이 기록됩니다
- 변경된 파일 수가 표시됩니다

---

**작성일**: 2026년 01-13  
**상태**: ✅ **구현 완료**
