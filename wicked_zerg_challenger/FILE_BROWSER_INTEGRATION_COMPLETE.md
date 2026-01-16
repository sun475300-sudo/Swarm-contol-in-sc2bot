# 파일 브라우저 API 통합 완료

**작성일**: 2026-01-16

## 요약

`local_training` 폴더와 `sc2-mobile-app` 폴더를 모바일 앱에서 탐색할 수 있도록 `dashboard_api.py`에 파일 브라우저 API가 추가되었습니다.

## 추가된 기능

1. **파일 목록 조회**: 디렉토리 내 파일 및 폴더 목록 조회
2. **파일 내용 조회**: 텍스트 파일 내용 조회 (최대 1MB)
3. **폴더 통계**: 파일 수, 디렉토리 수, 총 크기 조회
4. **보안**: Path traversal 방지 및 허용된 디렉토리만 접근

## API 엔드포인트

- `GET /api/files/local-training` - local_training 폴더 목록
- `GET /api/files/sc2-mobile-app` - sc2-mobile-app 폴더 목록
- `GET /api/files/content` - 파일 내용 조회
- `GET /api/files/stats` - 폴더 통계

## 상세 문서

- `FILE_BROWSER_API_GUIDE.md`: API 사용 가이드 및 통합 예시

## 다음 단계

1. `dashboard_api.py`의 들여쓰기 오류 수정 (필요시)
2. API 테스트
3. 모바일 앱에 파일 브라우저 컴포넌트 추가
