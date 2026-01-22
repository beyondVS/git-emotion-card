# 구현 작업: 감정 카드 생성 (Generate Emotion Card)

**브랜치**: `001-generate-emotion-card` | **날짜**: 2026-01-22 | **사양**: [spec.md](spec.md)
**입력**: `/specs/001-generate-emotion-card`의 설계 문서

## 종속성 그래프

```mermaid
graph TD
    Start[시작] --> Setup[1단계: 설정]
    Setup --> Base[2단계: 기본 엔티티 및 인프라]
    Base --> US1["3단계: 사용자 스토리 1 (Cold Miss)"]
    US1 --> US2["4단계: 사용자 스토리 2 (Hit & Fresh)"]
    US2 --> US3["5단계: 사용자 스토리 3 (Hit & Stale)"]
    US3 --> Final[최종 단계: 다듬기]
    Final --> End[완료]
```

## 구현 전략

- **MVP 우선**: 핵심 기능인 "분석 요청 → SVG 반환"을 우선 구현합니다.
- **점진적 전달**:
    - `GithubUser` 및 `GithubEvent` 모델 구현.
    - 증분 수집 및 LLM 분석 로직 통합 (US1).
    - 분석 완료 결과 조회 및 실제 카드 렌더링 (US2).
    - 캐싱 전략 및 만료 데이터 갱신 (US3).
- **테스트 주도**: 각 단계마다 핵심 로직에 대한 테스트를 먼저 작성하거나 병행합니다.

## 1단계: 설정 (Setup)

**목표**: 새로운 Django 앱(`card`)을 초기화하고 프로젝트 설정을 구성합니다.

- [x] T001 [Setup] `backend/card` 앱 생성 및 `INSTALLED_APPS` 등록 (앱 폴더 확인 후 등록)
- [x] T002 [Setup] `backend/card/urls.py` 생성 및 프로젝트 `config/urls.py`에 연결
- [x] T003 [Setup] Celery 및 Redis 설정 확인 (`backend/config/settings.py` 점검)

## 2단계: 기본 엔티티 및 인프라 (Foundations)

**목표**: 데이터 모델을 구현하고 DB 마이그레이션을 수행합니다.

- [x] T004 [Base] `backend/card/models.py`에 `GithubUser` 모델 구현
- [x] T005 [Base] `backend/card/models.py`에 `GithubEvent` 모델 구현 (증분 수집용, Event ID PK)
- [x] T006 [Base] `backend/card/models.py`에 `AnalysisResult` 모델 구현
- [x] T007 [Base] `backend/card/admin.py`에 모델 등록
- [x] T008 [Base] 데이터베이스 마이그레이션 생성 및 적용 (`makemigrations`, `migrate`)

## 3단계: 사용자 스토리 1 - 최초 사용자 카드 조회 (Cold Miss)

**목표**: 데이터가 없는 사용자가 요청 시 "분석 중" SVG를 반환하고, 백그라운드에서 이벤트를 수집/분석합니다.

**독립적 테스트**:
- `GET /card.svg?username=newuser` 요청 시 200 OK 및 Placeholder SVG 반환.
- Celery 태스크 실행 시 `GithubEvent`가 DB에 저장되고 분석 결과가 생성되는지 확인.

- [x] T009 [US1] `backend/templates/card/placeholder.svg` 생성 (분석 중 이미지)
- [x] T010 [US1] `backend/card/views.py`에 `CardView` 기본 로직 구현 (Cold Miss 감지 및 Placeholder 반환)
- [x] T011 [P] [US1] `backend/card/services.py`에 `GitHubClient` 구현 (이벤트 ID 파싱 포함)
- [x] T012 [P] [US1] `backend/card/services.py`에 `GeminiClient` 구현 (프롬프트 관리 포함)
- [x] T013 [US1] `backend/card/tasks.py`에 `analyze_user_task` 구현 (GitHub 이벤트 증분 수집 -> DB 저장 -> 최근 24시간 조회 -> Gemini 분석 -> 결과 저장)
- [x] T014 [US1] `backend/card/views.py`에서 Cold Miss 시 `analyze_user_task` 호출 연결

## 4단계: 사용자 스토리 2 - 분석 완료 후 카드 조회 (Hit & Fresh)

**목표**: 분석이 완료된 사용자에 대해 실제 결과가 반영된 SVG 카드를 반환합니다.

- [x] T015 [US2] `backend/templates/card/card.svg` 생성 (데이터 바인딩용 템플릿)
- [x] T016 [US2] `backend/card/views.py`에 분석 완료(`AnalysisResult` 존재) 시 실제 카드 렌더링 로직 추가
- [x] T017 [US2] `backend/card/views.py`에 `Cache-Control` 헤더 설정 적용

## 5단계: 사용자 스토리 3 - 만료된 데이터 조회 및 백그라운드 갱신 (Hit & Stale)

**목표**: 데이터가 만료(1시간 경과)된 경우, 기존 카드를 즉시 반환하고 백그라운드에서 재분석을 수행합니다.

- [x] T018 [US3] `backend/card/views.py`에 Stale 데이터 감지 및 재분석 트리거 로직 추가 (`Stale-While-Revalidate`)
- [x] T019 [US3] `backend/card/tasks.py`에 Redis Distributed Lock 구현 (중복 실행 방지)

## 최종 단계: 다듬기 및 교차 관심사

**목표**: 에러 처리, 코드 정리 및 최종 점검.

- [x] T020 [Final] `backend/templates/card/error.svg` 생성
- [x] T021 [Final] `backend/card/views.py`에 예외 처리 및 Fallback SVG 적용
- [x] T022 [Final] `backend/card/tests.py`에 통합 테스트 작성 (Cold/Fresh/Stale 시나리오, 응답 시간, 증분 수집 검증)