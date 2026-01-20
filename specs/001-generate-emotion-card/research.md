# 기술 조사 및 결정 사항 (Research & Decisions)

## 1. 비동기 처리 아키텍처
- **결정**: **Celery + Redis + PostgreSQL**
- **근거**:
  - ML 모델 추론(HuggingFace)과 LLM 호출(Gemini)은 수 초 이상 소요되는 Heavy Task로, 웹 요청 주기(Request-Response Cycle) 내에서 처리 불가능.
  - Django Async View만으로는 CPU Bound 작업(ML) 처리 시 이벤트 루프 블로킹 위험이 있음.
  - Celery는 파이썬 생태계의 표준적인 비동기 큐 솔루션으로 안정성이 검증됨.
- **고려된 대안**:
  - **Django Async View + Threading**: 가볍지만, 동시 요청 증가 시 서버 리소스 고갈 및 관리 어려움.
  - **DB Polling**: 구현은 쉽지만 실시간성이 떨어지고 DB 부하 증가.

## 2. 데이터베이스
- **결정**: **PostgreSQL**
- **근거**:
  - Celery 워커와 웹 서버가 동시에 DB에 접근(Write)해야 함.
  - SQLite는 파일 기반으로, 높은 동시성 환경에서 `database is locked` 오류가 빈번함.
  - JSONB 필드를 활용하여 가변적인 ML 분석 결과(`emotion_result`)를 유연하게 저장 가능.

## 3. AI 모델 서빙
- **결정**: **HuggingFace (Local) + Gemini Flash Lite (API)**
- **근거**:
  - **감정 분석**: `xlm-roberta-base-finetuned-kor-8-emotions` 모델은 로컬에서 실행 가능한 크기이며, 한국어 감정 분석에 특화됨. API 호출 비용 절감.
  - **페르소나 생성**: 복잡한 추론과 문장 생성은 로컬 모델보다 거대 LLM(Gemini)이 훨씬 우수함. Flash Lite 모델은 속도와 비용 면에서 MVP에 적합.
