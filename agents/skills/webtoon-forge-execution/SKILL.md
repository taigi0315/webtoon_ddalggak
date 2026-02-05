---
name: webtoon-forge-execution
description: Execute and iterate the WebtoonForge project end-to-end from architecture doc to working backend/frontend milestones. Use when implementing or extending the WebtoonForge stack.
---

# WebtoonForge Execution Skill

## When to use
- `webtoon-forge-architecture.md` 기반으로 실제 구현을 진행할 때
- 백엔드(LangGraph/FastAPI)와 프론트엔드(React/Zustand)를 함께 확장할 때
- 작업 마일스톤 추적 문서를 동시에 유지해야 할 때

## Workflow
1. `TASKS.md`를 먼저 만들고 현재 목표를 체크리스트로 정의한다.
2. 백엔드는 아래 순서로 구현한다.
   - 모델/상태 정의
   - 그래프 노드 및 오케스트레이션
   - FastAPI 엔드포인트
   - export/후처리 서비스
3. 프론트엔드는 아래 순서로 구현한다.
   - 타입 정의
   - Zustand store 및 API 연결
   - Studio UI(입력/진행/프리뷰)
4. 큰 마일스톤 완료 시 `TASKS.md` 체크박스와 `Milestone Log`를 즉시 업데이트한다.

## Guardrails
- 구현은 문서 구조를 우선 따르되, 실행 가능 MVP를 먼저 만든다.
- API/타입 계약은 프론트/백엔드에서 동일하게 유지한다.
- placeholder 구현(예: mock image, export manifest)에는 TODO 성격을 코드 주석으로 남긴다.
