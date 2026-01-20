# 데이터 모델 (Data Model)

## ERD Overview

### 1. GithubUser
사용자 관리 및 분석 상태 추적 엔티티.

| Field | Type | Attributes | Description |
|---|---|---|---|
| `username` | varchar(150) | PK, Unique | GitHub 사용자 ID |
| `last_analyzed_at` | datetime | Nullable | 마지막 분석 완료 시각 |
| `created_at` | datetime | AutoNowAdd | 최초 생성 시각 |
| `updated_at` | datetime | AutoNow | 정보 갱신 시각 |

### 2. GithubEvent
수집된 원본 이벤트 및 1차 감정 분석 결과.

| Field | Type | Attributes | Description |
|---|---|---|---|
| `id` | varchar(100) | PK | GitHub Event ID (중복 방지) |
| `user` | FK | on_delete=CASCADE | `GithubUser` 참조 |
| `type` | varchar(50) | | 이벤트 타입 (PushEvent 등) |
| `created_at` | datetime | Index | 이벤트 발생 시각 (필터링용) |
| `message` | text | | 추출된 커밋/이슈 메시지 |
| `emotion_result` | jsonb | Nullable | 감정 분석 결과 (Label & Score) |

### 3. AnalysisResult
최종 페르소나 및 카드 데이터.

| Field | Type | Attributes | Description |
|---|---|---|---|
| `id` | bigint | PK, AutoInc | ID |
| `user` | FK | on_delete=CASCADE | `GithubUser` 참조 |
| `persona_keyword` | varchar(50) | | 페르소나 타이틀 |
| `emotion` | varchar(20) | | 분석된 대표 감정 (JOY, ANGER 등) |
| `comment` | varchar(200) | | 한 줄 코멘트 |
| `analyzed_at` | datetime | Index | 분석 완료 시각 |
