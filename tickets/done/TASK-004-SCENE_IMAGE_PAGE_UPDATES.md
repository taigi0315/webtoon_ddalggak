# TASK-004: Scene Image Page Updates & Optimization

## Context

The user has reported several issues and requested features for the scene image generation workflow. The generation is slow, retries wait too long, previous images aren't shown, and a batch generation feature is missing.

## Objectives

### 1. Optimization & Fine-tuning (Backend)

- **Analyze Slow Generation:** Investigate why scene image generation is taking a long time.
- **Reduce Retry Wait:** Shorten the retry waiting time for failed generations (likely in Gemini client or similar).

### 2. Bug Fixes (Frontend/Backend)

- **Show Previous Images:** ensure previously generated images for a scene are visible and selectable in the UI.

### 3. feature Update (Frontend/Backend)

- **Batch Generation:** Add a "Create All Scene Images" button to trigger generation for all scenes in a story/episode.

## Implementation Plan

### Phase 1: Performance & Config (Backend)

- [x] Analyze `app/services/vertex_gemini.py` or relevant generation service for retry logic and timeouts.
- [x] Reduce retry backoff/wait times.
- [x] Profile or trace generation process to identify bottlenecks (prompts, API calls, latency).

### Phase 2: Frontend Fixes & Features

- [x] Inspect `frontend/app/studio/scenes/page.tsx` (or relevant page) to see how images are loaded.
- [x] Ensure `render_result` artifacts are properly fetched and displayed history.
- [x] Implement "Create All" button.
- [x] Create/Update backend endpoint for batch generation if not exists.

## Acceptance Criteria

- [x] Scene generation retry wait is shorter (better UX).
- [x] Pre-existing images appear in the specific panel/scene UI.
- [x] "Create All" button triggers generation for all scenes.
- [x] Generation speed bottleneck is identified (and improved if possible).
