# Quickstart: Emotion Card Feature

## 사전 준비 (Prerequisites)
1. **Docker Desktop** 실행 중이어야 함.
2. **PostgreSQL Client** (선택 사항).
3. **HuggingFace & Gemini API Key** (`.env` 설정).

## 실행 방법

### 1. 인프라 실행 (Docker)
```bash
docker-compose up -d db redis
```

### 2. 가상환경 및 패키지 설치
```bash
uv sync
```

### 3. 마이그레이션
```bash
python manage.py migrate
```

### 4. 워커 실행 (별도 터미널)
```bash
celery -A config worker --loglevel=info
```

### 5. 웹 서버 실행
```bash
python manage.py runserver
```

## 테스트
브라우저에서 `http://localhost:8000/card.svg?username=myuser` 접속.
