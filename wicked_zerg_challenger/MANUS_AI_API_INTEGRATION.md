# Manus AI API 통합 가이드

**작성일**: 2026-01-16

## 개요

Manus AI API (`api.manus.ai`)를 사용하여 AI 작업을 생성하고 관리할 수 있는 클라이언트를 구현했습니다.

## 기본 사용법

### Base URL
```
https://api.manus.ai
```

### 인증
모든 요청에 `API_KEY` 헤더를 포함해야 합니다:
```
API_KEY: your-api-key
```

## 환경 변수 설정

### PowerShell
```powershell
$env:MANUS_AI_API_URL = "https://api.manus.ai"
$env:MANUS_AI_API_KEY = "your-api-key-here"
$env:MANUS_AI_ENABLED = "1"
```

### Windows CMD
```cmd
set MANUS_AI_API_URL=https://api.manus.ai
set MANUS_AI_API_KEY=your-api-key-here
set MANUS_AI_ENABLED=1
```

### Linux/Mac
```bash
export MANUS_AI_API_URL=https://api.manus.ai
export MANUS_AI_API_KEY=your-api-key-here
export MANUS_AI_ENABLED=1
```

### 파일에서 API 키 로드 (선택적)

다음 경로 중 하나에 API 키 파일을 생성할 수 있습니다:
- `monitoring/api_keys/manus_ai_api_key.txt`
- `api_keys/manus_ai_api_key.txt`
- `secrets/manus_ai_api_key.txt`

## 주요 기능

### 1. Projects (프로젝트)

#### 프로젝트 목록 조회
```python
from monitoring.manus_ai_client import create_client_from_env

client = create_client_from_env()
projects = client.list_projects()
```

#### 프로젝트 생성
```python
project = client.create_project(
    name="SC2 AI Bot",
    description="StarCraft II AI Bot 프로젝트"
)
```

#### 프로젝트 조회
```python
project = client.get_project(project_id="project-123")
```

### 2. Tasks (작업)

#### 작업 생성
```python
task = client.create_task(
    prompt="Write a function to calculate fibonacci numbers",
    agent_profile="manus-1.6"
)
```

#### 작업 목록 조회
```python
tasks = client.list_tasks(limit=20)
```

#### 특정 프로젝트의 작업 목록
```python
tasks = client.list_tasks(project_id="project-123", limit=20)
```

#### 작업 조회
```python
task = client.get_task(task_id="task-456")
```

#### 작업 수정
```python
updated_task = client.update_task(
    task_id="task-456",
    prompt="Updated prompt"
)
```

#### 작업 삭제
```python
success = client.delete_task(task_id="task-456")
```

### 3. Files (파일)

#### 파일 업로드
```python
file_info = client.upload_file(
    file_path="data/training_results.json",
    project_id="project-123"  # 선택적
)
```

#### 파일 목록 조회
```python
files = client.list_files(project_id="project-123")  # 선택적
```

### 4. Webhooks (웹훅)

#### 웹훅 생성
```python
webhook = client.create_webhook(
    url="https://your-server.com/webhooks/manus",
    events=["task.completed", "task.failed"],
    project_id="project-123"  # 선택적
)
```

#### 웹훅 목록 조회
```python
webhooks = client.list_webhooks(project_id="project-123")  # 선택적
```

## 사용 예제

### 기본 예제

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from monitoring.manus_ai_client import create_client_from_env

# 클라이언트 생성
client = create_client_from_env()

if not client or not client.enabled:
    print("Manus AI 클라이언트가 비활성화되어 있습니다.")
    exit(1)

# 헬스 체크
if client.health_check():
    print("? Manus AI API 연결 성공")
else:
    print("? Manus AI API 연결 실패")
    exit(1)

# 프로젝트 생성
project = client.create_project(
    name="SC2 AI Training",
    description="StarCraft II AI 학습 프로젝트"
)

if project:
    project_id = project.get("id")
    print(f"? 프로젝트 생성 성공: {project_id}")

    # 작업 생성
    task = client.create_task(
        prompt="Analyze SC2 replay data and suggest improvements",
        agent_profile="manus-1.6",
        project_id=project_id
    )

    if task:
        task_id = task.get("id")
        print(f"? 작업 생성 성공: {task_id}")
```

### SC2 AI Bot 통합 예제

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from monitoring.manus_ai_client import create_client_from_env
import json

def analyze_training_results_with_manus(results_path: str):
    """학습 결과를 Manus AI로 분석"""
    client = create_client_from_env()
    
    if not client or not client.enabled:
        print("Manus AI가 비활성화되어 있습니다.")
        return None
    
    # 학습 결과 파일 읽기
    with open(results_path, 'r', encoding='utf-8') as f:
        results = json.load(f)
    
    # Manus AI에게 분석 요청
    prompt = f"""
    다음 StarCraft II AI 학습 결과를 분석하고 개선 사항을 제안해주세요:
    
    {json.dumps(results, indent=2, ensure_ascii=False)}
    
    분석 항목:
    1. 승률 트렌드
    2. 성능 병목 지점
    3. 개선 가능한 전략
    4. 최적화 제안
    """
    
    task = client.create_task(
        prompt=prompt,
        agent_profile="manus-1.6"
    )
    
    if task:
        task_id = task.get("id")
        print(f"? 분석 작업 생성: {task_id}")
        return task_id
    
    return None
```

## API 엔드포인트 요약

### Projects
- `GET /v1/projects` - 프로젝트 목록
- `GET /v1/projects/{id}` - 프로젝트 조회
- `POST /v1/projects` - 프로젝트 생성

### Tasks
- `GET /v1/tasks` - 작업 목록
- `GET /v1/tasks/{id}` - 작업 조회
- `POST /v1/tasks` - 작업 생성
- `PUT /v1/tasks/{id}` - 작업 수정
- `DELETE /v1/tasks/{id}` - 작업 삭제

### Files
- `GET /v1/files` - 파일 목록
- `POST /v1/files` - 파일 업로드

### Webhooks
- `GET /v1/webhooks` - 웹훅 목록
- `POST /v1/webhooks` - 웹훅 생성

## 에러 처리

클라이언트는 자동으로 재시도합니다 (최대 3회):

```python
try:
    task = client.create_task(prompt="...")
    if not task:
        print("작업 생성 실패 (재시도 후에도 실패)")
except Exception as e:
    print(f"오류 발생: {e}")
```

## 로깅

클라이언트는 모든 작업을 로깅합니다:
- `INFO`: 성공적인 작업
- `WARNING`: 실패한 작업 (재시도 전)
- `ERROR`: 최종 실패

## 테스트

```bash
cd wicked_zerg_challenger/monitoring
python manus_ai_client.py
```

## 참고

- 기존 `manus_dashboard_client.py` (`manus.im`)와 별개의 클라이언트입니다
- 두 클라이언트를 동시에 사용할 수 있습니다
- 환경 변수 구분:
  - `manus_dashboard_client.py`: `MANUS_DASHBOARD_URL`, `MANUS_DASHBOARD_API_KEY`
  - `manus_ai_client.py`: `MANUS_AI_API_URL`, `MANUS_AI_API_KEY`

## API Reference

더 자세한 내용은 [Manus AI API Reference](https://api.manus.ai/docs)를 참고하세요.
