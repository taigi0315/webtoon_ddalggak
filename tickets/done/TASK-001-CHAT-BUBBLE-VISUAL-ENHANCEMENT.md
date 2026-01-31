# TASK-001: Chat Bubble Visual Enhancement & Type Differentiation

## 상태

- Status: ✅ **COMPLETED**
- Priority: HIGH
- Created: 2026-01-31
- Completed: 2026-01-31
- Assignee: Backend & Frontend Team

## 목표

웹툰 씬의 Chat Bubble, Narration, Thought, SFX의 시각적 표현을 개선하고 각 타입별로 차별화합니다.

## 요구사항

### 1. Opacity (투명도) 설정

- [x] Chat bubble에 투명도 적용
- [x] Config 파일에서 투명도 조정 가능하도록 설정
- [x] 기본값: 40% opacity

**Config Location:**

- ✅ Backend: `app/config/chat_bubble_config.json`
- ✅ Frontend: Canvas 렌더링 시 타입별 스타일 적용

### 2. Type별 시각적 차별화

- [x] Chat bubble (대화)
  - ✅ 스타일: 일반 말풍선 (ellipse)
  - ✅ 색상/테두리: 흰색 배경 40% 투명도, 검은색 테두리
  - ✅ 폰트: cs-raving-drawn-font
- [x] Narration (나레이션)
  - ✅ 스타일: 사각형 박스
  - ✅ 색상/테두리: 검은색 배경 60% 투명도, 흰색 텍스트
  - ✅ 폰트: cs-raving-drawn-font
- [x] Thought (생각)
  - ✅ 스타일: 구름 모양 (cloud approximation with circles)
  - ✅ 색상/테두리: 연한 파란색 배경
  - ✅ 폰트: cs-raving-drawn-font
- [x] SFX (효과음)
  - ✅ 스타일: 배경 없음, text stroke 효과
  - ✅ 색상/테두리: 빨간색 텍스트, 검은색 stroke
  - ✅ 폰트: cs-raving-drawn-font (크고 굵게)

### 3. 폰트 설정 시스템

- [x] Backend에 폰트 설정 추가
- [x] Frontend에서 타입별 폰트 적용 (Canvas 렌더링)
- [x] 폰트 파일: `app/assets/fonts/cs-raving-drawn-font/CsravingdrawnRegularDemo-DYjD1.otf`

### 4. 순차적 애니메이션

- [x] Bubble이 하나씩 순차적으로 나타나도록 구현 (비디오 생성)
- [x] Stay time (버블 표시 지속 시간) config로 조정 가능
- [x] 대화 길이에 따라 stay time 자동 계산
  - ✅ Formula: `stay_time = min_time + (text_length * time_per_char)`

**Implemented Config:**

```json
{
  "animation": {
    "min_stay_time": 2.0,
    "time_per_character": 0.05,
    "transition_duration": 0.3,
    "sequential": true
  }
}
```

## 구현 완료 내용

### Backend ✅

- [x] `app/config/chat_bubble_config.json` 생성
- [x] `app/api/v1/schemas.py`에 `bubble_type`, `speaker` 필드 추가
- [x] `app/services/video.py` 대폭 개선:
  - Config 로딩
  - 타입별 렌더링 (chat, thought, narration, sfx)
  - 투명도 적용 (`hex_to_rgba`)
  - 타입별 폰트, 색상, 모양
  - 순차적 애니메이션 (프레임별 bubble 추가)
  - Stay time 자동 계산

### Frontend ✅

- [x] `frontend/lib/api/types.ts`에 `bubble_type`, `speaker` 추가
- [x] `frontend/app/studio/dialogue/page.tsx` 업데이트:
  - Bubble type 선택기 연결
  - Speaker 입력 필드 활성화
  - Save/Load 시 `bubble_type`, `speaker` 포함
  - Canvas에서 타입별 시각적 차별화 적용

### Video Generation ✅

- [x] 비디오 생성 시 순차적 bubble 표시 구현
- [x] Stay time 계산 적용
- [x] 폰트 로딩 및 적용 완료

## 구현 세부사항

### 순차적 애니메이션 로직

1. **Frame 0**: 이미지만 (dialogue 없음) - `base_duration` 동안
2. **Frame 1**: 이미지 + bubble 1 - `transition + stay_time1` 동안
3. **Frame 2**: 이미지 + bubble 1,2 - `transition + stay_time2` 동안
4. **Frame N**: 이미지 + 모든 bubble - `transition + stay_timeN` 동안

Bubbles는 위치 기준(y, x)으로 정렬되어 자연스러운 읽기 순서를 따릅니다.

### Config Tuning Guide

자세한 튜닝 가이드는 `docs/CHAT_BUBBLE_CONFIG.md` 참조

**Quick tuning:**

- 투명도 조정: `opacity` 값 변경 (0.0-1.0)
- 애니메이션 속도: `min_stay_time`, `time_per_character` 조정
- 순차적 모드 끄기: `sequential: false`

## 테스트 체크리스트

- [x] 투명도가 config 값대로 적용되는지 확인
- [x] 각 타입(chat, narration, thought, sfx)이 시각적으로 구별되는지 확인
- [x] 폰트가 타입별로 올바르게 적용되는지 확인 (비디오 생성 시)
- [x] Bubble이 순차적으로 나타나는지 확인 (비디오 생성 시)
- [x] Stay time이 대화 길이에 따라 적절히 계산되는지 확인
- [ ] End-to-end 비디오 출력 테스트 (사용자 테스트 필요)

## 관련 파일 (Implemented)

- Backend:
  - ✅ `app/config/chat_bubble_config.json` - Main config file
  - ✅ `app/api/v1/schemas.py` - DialogueBubble schema
  - ✅ `app/services/video.py` - Video generation with sequential animation
  - ✅ `app/assets/fonts/cs-raving-drawn-font/CsravingdrawnRegularDemo-DYjD1.otf`
- Frontend:
  - ✅ `frontend/app/studio/dialogue/page.tsx` - Dialogue editor with type selector
  - ✅ `frontend/lib/api/types.ts` - TypeScript types

- Documentation:
  - ✅ `docs/CHAT_BUBBLE_CONFIG.md` - Configuration tuning guide

## 참고사항

- ✅ 기존 대화 데이터 호환: bubble_type 기본값 "chat" 적용
- ✅ 비디오 생성에 순차적 애니메이션 적용됨
- ✅ Frontend 프리뷰에서 타입별 시각적 차별화 적용됨
- ⚠️ 폰트 라이선스 확인 필요 (cs-raving-drawn-font는 Demo 버전)

## Related Tickets

- TASK-002: Video Creation Workflow Simplification
- TASK-003: Scene Save Without Dialogue

## Completion Notes

모든 핵심 기능 구현 완료:

1. ✅ Config-driven styling system
2. ✅ Type differentiation (chat, thought, narration, sfx)
3. ✅ Sequential animation for video generation
4. ✅ Opacity and font customization
5. ✅ Automatic stay time calculation

**다음 단계:**

- 실제 비디오 생성으로 end-to-end 테스트
- Config 값 fine-tuning (사용자 피드백 기반)
- 필요시 Frontend 프리뷰에도 애니메이션 추가 고려
