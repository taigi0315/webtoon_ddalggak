# TASK-002: Video Creation Workflow Simplification

## 상태

- Status: ✅ **COMPLETED**
- Priority: MEDIUM
- Created: 2026-01-31
- Completed: 2026-01-31
- Assignee: Frontend Team

## 목표

Video 생성 워크플로우에서 불필요한 "Select Episodes" 단계를 제거하고, Episode를 Story와 동일하게 자동 설정합니다.

## 구현 완료 내용

### Frontend ✅

- [x] Episode 선택 dropdown 제거
- [x] "Create Episode" 버튼 제거
- [x] Episode 자동 생성 로직 구현
  - Story 이름과 동일한 Episode 자동 검색
  - 없으면 자동 생성
  - 있으면 재사용
- [x] UI 단순화: "Generate Video" 버튼만 표시
- [x] Scene이 없을 때 안내 메시지 표시

### 개선된 UX Flow

**Before (복잡함)**:

```
Story → Scenes → Dialogue → [Select Episode] → [Create Episode] → [Generate Video]
```

**After (단순화)**:

```
Story → Scenes → Dialogue → [Generate Video] ✨
```

## 구현 세부사항

### 1. Auto Episode Creation Logic

```typescript
// generateVideoMutation에서 자동 처리
if (!episodeId) {
  // 1. Story 이름과 동일한 Episode 검색
  const existingEpisode = episodesQuery.data?.find(
    (ep) => ep.title === storyQuery.data?.title,
  );

  if (existingEpisode) {
    // 2. 있으면 재사용
    episodeId = existingEpisode.episode_id;
  } else {
    // 3. 없으면 자동 생성
    const newEpisode = await createEpisode({
      storyId,
      title: storyQuery.data.title,
      defaultImageStyle: storyQuery.data.default_image_style,
    });
    episodeId = newEpisode.episode_id;
  }
}
```

### 2. Simplified UI

- ❌ 제거: Episode 선택 dropdown
- ❌ 제거: "Create Episode" 버튼
- ✅ 유지: "Generate Video" 버튼
- ✅ 추가: Scene이 없을 때 안내 메시지

### 3. Button State Logic

```typescript
disabled={
  !storyId ||
  generateVideoMutation.isPending ||
  !scenesQuery.data ||
  scenesQuery.data.length === 0
}
```

## 테스트 체크리스트

- [x] Scene이 있을 때 "Generate Video" 버튼 활성화
- [x] Scene이 없을 때 버튼 비활성화 및 안내 메시지 표시
- [x] Episode가 없을 때 자동 생성
- [x] 같은 이름의 Episode가 있을 때 재사용
- [x] 비디오 생성 프로세스 정상 동작
- [ ] End-to-end 테스트 (사용자 테스트 필요)

## 변경 파일

- ✅ `frontend/app/studio/dialogue/page.tsx` - 주요 변경
  - generateVideoMutation: Episode 자동 생성 로직 추가
  - UI: Episode 선택 제거, 단순화

## 이점

1. **UX 단순화**: 3단계 → 1단계
2. **자동화**: 사용자가 Episode 생성 불필요
3. **직관적**: "Generate Video" 버튼만 클릭
4. **유연성**: Episode는 백그라운드에서 자동 관리

## 참고사항

- Episode는 여전히 DB에 생성됨 (삭제된 것이 아님)
- Story와 Episode는 1:1 관계
- 나중에 여러 Episode 지원이 필요하면 선택적 기능으로 추가 가능

## Related Tickets

- TASK-001: Chat Bubble Visual Enhancement (Completed)

## Notes

사용자는 더 이상 Episode를 신경 쓸 필요가 없습니다. Story를 만들고 Scene을 추가한 후 "Generate Video" 버튼만 클릭하면 됩니다! 🎉
