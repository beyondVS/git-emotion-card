# Quickstart Guide

이 기능(`001-generate-emotion-card`)을 로컬 환경에서 실행하고 테스트하는 방법입니다.

## 전제 조건 (Prerequisites)

- **Docker**: PostgreSQL, Redis 실행을 위해 필요합니다.
- **Python 3.11+**: 프로젝트 런타임.
- **uv**: 패키지 관리자.
- **환경 변수**: `.env` 파일에 다음 설정이 필요합니다.
  - `GITHUB_TOKEN`: GitHub API 토큰 (필수)
  - `GEMINI_API_KEY`: Gemini API 키 (필수)

## 1. 인프라 실행

```bash
# 프로젝트 루트에서
docker-compose up -d db redis
```

## 2. 의존성 설치 및 마이그레이션

```bash
# 의존성 설치
uv sync

# DB 마이그레이션 (GithubUser, AnalysisResult 테이블 생성)
uv run python backend/manage.py makemigrations card
uv run python backend/manage.py migrate
```

## 3. Celery 워커 실행 (터미널 1)

비동기 분석 작업을 처리할 워커를 실행합니다.

```bash
# Windows (pool=solo 권장)
uv run celery -A backend.config worker --loglevel=info --pool=solo

# Linux/Mac
uv run celery -A backend.config worker --loglevel=info
```

## 4. 웹 서버 실행 (터미널 2)

```bash
uv run python backend/manage.py runserver 0.0.0.0:8000
```

## 5. 테스트

브라우저 또는 `curl`을 사용하여 카드를 요청합니다.

```bash
# 1. 최초 요청 (Cold Miss -> Analyzing 카드 반환 + Celery 작업 시작)
curl -v "http://localhost:8000/card.svg?username=your_username"

# 2. Celery 로그 확인
# "Fetching events...", "Gemini Analysis Result..." 등이 출력되어야 함.

# 3. 분석 완료 후 재요청 (Hit -> 결과 카드 반환)
curl -v "http://localhost:8000/card.svg?username=your_username"
```