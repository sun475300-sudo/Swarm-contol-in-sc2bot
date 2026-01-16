# sc2-ai-dashboard 웹 통합 완료

**작성일**: 2026-01-16

## 개요

`local_training` 폴더와 `sc2-ai-dashboard` 폴더를 웹에서 볼 수 있도록 `dashboard_api.py`에 파일 브라우저 API를 통합했습니다.

## 통합된 폴더

1. **local_training** - 로컬 학습 데이터 폴더
2. **sc2-mobile-app** - 모바일 앱 폴더
3. **sc2-ai-dashboard** - AI 대시보드 폴더 (신규 추가)

## API 엔드포인트

### 1. 파일 목록 조회

#### local_training 폴더
```
GET /api/files/local-training?path=
```
- **파라미터**: `path` (선택적) - 하위 경로
- **응답**: 폴더 내 파일 및 디렉토리 목록

#### sc2-ai-dashboard 폴더
```
GET /api/files/sc2-ai-dashboard?path=
```
- **파라미터**: `path` (선택적) - 하위 경로
- **응답**: 폴더 내 파일 및 디렉토리 목록

#### sc2-mobile-app 폴더
```
GET /api/files/sc2-mobile-app?path=
```
- **파라미터**: `path` (선택적) - 하위 경로
- **응답**: 폴더 내 파일 및 디렉토리 목록

### 2. 파일 내용 조회

```
GET /api/files/content?base={base}&path={path}
```

- **파라미터**:
  - `base`: 폴더 키 (`local_training`, `sc2-ai-dashboard`, `sc2-mobile-app`)
  - `path`: 파일 경로 (상대 경로)
  - `max_size`: 최대 파일 크기 (기본값: 1MB)
- **응답**: 텍스트 파일 내용 (UTF-8)

### 3. 폴더 통계

```
GET /api/files/stats?base={base}&path={path}
```

- **파라미터**:
  - `base`: 폴더 키 (`local_training`, `sc2-ai-dashboard`, `sc2-mobile-app`)
  - `path`: 폴더 경로 (선택적)
- **응답**: 폴더 통계 (파일 수, 디렉토리 수, 총 크기)

## 사용 예제

### 1. sc2-ai-dashboard 루트 폴더 목록 조회

```bash
curl http://localhost:8001/api/files/sc2-ai-dashboard
```

**응답 예시:**
```json
{
  "base": "sc2-ai-dashboard",
  "path": "",
  "items": [
    {
      "name": "src",
      "type": "directory",
      "size": null,
      "modified": "2026-01-16T12:34:56",
      "path": "src"
    },
    {
      "name": "README.md",
      "type": "file",
      "size": 1234,
      "modified": "2026-01-16T12:34:56",
      "path": "README.md"
    }
  ],
  "count": 2
}
```

### 2. 하위 폴더 조회

```bash
curl "http://localhost:8001/api/files/sc2-ai-dashboard?path=src/components"
```

### 3. 파일 내용 조회

```bash
curl "http://localhost:8001/api/files/content?base=sc2-ai-dashboard&path=README.md"
```

**응답 예시:**
```json
{
  "base": "sc2-ai-dashboard",
  "path": "README.md",
  "content": "# SC2 AI Dashboard\n\n...",
  "type": "text",
  "size": 1234,
  "encoding": "utf-8"
}
```

### 4. 폴더 통계 조회

```bash
curl "http://localhost:8001/api/files/stats?base=sc2-ai-dashboard"
```

**응답 예시:**
```json
{
  "base": "sc2-ai-dashboard",
  "path": "",
  "statistics": {
    "files": 125,
    "directories": 15,
    "total_size": 5242880,
    "total_size_mb": 5.0
  }
}
```

## 보안 기능

### 1. 경로 탐색 공격 방지

- `..` 및 절대 경로(`/`) 차단
- 모든 경로가 허용된 기본 디렉토리 내부인지 검증
- 경로 정규화 및 검증

### 2. 허용된 기본 디렉토리

```python
ALLOWED_BASE_DIRS = {
    "local_training": Path(__file__).parent.parent / "local_training",
    "sc2-mobile-app": Path("D:/Swarm-contol-in-sc2bot/sc2-mobile-app"),
    "sc2-ai-dashboard": Path("D:/Swarm-contol-in-sc2bot/sc2-ai-dashboard"),
}
```

### 3. 파일 크기 제한

- 텍스트 파일 읽기: 기본 최대 1MB
- 큰 파일은 메타데이터만 반환

## 지원 파일 형식

텍스트 파일로 인식되는 확장자:
- `.txt`, `.py`, `.js`, `.ts`, `.tsx`
- `.json`, `.md`, `.yml`, `.yaml`
- `.xml`, `.html`, `.css`
- `.log`, `.csv`, `.ini`, `.cfg`, `.toml`

## 웹 대시보드에서 사용

웹 대시보드나 모바일 앱에서 이 API를 사용하여:

1. **파일 브라우저**: 폴더 구조 탐색
2. **코드 뷰어**: 소스 코드 파일 내용 확인
3. **통계 대시보드**: 폴더 크기 및 파일 수 모니터링
4. **문서 뷰어**: Markdown, README 파일 읽기

## JavaScript 예제

```javascript
// sc2-ai-dashboard 폴더 목록 조회
async function listDashboardFiles(path = '') {
    const response = await fetch(
        `http://localhost:8001/api/files/sc2-ai-dashboard?path=${encodeURIComponent(path)}`
    );
    const data = await response.json();
    return data.items;
}

// 파일 내용 읽기
async function readFile(base, path) {
    const response = await fetch(
        `http://localhost:8001/api/files/content?base=${base}&path=${encodeURIComponent(path)}`
    );
    const data = await response.json();
    return data.content;
}

// 폴더 통계 조회
async function getFolderStats(base, path = '') {
    const response = await fetch(
        `http://localhost:8001/api/files/stats?base=${base}&path=${encodeURIComponent(path)}`
    );
    const data = await response.json();
    return data.statistics;
}
```

## 다음 단계

1. ? `sc2-ai-dashboard` 폴더 통합 완료
2. ? 웹 대시보드 UI에 파일 브라우저 추가 (추후 구현)
3. ? 파일 검색 기능 추가 (추후 구현)
4. ? 파일 다운로드 기능 추가 (추후 구현)

## 참고

- 기존 `local_training` 및 `sc2-mobile-app` API는 그대로 작동합니다
- 모든 API는 동일한 보안 검증을 사용합니다
- 파일 브라우저는 읽기 전용입니다 (수정/삭제 기능 없음)
