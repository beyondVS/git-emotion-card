# **📄 Github 활동 이벤트 기반 감정 뱃지 서비스 구축 전략 (v3.5)**

## **1\. 프로젝트 개요 (Project Overview)**

* **서비스명:** **Git Emotion Card**
* **핵심 가치:** GitHub 활동 텍스트를 분석하여 개발자의 현재 심리 상태(페르소나)와 하루의 감정 흐름을 시각화.
* **기술 철학:** **LLM-Powered Analysis**
    * LLM(대규모 언어 모델)이 사용자의 최근 24시간 활동 로그 전체를 분석하여, 맥락에 맞는 페르소나와 요약 코멘트를 생성합니다.

## **2\. 감정 분류 체계 (Emotion Classification Standards)**

심리학자 **폴 에크만(Paul Ekman)**의 6가지 기본 감정 이론을 기반으로 개발자의 활동에 맞춰 변형.(혐오는 다른 감정에 포함) \
LLM은 텍스트의 키워드, 문장 부호, 뉘앙스를 분석하여 다음 6가지 상태 중 하나로 분류합니다. (시스템 프롬프트 기준)

| 상태 (Enum)     | 키워드 예시                                         | 뉘앙스 및 해석                                  |
|:--------------|:-----------------------------------------------|:------------------------------------------|
| **JOY**       | `feat`, `release`, `merge`, `solved`, `성공`     | **성취/기쁨**: 도파민 충전, 퇴근 준비 완료, 자신감 넘침       |
| **ANGER**     | `shit`, `fuck`, `stupid`, `blame`, `망할`        | **분노/짜증**: 키보드 샷건 장전, 범인 색출 중, 공격적        |
| **ANXIETY**   | `hotfix`, `urgent`, `critical`, `!`, `제발`      | **불안/다급**: 식은땀, 프로덕션 비상, 느낌표 연타(!!!)      |
| **SADNESS**   | `chore`, `fix`, `revert`, `legacy`, `노가다`      | **피로/우울**: 영혼 가출, 단순 반복 작업, 지루함, 체념       |
| **CONFUSION** | `oops`, `why`, `weird`, `?`, `뭐지`              | **당황/놀람**: "이게 왜 안 되지?", 이해 불가, 귀신이 곡할 노릇 |
| **NEUTRAL**   | `docs`, `refactor`, `style`, `rename`, `clean` | **평온/중립**: 이너 피스, 기계적인 타자, 감정 배제          |
| **IDLE**      | (이벤트 없음)                                       | **잠수/휴식**: 침대와 동기화 중, 현생 로그인              |

## **3\. 페르소나 정의 (System Analyst)**

* **화자:** **AI System Analyst** (시스템 분석가)
* **역할:** 24시간 동안의 Git 이벤트를 분석하여 개발자의 상태를 제3자 관점에서 브리핑.
* **Tone & Manner:**
    * **Witty & Cynical:** 개발자의 애환을 풍자 (예: "카페인으로 혈관 코딩 중").
    * **Dry & Hardware-like:** 하드웨어 비유 사용 (과부하, 재부팅 필요, 동기화 중).
    * **Insightful:** 단순 사실 나열이 아닌, 그 이면의 고통이나 기쁨을 통찰.

## **3\. 시스템 아키텍처 (Architecture)**

\*\*서빙 레이어(조회)\*\*와 \*\*워커 레이어(분석)\*\*를 분리하여, 사용자에게는 지연 없는 응답을 제공하고 분석은 비동기로 처리합니다. 전체 인프라는 **Docker Compose**로 관리됩니다.

### **3.1. 기술 스택 (Tech Stack)**

* **Container:** Docker, Docker Compose
* **Backend:** Python 3.11, Django 5.2, Uvicorn
* **Database:** PostgreSQL 15 (사용자 데이터 및 분석 결과 저장)
* **Cache & Broker:** Redis 7 (작업 큐 및 SVG 캐싱)
* **Worker:** Celery 5

### **3.2. 서빙 레이어 (Serving Layer - Synchronous)**

사용자가 뱃지 이미지(GET /badge/{username})를 요청했을 때의 처리 로직입니다.

1. **Request:** 클라이언트로부터 요청 수신.
2. **Decision Making (Stale-While-Revalidate):**
    * **Case A (Hit & Fresh):** 갱신된 지 **1시간 이내**. → 캐시된 SVG 즉시 반환.
    * **Case B (Hit & Stale):** **1시간 경과**. → 캐시된(오래된) SVG 즉시 반환 \+ **Task 트리거**.
    * **Case C (Miss):** 데이터 없음. → 'Analyzing...' SVG 반환 \+ **Task 트리거**.

### **3.3. 워커 레이어 (Worker Layer - Asynchronous)**

1. **Job Queueing:** `analyze_user_status` 작업 적재.
2. **Collector:** GitHub API 호출 (PushEvent 상세 조회 포함).
3. **Analyzer (LLM):** 전체 맥락 분석 및 페르소나 도출 (Google Gemini).
4. **Renderer:** SVG 렌더링 및 Redis/DB 갱신.

## **4\. 상세 구현 명세 (Collection Targets)**

LLM 분석을 위해 수집해야 할 핵심 이벤트와 텍스트 추출 경로입니다.  
특히 PushEvent는 커밋 메시지 상세 분석을 위해 별도의 API 호출이 필요합니다.

| 이벤트 타입                            | 텍스트 추출 경로 (JSON Path / API Call)                        | 비고             |
|:----------------------------------|:--------------------------------------------------------|:---------------|
| **IssuesEvent**                   | payload.issue.title, payload.issue.body                 | opened, edited |
| **PullRequestEvent**              | payload.pull\_request.title, payload.pull\_request.body | opened, edited |
| **IssueCommentEvent**             | payload.comment.body                                    | \-             |
| **PullRequestReviewCommentEvent** | payload.comment.body                                    | \-             |
| **PullRequestReviewEvent**        | payload.review.body                                     | submitted      |
| **CommitCommentEvent**            | payload.comment.body                                    | \-             |
| **DiscussionsEvent**              | payload.discussion.title, payload.discussion.body       | \-             |
| **DiscussionCommentEvent**        | payload.comment.body                                    | \-             |
| **ReleaseEvent**                  | payload.release.body                                    | \-             |
| **PushEvent**                     | **GET /commits/{sha} → commit.message**                 |                |

## **5\. LLM 프롬프트 전략 (Core Logic)**

* **Role:** 시스템 분석가 (System Analyst).
* **Input:** **최근 24시간 동안 발생한 이벤트 텍스트 로그** (커밋 메시지, 이슈/PR 본문, 코멘트 등).
* **Logic:**
    * **자유로운 해석:** 사전 정의된 감정 분류 없이, LLM이 텍스트의 전체 맥락을 자유롭게 해석하여 창의적인 페르소나와 코멘트를 생성합니다.
    * **안전한 해석:** 기능 추측 지양, 작업의 흐름/강도 해석.
    * **Privacy:** 리포지토리명 마스킹 (System Core, Data Module 등).
* **Output:** JSON (persona\_title, comment).

## **6\. 디자인 명세 (SVG Design)**

* **스타일:** **Modern System Dashboard** (160px Compact).
* **구성:**
    * **Header:** 페르소나 타이틀.
    * **Badge:** 우측 상단, **텍스트 \+ 점멸하는 점(Live Dot)** (배경 박스 없음).
    * **Footer:** 하단 중앙, 이탤릭체 시스템 로그 스타일 코멘트.
* **테마:** Light/Dark 모드 자동 대응.

## **7. 개발 로드맵 (Action Plan)**

### **Phase 1: 인프라 및 수집기 구축 (Infrastructure & Collector)**

* [x] Docker 및 Docker Compose 환경 구성 (PostgreSQL, Redis, Celery).
* [x] Django 및 Uvicorn 서빙 환경 구축.
* [ ] GitHub API Client 구현 (Rate Limit 처리).
* [ ] **PushEvent Detail Fetcher 구현 (비동기 병렬 처리 권장).**

### **Phase 2: 분석 엔진 개발 (Analysis Engine)**

* [ ] LLM System Prompt 최적화 및 테스트 (Few-shot Examples 포함).
* [ ] 리포지토리명 마스킹 로직 구현.

### **Phase 3: 뷰 및 서비스 연동 (View & Serving)**

* [ ] Modern System Dashboard SVG 템플릿(160px) 구현.
* [ ] Django 엔드포인트 (GET /badge/{username}) 구현.
* [ ] Stale-While-Revalidate 로직 적용 (Redis TTL 관리).

### **Phase 4: 최적화 및 배포 (Optimization)**

* [ ] SVG 텍스트 길이 자동 조절(Text Wrapping) 로직 정교화.
* [ ] HTTP Cache-Control 헤더 설정 (GitHub Proxy 캐시 대응).
* [ ] 최종 배포 및 모니터링 연동.