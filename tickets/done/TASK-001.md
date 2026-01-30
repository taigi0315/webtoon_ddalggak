# TASK-001: Intelligent Scene Count Recommendation

**Type:** Feature / AI Logic
**Priority:** High
**Status:** Open
**Created:** 2026-01-29

## Description

Implement an AI-powered feature to recommend the optimal number of scenes for a story, targeting a webtoon video duration of 60-90 seconds (approx. 80s ideal).

## Requirements

### 1. Backend Logic

- **Endpoint:** `POST /v1/stories/{id}/estimate-scenes`
- **Input:** Story text (or simply story ID to fetch text).
- **Target Logic:**
  - **Ideal Range:** 7 to 15 scenes (for ~80s video).
  - **Heuristics:**
    - If story is very short (< 5 scenes effectively) -> Suggest min (e.g. 5) but include warning "Too short".
    - If story is very long (> 15 scenes effectively) -> Suggest max (e.g. 15) but include warning "Too long, consider splitting".
    - If within range -> Suggest calculated optimal count (e.g. 8, 12).
- **AI Model Role:**
  - Analyze story density and pacing.
  - Provide specific feedback message explaining the recommendation.
- **Output:**
  - `recommended_count`: int
  - `status`: "ok" | "too_short" | "too_long"
  - `message`: User-friendly explanation (e.g., "Based on your story length, 8 scenes will result in a ~80s video.").

### 2. Frontend UI

- **Location:** Scene count input area (Scene Generation step).
- **Component:**
  - Button label: "Recommend number of scenes".
  - Icon: AI/Magic wand icon.
- **Interaction:**
  - User clicks button.
  - Frontend calls backend.
  - Input field updates with `recommended_count`.
  - Feedback message appears below input:
    - Green text for "ok".
    - Yellow/Red text for "too_short" or "too_long".
    - Allow user to Override the suggestion.

## Implementation Plan

1.  **Prompt Engineering:**
    - Create `app/prompts/v1/story_build/scene_estimation.yaml`.
    - Prompt should instruct model on video duration targets (10-15s per scene average).
2.  **Backend Service:**
    - Add estimation logic to `app/services/story_analysis.py` (or similar).
    - Expose via API endpoint.
3.  **Frontend Update:**
    - Add button and handler to Scene Generation form.

## Acceptance Criteria

- Clicking "Recommend" fetches a valid integer.
- Short stories trigger "Too short" warning.
- Long stories trigger "Too long" warning.
- Logic consistently targets the 7-15 scene sweet spot for standard length stories.
