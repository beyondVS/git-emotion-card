# 구현 계획: [기능]

**브랜치**: `[###-feature-name]` | **날짜**: [DATE] | **사양**: [링크]
**입력**: `/specs/[###-feature-name]/spec.md`의 기능 명세서

**참고**: 이 템플릿은 `/speckit.plan` 명령에 의해 채워집니다. 실행 워크플로우는 `.specify/templates/commands/plan.md`를 참조하십시오.

## 요약

[기능 사양에서 추출: 기본 요구 사항 + 연구를 통한 기술적 접근 방식]

## 기술적 컨텍스트

<!--
  조치 필요: 이 섹션의 내용을 프로젝트의 기술적 세부 정보로 바꾸십시오.
  여기에 제시된 구조는 반복 프로세스를 안내하기 위한 자문 용도로 제공됩니다.
-->

**언어/버전**: [예: Python 3.11, Swift 5.9, Rust 1.75 또는 NEEDS CLARIFICATION]  
**주요 종속성**: [예: FastAPI, UIKit, LLVM 또는 NEEDS CLARIFICATION]  
**저장소**: [해당되는 경우, 예: PostgreSQL, CoreData, 파일 또는 N/A]  
**테스트**: [예: pytest, XCTest, cargo test 또는 NEEDS CLARIFICATION]  
**대상 플랫폼**: [예: Linux 서버, iOS 15+, WASM 또는 NEEDS CLARIFICATION]
**프로젝트 유형**: [단일/웹/모바일 - 소스 구조 결정]  
**성능 목표**: [도메인별, 예: 1000 req/s, 10k lines/sec, 60 fps 또는 NEEDS CLARIFICATION]  
**제약 사항**: [도메인별, 예: <200ms p95, <100MB 메모리, 오프라인 가능 또는 NEEDS CLARIFICATION]  
**규모/범위**: [도메인별, 예: 10k 사용자, 1M LOC, 50 화면 또는 NEEDS CLARIFICATION]

## 헌법 확인

*게이트: 0단계 연구 전에 통과해야 합니다. 1단계 설계 후 다시 확인하십시오.*

[헌법 파일에 따라 결정된 게이트]

## 프로젝트 구조

### 문서 (이 기능)

```text
specs/[###-feature]/
├── plan.md              # 이 파일 (/speckit.plan 명령 출력)
├── research.md          # 0단계 출력 (/speckit.plan 명령)
├── data-model.md        # 1단계 출력 (/speckit.plan 명령)
├── quickstart.md        # 1단계 출력 (/speckit.plan 명령)
├── contracts/           # 1단계 출력 (/speckit.plan 명령)
└── tasks.md             # 2단계 출력 (/speckit.tasks 명령 - /speckit.plan에 의해 생성되지 않음)
```

### 소스 코드 (리포지토리 루트)
<!--
  조치 필요: 아래의 자리 표시자 트리를 이 기능에 대한 구체적인 레이아웃으로 바꾸십시오.
  사용하지 않는 옵션을 삭제하고 선택한 구조를 실제 경로(예: apps/admin, packages/something)로 확장하십시오.
  전달된 계획에는 옵션 라벨이 포함되어서는 안 됩니다.
-->

```text
# [사용하지 않는 경우 제거] 옵션 1: 단일 프로젝트 (기본값)
src/
├── models/
├── services/
├── cli/
└── lib/

tests/
├── contract/
├── integration/
└── unit/

# [사용하지 않는 경우 제거] 옵션 2: 웹 애플리케이션 ("프론트엔드" + "백엔드"가 감지된 경우)
backend/
├── src/
│   ├── models/
│   ├── services/
│   └── api/
└── tests/

frontend/
├── src/
│   ├── components/
│   ├── pages/
│   └── services/
└── tests/

# [사용하지 않는 경우 제거] 옵션 3: 모바일 + API ("iOS/Android"가 감지된 경우)
api/
└── [위의 백엔드와 동일]

ios/ 또는 android/
└── [플랫폼별 구조: 기능 모듈, UI 흐름, 플랫폼 테스트]
```

**구조 결정**: [선택한 구조를 문서화하고 위에 캡처된 실제 디렉토리를 참조하십시오]

## 복잡성 추적

> **헌법 확인에 정당화되어야 하는 위반 사항이 있는 경우에만 작성하십시오**

| 위반 | 필요한 이유 | 더 간단한 대안이 거부된 이유 |
|------|-------------|------------------------------|
| [예: 4번째 프로젝트] | [현재 필요] | [3개 프로젝트가 불충분한 이유] |
| [예: 리포지토리 패턴] | [특정 문제] | [직접 DB 액세스가 불충분한 이유] |
