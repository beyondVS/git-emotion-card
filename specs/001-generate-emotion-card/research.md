# 연구 및 결정 사항

**기능**: Generate Emotion Card
**상태**: 완료

## 결정 1: SVG 생성 전략

- **질문**: 동적인 SVG 카드를 어떻게 생성할 것인가?
- **결정**: Django Template Engine을 사용하여 `.svg` 파일을 렌더링한다.
- **근거**:
  - SVG는 근본적으로 XML 텍스트이므로, Django의 강력한 템플릿 상속 및 변수 치환 기능을 그대로 사용할 수 있다.
  - 별도의 이미지 처리 라이브러리(Pillow, Cairo 등)를 설치할 필요가 없어 가볍다.
  - 프론트엔드 지식(CSS/HTML)을 활용하여 디자인을 쉽게 수정할 수 있다.
- **대안**:
  - **Pillow/OpenCV**: 래스터 이미지(PNG/JPG) 생성에 적합하며 SVG 생성에는 부적합.
  - **Matplotlib**: 데이터 시각화에는 좋으나, 디자인된 카드 제작에는 오버헤드가 큼.

## 결정 2: GitHub API 클라이언트

- **질문**: GitHub API 통신을 위해 어떤 라이브러리를 사용할 것인가?
- **결정**: 기존 `backend/playground/emotion_analysis.py`에 구현된 커스텀 `GitHubClient` (requests 기반)를 리팩토링하여 사용한다.
- **근거**:
  - **Minimal Change**: 이미 작동하는 코드가 존재함.
  - **Dependency**: `PyGithub` 등 무거운 라이브러리를 추가할 필요가 없음.
  - **Control**: 필요한 엔드포인트(User Events, Commit Message)만 명확하게 제어 가능.
- **대안**:
  - **PyGithub**: 기능은 강력하지만 프로젝트 범위(단순 이벤트 수집)에 비해 무거움.

## 결정 3: 비동기 작업 처리 (Celery)

- **질문**: 분석 요청의 비동기 처리를 어떻게 구성할 것인가?
- **결정**: Django + Celery + Redis 조합을 사용한다.
- **근거**:
  - 프로젝트 헌법의 표준 스택임.
  - "Stale-While-Revalidate" 패턴 구현 시, 백그라운드 갱신 작업을 안정적으로 큐에 넣고 관리하기에 최적.
  - 분산 락(Distributed Lock) 구현에 Redis를 활용하기 용이함.

## 결정 4: LLM 클라이언트

- **질문**: Gemini 연동을 위한 라이브러리는?
- **결정**: `google-genai` (최신 SDK)를 사용한다.
- **근거**:
  - `playground` 코드에서 이미 사용 중.
  - Gemini Flash Lite 모델을 지원.
- **주의**: 로컬 ML 모델(`transformers`) 의존성은 제거해야 함 (사양 변경 사항).