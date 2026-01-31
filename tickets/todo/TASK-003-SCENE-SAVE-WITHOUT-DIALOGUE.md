# TASK-003: Scene Save Without Dialogue

## 상태

- Status: TODO
- Priority: MEDIUM
- Created: 2026-01-31
- Assignee: Backend & Frontend Team

## 목표

"Save Later" 버튼이 대화(Dialogue) 없이도 씬을 저장할 수 있도록 수정합니다.

## 요구사항

### 현재 문제

- "Save Later" 버튼이 dialogue가 있어야만 제출 가능
- 대화가 없는 씬(예: 배경만 있는 씬, 액션 씬 등)을 저장할 수 없음

### 해결 방안

- [ ] Dialogue를 선택적(optional) 필드로 변경
- [ ] Dialogue 없이도 씬 저장 가능하도록 validation 수정
- [ ] UI에서 "Save Later" 버튼 활성화 조건 변경

## 구현 범위

### Backend

- [ ] Scene 저장 API 엔드포인트 수정
  - Dialogue 필드를 optional로 변경
  - Validation 로직 업데이트 (dialogue 없이도 저장 가능)
- [ ] Pydantic Schema 수정
  - `SceneCreate`, `SceneUpdate` 스키마에서 dialogue를 optional로 설정
  - 예: `dialogue: Optional[List[DialogueItem]] = []`
- [ ] Database Model 확인
  - Scene과 Dialogue 관계 확인 (1:N 관계일 것으로 예상)
  - Dialogue가 없는 씬도 유효하도록 constraint 확인

### Frontend

- [ ] "Save Later" 버튼 활성화 조건 수정
  - 현재: Dialogue가 있을 때만 활성화
  - 변경: 씬이 유효하면 항상 활성화 (이미지 필수, dialogue 선택사항)
- [ ] Validation 메시지 업데이트
  - Dialogue 없음 경고 제거 또는 선택사항으로 변경
- [ ] TypeScript Types 업데이트
  - `frontend/lib/api/types.ts`에서 dialogue를 optional로 변경

### Validation 규칙 (개선 후)

**필수 항목:**

- Scene image (배경 이미지)
- Scene metadata (scene_number, etc.)

**선택 항목:**

- Dialogue
- Narration
- SFX

## 테스트 체크리스트

- [ ] Dialogue 없이 씬을 저장할 수 있는지 확인
- [ ] Dialogue 없는 씬이 데이터베이스에 정상 저장되는지 확인
- [ ] Dialogue 있는 씬도 기존처럼 정상 저장되는지 확인
- [ ] "Save Later" 버튼이 적절한 조건에서 활성화되는지 확인
- [ ] 저장된 씬을 불러올 때 Dialogue가 없어도 정상 로드되는지 확인
- [ ] 비디오 생성 시 Dialogue 없는 씬도 정상 처리되는지 확인

## 관련 파일

- Backend:
  - `app/api/v1/schemas.py` (SceneCreate, SceneUpdate)
  - `app/api/v1/scenes.py` or similar (scene CRUD endpoints)
  - `app/db/models.py` (Scene, Dialogue models)
  - `app/services/scene_service.py` (if exists)
- Frontend:
  - Scene editor component (예: `frontend/components/SceneEditor.tsx`)
  - `frontend/lib/api/types.ts`
  - `frontend/lib/api/client.ts` or `queries.ts`

## 데이터 모델 예시

### Before (Dialogue 필수)

```python
class SceneCreate(BaseModel):
    scene_number: int
    image_url: str
    dialogues: List[DialogueItem]  # Required
```

### After (Dialogue 선택사항)

```python
class SceneCreate(BaseModel):
    scene_number: int
    image_url: str
    dialogues: Optional[List[DialogueItem]] = []  # Optional
```

## UI/UX 고려사항

- Dialogue 없는 씬도 유효한 사용 사례임을 명확히 함
- 사용자가 의도적으로 Dialogue를 비워둘 수 있음
- 저장 전 확인 메시지 (선택사항): "이 씬에는 대화가 없습니다. 저장하시겠습니까?"

## 참고사항

- 웹툰에서 대화 없는 씬은 흔함 (배경 컷, 액션 씬, 감정 표현 등)
- Video 생성 로직에서 dialogue 없는 씬을 적절히 처리해야 함 (stay time 기본값 적용 등)

## Related Tickets

- TASK-001 (Chat bubble animation의 stay time 계산과 연관 가능)

## Notes

- Dialogue를 선택사항으로 만드는 간단한 변경이지만 여러 레이어에 영향을 줌
- Backend validation, Frontend validation, TypeScript types 모두 일관성 있게 수정 필요
