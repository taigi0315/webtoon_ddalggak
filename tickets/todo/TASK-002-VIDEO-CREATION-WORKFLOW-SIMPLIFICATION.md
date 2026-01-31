# TASK-002: Video Creation Workflow Simplification

## 상태

- Status: TODO
- Priority: MEDIUM
- Created: 2026-01-31
- Assignee: Frontend Team

## 목표

Video 생성 워크플로우에서 불필요한 "Select Episodes" 단계를 제거하고, Episode를 Story와 동일하게 자동 설정합니다.

## 요구사항

### 현재 문제

사용자가 대화 설정을 완료한 후 비디오를 생성하려고 할 때:

1. "Select Episodes" 화면이 나타남
2. 사용자가 Episode를 별도로 생성해야 함
3. 이 단계가 불필요함 (Episode = Story로 간주되어야 함)

### 해결 방안

- [ ] "Select Episodes" 단계 제거
- [ ] Episode를 Story 이름으로 자동 preset
- [ ] 비디오 생성 버튼 클릭 시 바로 생성 프로세스 시작

## 구현 범위

### Frontend

- [ ] Video 생성 워크플로우 UI 수정
  - Episode 선택 단계 제거
  - Story 이름을 Episode로 자동 사용
- [ ] API 호출 수정
  - Episode ID 대신 Story ID 또는 자동 생성된 Episode ID 사용
  - Episode 선택 없이 비디오 생성 요청

### Backend (필요시)

- [ ] Video 생성 API 엔드포인트 확인
  - Episode 파라미터가 필수인지 확인
  - 필요시 Episode를 자동 생성하도록 수정
  - Story와 Episode 관계 단순화

### 데이터 모델 검토

- [ ] Story와 Episode 관계 검토
- [ ] Episode가 항상 필요한지 확인
- [ ] 1 Story = 1 Episode 자동 매핑 로직 구현

## 테스트 체크리스트

- [ ] 대화 설정 완료 후 "Create Video" 버튼 클릭 시 바로 비디오 생성이 시작되는지 확인
- [ ] Episode 선택 단계가 나타나지 않는지 확인
- [ ] 생성된 비디오가 올바른 Story 내용을 포함하는지 확인
- [ ] 기존 비디오 생성 기능에 문제가 없는지 확인

## 관련 파일

- Frontend:
  - Video 생성 관련 컴포넌트 (예: `frontend/components/VideoCreation.tsx`)
  - Video 생성 워크플로우 페이지
  - `frontend/lib/api/client.ts` (video API 호출)
- Backend:
  - `app/api/v1/video.py` or similar (video generation endpoint)
  - `app/db/models.py` (Story, Episode models)
  - `app/services/video_generator.py`

## UX Flow (개선 후)

```
Story 생성 → Scene 추가 → Dialogue 설정 → [Create Video] → Video 생성 완료
```

**제거되는 단계:**

```
[Select Episodes] → [Create Episode] → ...
```

## 참고사항

- Episode 개념이 완전히 제거되는 것이 아니라, 백그라운드에서 자동 처리됨
- Story와 Episode가 1:1 관계라면 DB 스키마 단순화 고려 가능
- 나중에 다중 Episode 지원이 필요하다면 선택적 기능으로 추가 가능

## Related Tickets

- None

## Notes

- 사용자 경험 단순화가 주 목표
- Episode = Story로 간주하여 불필요한 단계 제거
