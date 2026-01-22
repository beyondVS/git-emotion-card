# Quickstart Guide

## 전제 조건

- Docker & Docker Compose
- `.env` 파일 설정 (GITHUB_TOKEN, GEMINI_API_KEY 필수)

## 실행 방법

1. **컨테이너 실행**
   ```bash
   docker-compose up --build
   ```

2. **데이터베이스 마이그레이션 (최초 1회)**
   자동으로 실행되지만, 수동 실행이 필요한 경우:
   ```bash
   docker-compose exec backend python manage.py migrate
   ```

3. **테스트**
   브라우저 또는 curl로 요청:
   ```bash
   # 로컬 테스트
   curl "http://localhost:8000/card.svg?username=torvalds" > card.svg
   ```

## 개발 가이드

- **코드 수정**: `backend/card/` 디렉토리 내의 파일을 수정하면 `uvicorn`의 reload 기능으로 즉시 반영됩니다 (Celery 워커는 재시작 필요).
- **테스트 실행**:
  ```bash
  docker-compose exec backend python manage.py test card
  ```
