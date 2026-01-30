# 구현 계획: 감정 카드 생성 (Generate Emotion Card)

**브랜치**: `001-generate-emotion-card` | **날짜**: 2026-01-22 | **사양**: [spec.md](spec.md)
**입력**: `/specs/001-generate-emotion-card/spec.md`의 기능 명세서

## 요약

GitHub 사용자의 최근 24시간 활동 이벤트를 수집하여 DB(`GithubEvent`)에 저장하고, Gemini(LLM)로 페르소나 및 감정 상태를 분석하여 SVG 카드 형태로 제공하는 API를 구현합니다. "지연 없는 응답"을 위해 Celery/Redis 기반의 비동기 처리와 Stale-While-Revalidate 캐싱 전략을 적용하며, **증분 수집(Incremental Collection)**을 통해 효율성을 극대화합니다.

## 기술적 컨텍스트

**언어/버전**: Python 3.11+ (Django 5.2)

**주요 종속성**:

- **Web**: Django 5.2 (ASGI)
- **Async**: Celery 5.x, Redis
- **LLM**: `google-genai` (Gemini 2.0 Flash Lite Preview)
- **HTTP**: `requests` (GitHub API)
- **Env**: `python-dotenv`

**저장소**: PostgreSQL (User metadata, Event history, Analysis results)
**테스트**: Django Test Framework (`manage.py test`)
**대상 플랫폼**: Docker (Linux Container)
**프로젝트 유형**: Monolithic Web (Django App)
**성능 목표**: API 응답 < 200ms (Cache Hit), 분석 처리 < 30s (Background)
**제약 사항**: GitHub API Rate Limit 준수, LLM 비용 최적화 (24h 이벤트 제한)
**규모/범위**: 단일 Django App (`backend/card`) 추가

## 헌법 확인

*게이트: 0단계 연구 전에 통과해야 합니다. 1단계 설계 후 다시 확인하십시오.*

- [x] **자기 평가**: 분석 로직을 LLM으로 단순화하여 복잡도 감소 (Pragmatism).
- [x] **실용주의**: 로컬 ML 모델 제거 및 외부 LLM 활용으로 유지보수 비용 절감.
- [x] **언어**: 모든 주석 및 커밋 메시지 한국어 작성 준수 예정.
- [x] **기술 스택**: 프로젝트 표준 (Django, Postgres, Celery, Redis) 준수.
- [x] **비용/보안**: PII 마스킹(필요시) 및 입력 데이터 제한(24h)으로 비용/보안 고려.

## 프로젝트 구조

### 문서 (이 기능)

```text
specs/001-generate-emotion-card/
├── plan.md              # 이 파일
├── research.md          # 0단계 출력 (기술 결정)
├── data-model.md        # 1단계 출력 (DB 스키마)
├── quickstart.md        # 1단계 출력 (실행 가이드)
├── contracts/           # 1단계 출력 (API 명세)
│   └── openapi.yaml
└── tasks.md             # 2단계 출력 (작업 목록)
```

### 소스 코드 (리포지토리 루트)

```text
backend/
├── card/                # [New App]
│   ├── __init__.py
│   ├── apps.py
│   ├── models.py        # GithubUser, GithubEvent, AnalysisResult
│   ├── views.py         # Card View (SVG render)
│   ├── tasks.py         # Celery Tasks (Analyze & Incremental Collection)
│   ├── services.py      # GitHub Client, Gemini Client logic
│   ├── urls.py
│   └── tests.py
├── templates/
│   └── card/
│       ├── card.svg     # SVG Template
│       ├── placeholder.svg
│       └── error.svg
└── playground/          # [Existing] Refactor or Deprecate
```

**구조 결정**:
1. 기존 `playground`의 로직을 `backend/card/services.py` 및 `tasks.py`로 이관하여 정식 기능으로 승격합니다.
2. `GithubEvent` 모델을 추가하여 원본 이벤트를 영구 저장하고, 분석 시 증분 수집 및 24시간 필터링을 수행합니다.

## 복잡성 추적

| 위반              | 필요한 이유            | 더 간단한 대안이 거부된 이유             |
|-----------------|-------------------|------------------------------|
| Celery/Redis 도입 | 비동기 분석, 캐싱, Distributed Lock (중복 방지) | 동기 처리 시 사용자 대기 시간 발생 (UX 저하) |
| SVG Template    | 동적 이미지 생성         | Pillow 등은 무겁고 디자인 수정이 어려움    |
| Event DB 저장     | 증분 수집 및 이력 관리      | 매번 전체 API 호출 시 Rate Limit 및 비효율성 발생 |