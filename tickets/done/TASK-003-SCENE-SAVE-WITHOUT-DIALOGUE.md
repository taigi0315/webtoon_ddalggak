# TASK-003: Scene Save Without Dialogue

## 상태

- Status: ✅ **COMPLETED**
- Priority: MEDIUM
- Created: 2026-01-31
- Completed: 2026-01-31
- Assignee: Backend & Frontend Team

## 목표

"Save Later" 버튼이 대화(Dialogue) 없이도 씬을 저장할 수 있도록 수정합니다.

## 구현 완료 내용

### Backend ✅

- [x] Pydantic Schema 수정
  - `DialogueLayerCreate.bubbles`: `Field(default_factory=list)`로 변경
  - `DialogueLayerUpdate.bubbles`: `Field(default_factory=list)`로 변경
  - 빈 dialogue layer 저장 가능하도록 변경

### Frontend ✅

- [x] Validation 로직 제거
  - `saveLayerMutation`에서 "Add at least one dialogue bubble" 에러 제거
  - 빈 bubbles 배열도 저장 가능하도록 변경
  - "Save Layer" 버튼 활성화 조건 유지 (scene 선택되어 있으면 활성화)

## 구현 세부사항

### 1. Backend Schema Changes

**File**: `app/api/v1/schemas.py`

**Before**:

```python
class DialogueLayerCreate(BaseModel):
    bubbles: list[DialogueBubble] = Field(min_length=1)  # ❌ Required

class DialogueLayerUpdate(BaseModel):
    bubbles: list[DialogueBubble] = Field(min_length=1)  # ❌ Required
```

**After**:

```python
class DialogueLayerCreate(BaseModel):
    bubbles: list[DialogueBubble] = Field(default_factory=list)  # ✅ Optional

class DialogueLayerUpdate(BaseModel):
    bubbles: list[DialogueBubble] = Field(default_factory=list)  # ✅ Optional
```

### 2. Frontend Validation Changes

**File**: `frontend/app/studio/dialogue/page.tsx`

**Before**:

```typescript
const validBubbles = bubbles.filter((bubble) => bubble.text.trim().length > 0);
if (validBubbles.length === 0) {
  throw new Error("Add at least one dialogue bubble before saving."); // ❌ Blocked
}
```

**After**:

```typescript
const validBubbles = bubbles.filter((bubble) => bubble.text.trim().length > 0);
// Allow saving with zero bubbles - dialogue is optional  // ✅ Allowed
```

## 사용 사례

### Now Possible:

1. **배경 전용 씬**: 대화 없이 분위기나 장소만 보여주는 씬
2. **액션 씬**: 대화 없이 액션만 있는 씬
3. **감정 표현 씬**: 캐릭터 표정이나 제스처만으로 표현
4. **몽타주 씬**: 여러 장면을 빠르게 연결하는 씬

## 테스트 체크리스트

- [x] Backend Schema validation 통과
- [x] Frontend validation 제거 확인
- [x] 빈 dialogue layer 저장 가능
- [x] 기존 dialogue 있는 씬도 정상 저장
- [ ] Video 생성 시 빈 dialogue 씬 처리 (이미 구현됨 - `video.py`에서 dialogue 없으면 skip)
- [ ] End-to-end 테스트 필요

## 변경된 파일

- ✅ `app/api/v1/schemas.py` - DialogueLayerCreate, DialogueLayerUpdate
- ✅ `frontend/app/studio/dialogue/page.tsx` - saveLayerMutation validation 제거

## Video Generation 호환성

**Already Supported** ✅

`app/services/video.py`의 `generate_webtoon_video` 함수는 이미 dialogue가 없는 씬을 처리할 수 있습니다:

```python
if scene.dialogues and sequential:
    # Sequential animation logic
    ...
elif scene.dialogues:
    # Non-sequential mode
    ...
else:
    # No dialogues: just show the image  ✅
    abs_path = os.path.abspath(scene.image_path)
    concat_lines.append(f"file '{abs_path}'")
    concat_lines.append(f"duration {scene.duration_seconds:.3f}")
```

## UI/UX 개선사항

- ✅ "Save Layer" 버튼은 scene이 선택되어 있으면 항상 활성화
- ✅ 빈 dialogue도 유효한 저장으로 처리
- ✅ 사용자가 의도적으로 dialogue를 비워둘 수 있음

## 참고사항

- 웹툰/만화에서 대화 없는 컷은 매우 일반적
- Video 생성 시 기본 scene duration 적용 (dialogue가 없으므로 text reading time 없음)
- 이 변경으로 더 다양한 스토리텔링 기법 사용 가능

## Related Tickets

- TASK-001: Chat Bubble Visual Enhancement (Completed)
- TASK-002: Video Creation Workflow Simplification (Completed)

## Notes

간단한 변경이지만 사용자 경험과 창작 자유도를 크게 향상시킵니다!

**웹툰 제작에서 "말없는 순간"도 중요한 스토리텔링 도구입니다.** 🎨
