# 파일 브라우저 API 가이드

**작성일**: 2026-01-16

## 개요

`dashboard_api.py`에 `local_training` 폴더와 `sc2-mobile-app` 폴더를 웹/모바일 앱에서 탐색할 수 있는 파일 브라우저 API가 추가되었습니다.

## API 엔드포인트

### 1. local_training 폴더 파일 목록

```http
GET /api/files/local-training?path=scripts
```

**파라미터**:
- `path` (optional): 상대 경로 (예: "scripts", "models", "logs")

**응답 예시**:
```json
{
  "base": "local_training",
  "path": "scripts",
  "items": [
    {
      "name": "replay_learning_manager.py",
      "type": "file",
      "size": 15234,
      "modified": "2026-01-15T10:30:00",
      "path": "scripts/replay_learning_manager.py"
    },
    {
      "name": "models",
      "type": "directory",
      "size": null,
      "modified": "2026-01-15T10:30:00",
      "path": "models"
    }
  ],
  "count": 2
}
```

### 2. sc2-mobile-app 폴더 파일 목록

```http
GET /api/files/sc2-mobile-app?path=src/pages
```

**파라미터**:
- `path` (optional): 상대 경로 (예: "src", "src/pages", "public")

**응답 예시**:
```json
{
  "base": "sc2-mobile-app",
  "path": "src/pages",
  "items": [
    {
      "name": "Dashboard.tsx",
      "type": "file",
      "size": 8234,
      "modified": "2026-01-15T10:30:00",
      "path": "src/pages/Dashboard.tsx"
    }
  ],
  "count": 1
}
```

### 3. 파일 내용 조회

```http
GET /api/files/content?base=local_training&path=scripts/main_integrated.py
```

**파라미터**:
- `base` (required): "local_training" 또는 "sc2-mobile-app"
- `path` (required): 파일의 상대 경로
- `max_size` (optional): 최대 파일 크기 (기본값: 1MB)

**응답 예시** (텍스트 파일):
```json
{
  "base": "local_training",
  "path": "scripts/main_integrated.py",
  "content": "# -*- coding: utf-8 -*-\\n...",
  "type": "text",
  "size": 15234,
  "encoding": "utf-8"
}
```

**응답 예시** (바이너리 파일):
```json
{
  "base": "local_training",
  "path": "models/model.pth",
  "content": null,
  "type": "binary",
  "size": 52428800,
  "message": "Binary file - content not available. Use download endpoint."
}
```

### 4. 폴더 통계

```http
GET /api/files/stats?base=local_training&path=scripts
```

**파라미터**:
- `base` (required): "local_training" 또는 "sc2-mobile-app"
- `path` (optional): 폴더의 상대 경로

**응답 예시**:
```json
{
  "base": "local_training",
  "path": "scripts",
  "statistics": {
    "files": 17,
    "directories": 2,
    "total_size": 524288,
    "total_size_mb": 0.5
  }
}
```

## 보안

- **Path Traversal 방지**: `../` 또는 절대 경로 사용 시 403 에러 반환
- **허용된 디렉토리만 접근**: `ALLOWED_BASE_DIRS`에 정의된 디렉토리만 접근 가능
- **파일 크기 제한**: 기본 최대 1MB (설정 가능)

## 모바일 앱 통합 예시

### React/TypeScript 예시

```typescript
// lib/api.ts에 추가
export async function listLocalTrainingFiles(path: string = '') {
  const response = await fetch(
    `${API_BASE_URL}/api/files/local-training?path=${encodeURIComponent(path)}`
  );
  return response.json();
}

export async function getFileContent(base: string, path: string) {
  const response = await fetch(
    `${API_BASE_URL}/api/files/content?base=${base}&path=${encodeURIComponent(path)}`
  );
  return response.json();
}
```

### 파일 브라우저 컴포넌트 예시

```tsx
import { useState, useEffect } from 'react';
import { listLocalTrainingFiles, getFileContent } from '../lib/api';

export function FileBrowser({ base }: { base: 'local_training' | 'sc2-mobile-app' }) {
  const [files, setFiles] = useState([]);
  const [currentPath, setCurrentPath] = useState('');
  const [selectedFile, setSelectedFile] = useState(null);

  useEffect(() => {
    loadFiles(currentPath);
  }, [currentPath]);

  async function loadFiles(path: string) {
    const data = await listLocalTrainingFiles(path);
    setFiles(data.items);
  }

  async function handleFileClick(file: any) {
    if (file.type === 'directory') {
      setCurrentPath(file.path);
    } else {
      const content = await getFileContent(base, file.path);
      setSelectedFile(content);
    }
  }

  return (
    <div>
      <div className="breadcrumb">
        <button onClick={() => setCurrentPath('')}>Root</button>
        {currentPath && <span> / {currentPath}</span>}
      </div>
      <ul>
        {files.map(file => (
          <li key={file.path} onClick={() => handleFileClick(file)}>
            {file.type === 'directory' ? '?' : '?'} {file.name}
            {file.size && <span>({file.size} bytes)</span>}
          </li>
        ))}
      </ul>
      {selectedFile && (
        <div className="file-content">
          <pre>{selectedFile.content}</pre>
        </div>
      )}
    </div>
  );
}
```

## 테스트

### cURL 예시

```bash
# local_training 폴더 목록
curl "http://localhost:8001/api/files/local-training"

# scripts 폴더 목록
curl "http://localhost:8001/api/files/local-training?path=scripts"

# 파일 내용 조회
curl "http://localhost:8001/api/files/content?base=local_training&path=scripts/main_integrated.py"

# sc2-mobile-app 폴더 목록
curl "http://localhost:8001/api/files/sc2-mobile-app"

# 폴더 통계
curl "http://localhost:8001/api/files/stats?base=local_training&path=scripts"
```

## 서버 실행

```bash
cd wicked_zerg_challenger/monitoring
uvicorn dashboard_api:app --host 0.0.0.0 --port 8001
```

또는 배치 파일:

```bash
cd wicked_zerg_challenger/bat
start_dashboard_with_ngrok.bat
```

## 다음 단계

1. 모바일 앱에 파일 브라우저 페이지 추가
2. 파일 내용 편집 기능 (선택적)
3. 파일 다운로드 기능 추가
4. 파일 업로드 기능 추가 (선택적)
