# TASK-003: Unified Studio Director Node

## Context

Separating Tone Planning and Budget Optimization is inefficient. We need a single "Studio Director" node that makes atomic decisions about scene boundaries, narrative weight, and art style consistency.

## Objectives

Implement the `StudioDirector` node in the `story_build` graph.

### 1. Unified Allocation Logic

- [ ] **Simultaneous Analysis**: Evaluate every narrative beat for both **Weight** (Plot importance) and **Tone** (Art style requirement).
- [ ] **Atomic Scene Splitting**: Create scene boundaries ONLY at tone transition points unless the narrator's beat is too long for a single image.
- [ ] **Budget Balancing**: If the number of detected "style-pure" segments > `max_scenes`:
  - Rank segments by Plot Weight.
  - Merge low-weight segments into adjacent high-weight segments.
  - **Rule**: When merging different tones, the "Project Default" style wins, or the higher-weight tone wins.
- [ ] **Image Style Assignment**: Assign a single `image_style_id` to each finalized scene.

### 2. Feedback Loops

- [ ] **The "Director's Cut"**: If the budget is impossible to meet without breaking style purity, send a `Condense` request back to the `ScriptWriter`.
- [ ] **Critic Integration**: Accept feedback from the `BlindTestRunner` to re-balance the weights if the story flow feels broken.

## Acceptance Criteria

- [ ] A story with 10 gags and 10 serious moments is successfully condensed into 15 scenes without "style bleeding" inside a single 9:16 image.
- [ ] No more "middle of the scene" Chibi hallucinations.
- [ ] The `StudioDirector` produces a clear `allocation_report` artifact explaining why it merged certain beats.
