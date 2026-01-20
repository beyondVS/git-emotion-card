# 구현 계획: Emotion Card 생성 기능

**기능**: `001-generate-emotion-card`
**상태**: 계획 수립됨

## 1. 아키텍처 및 인프라 설계 (@Architect & @DevOps)

### 시스템 아키텍처

본 기능은 긴 대기 시간이 소요되는 AI 분석 작업을 웹 요청과 분리하기 위해 **비동기 작업 큐(Task Queue)** 패턴을 채택합니다.

- **Client**: 브라우저 또는 GitHub 마크다운 렌더러 (`GET /card.svg?username=xxx`)
- **Web Server (Django/ASGI)**:
    - 요청 수신 즉시 DB 조회하여 분석 상태(Cold/Fresh/Stale) 판단.
    - 분석 필요 시 Celery Task 발행 후 즉시 응답(SVG 반환).
- **Message Broker (Redis)**: 비동기 작업 메시지 중개.
- **Worker (Celery)**:
    - 백그라운드에서 GitHub 이벤트 수집, 감정 분석(Local LLM), 페르소나 생성(Gemini) 수행.
    - 결과를 DB(PostgreSQL)에 저장.
- **Database (PostgreSQL)**: 사용자 정보, 이벤트 로그, 분석 결과 저장. (SQLite의 동시성 잠금 문제 해결을 위해 도입)

### Docker Compose 구성 계획

`docker-compose.yml`에 다음 서비스들이 추가/구성되어야 합니다.

1. **`db`**: PostgreSQL 15+ (기존 SQLite 대체 권장)
2. **`redis`**: Redis 7.0+ (Broker & Cache & Lock)
3. **`web`**: Django ASGI 실행 (`uvicorn` or `daphne`)
4. **`worker`**: Celery Worker 프로세스 (`celery -A config worker ...`)

### 필요 종속성 (Dependencies)

`pyproject.toml`에 추가 (`uv add`):

- `celery`: 비동기 작업 관리
- `redis[hiredis]`: Celery Broker 및 Cache Backend
- `psycopg[binary]`: PostgreSQL 드라이버
- `transformers`: HuggingFace 모델 실행
- `torch`: PyTorch (CPU 버전 권장 for MVP)
- `google-genai`: Gemini API 클라이언트
- `uvicorn`: ASGI 서버

---

## 2. 데이터 모델링 (@DataArchitect)

### ERD 설계 (`card` 앱)

**1. `GithubUser`**
분석 대상 사용자 관리 및 락킹을 위한 메인 엔티티.

- `username`: `varchar(150)` (PK) - GitHub 사용자 ID.
- `last_analyzed_at`: `datetime` (Nullable) - 마지막 분석 완료 시각.
- `is_analyzing`: `boolean` - (Application Level Lock 대신 Redis Lock 사용 권장하므로 제외 가능, 혹은 상태 표시용) → *Redis Distributed
  Lock으로 대체하여 DB 부하 감소 결정.*

**2. `GithubEvent`**
GitHub에서 수집된 원본 이벤트 및 1차 감정 분석 결과.

- `id`: `varchar(100)` (PK) - GitHub Event ID.
- `user`: `FK(GithubUser)` - 소유자.
- `type`: `varchar(50)` - 이벤트 타입 (PushEvent 등).
- `created_at`: `datetime` - 이벤트 발생 시각 (인덱스 필요).
- `message`: `text` - 추출된 커밋/이슈 메시지.
- `emotion_result`: `jsonb` - 로컬 모델 감정 분석 결과 (Label & Score).

**3. `AnalysisResult`**
최종 생성된 페르소나 및 카드 데이터.

- `id`: `bigint` (PK).
- `user`: `FK(GithubUser)` - 소유자.
- `persona_keyword`: `varchar(50)` - 짧은 페르소나 타이틀 (예: "분노의 코더").
- `emotion`: `varchar(20)` - 분석된 대표 감정 (JOY, ANGER, ANXIETY, SADNESS, CONFUSION, NEUTRAL).
- `comment`: `varchar(200)` - 한 줄 코멘트.
- `analyzed_at`: `datetime` - 분석 완료 시각 (인덱스 필요).

---

## 3. 상세 작업 목록 (Todo List)

### 인프라 및 설정 (Infra & Config)

- [ ] [Infra] `pyproject.toml`에 필수 패키지(`celery`, `redis[hiredis]`, `psycopg` 등) 추가 및 설치.
- [ ] [Infra] `docker-compose.yml` 작성 (Postgres, Redis, Web, Worker 구성).
- [ ] [Backend] `settings.py`에 Celery Broker/Backend 및 Database(Postgres) 설정.
- [ ] [Backend] 로컬 감정 분석 모델(`xlm-roberta...`) 다운로드 스크립트 또는 캐싱 설정.

### 백엔드 개발 (Backend)

- [ ] [Backend] `card/models.py`에 `GithubUser`, `GithubEvent`, `AnalysisResult` 모델 정의 및 Migration.
- [ ] [Backend] `card/services/github.py`: GitHub API 클라이언트 구현 (이벤트 수집).
- [ ] [Backend] `card/services/emotion.py`: HuggingFace 로컬 모델 로딩 및 추론 로직 구현.
- [ ] [Backend] `card/services/persona.py`: Gemini API 연동 및 프롬프트 제어 로직 구현.
- [ ] [Backend] `card/tasks.py`: Celery Task 구현 (전체 분석 파이프라인 오케스트레이션).
    - Redis Distributed Lock 적용 (중복 실행 방지).
- [ ] [Backend] `card/views.py`: `GET /card.svg` 구현.
    - Cold Miss: "분석 중" SVG 반환 + Task 트리거.
    - Hit & Fresh: DB 결과 SVG 반환.
    - Hit & Stale: DB 결과 SVG 반환 + Task 트리거.

### 프론트엔드/SVG (Frontend)

- [ ] [Frontend] SVG 템플릿 파일 작성 (`templates/card/status_card.svg`, `placeholder.svg`).
    - Django Template Language(DTL) 사용하여 데이터 바인딩.
    - CSS 스타일 인라인 적용.

---

## 4. 엣지 케이스 및 테스트 계획 (@QAEngineer)

### 테스트 전략

- **Unit Test**: 모델 메서드 및 유틸리티 함수 테스트.
- **Integration Test**: 뷰 호출 시 DB 상태 변화 및 Task 트리거 여부 검증. (Celery `task_always_eager` 모드 활용).
- **Mocking**:
    - **GitHub API**: `unittest.mock`을 사용하여 API 호출 비용 및 속도 문제 해결.
    - **LLM/Model**: 무거운 추론 과정을 Mocking하여 로직 흐름 검증에 집중.

### 주요 엣지 케이스 점검

1. **Concurrency (동시성)**:
    - 동일 유저 `newuser`에 대해 0.1초 간격으로 10번 요청 시, Celery Task는 **단 1개**만 생성되어야 함. (Redis Lock 검증)
2. **API Rate Limit**:
    - GitHub API 제한 도달 시, Task는 실패 처리되거나 재시도(Retry) 되어야 하며, 사용자에게는 이전 데이터(Stale) 또는 에러 카드(Fallback)가 보여야 함.
3. **Model Loading Latency**:
    - 워커 프로세스 시작 시 거대한 ML 모델 로딩으로 인한 타임아웃 발생 가능성 점검. (모델 전역 로딩 방식 적용)
4. **Invalid User**:
    - 존재하지 않는 GitHub 유저 요청 시 `404 Not Found` 스타일의 SVG 카드 반환.