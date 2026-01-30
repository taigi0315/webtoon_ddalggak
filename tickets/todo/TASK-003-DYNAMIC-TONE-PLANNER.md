# TASK-003: Dynamic Tone Planner & Iterative Scene Optimizer

## Context

Standard scene splitting is too mechanical. We need an agentic process to handle art style shifts (like "Chibi Gags") and budget constraints (`max_scenes`) intelligently using importance-based weighting.

## Objectives

Implement an iterative loop between `ToneAuditor` and `SceneOptimizer`.

### 1. Tone & Weight Analysis

- [ ] **Tone Detection**: Scan the script for shifts in mood (e.g., Serious -> Gag, Romance -> Action).
- [ ] **Importance Weighting**: Assign a weight (0.0 to 1.0) to each narrative beat.
  - High weight: Essential plot points, emotional peaks.
  - Low weight: Transitional running, minor atmosphere, repeat transitions.

### 2. Iterative Scene Optimization ("Force Combining")

- [ ] **Budget Constraint**: Compare required scenes (based on tone shifts) vs. `max_scenes` budget.
- [ ] **Intelligent Merge**: If over budget, combine low-weight beats into neighboring high-weight scenes.
- [ ] **Style Anchor Assignment**: Assign a specific `image_style_id` to each scene record based on the dominant tone.

### 3. Agentic Feedback Loop

- [ ] **Script Optimizer Loop**: Implement a LangGraph edge where the `Optimizer` can ask the `ScriptWriter` to "Summarize or skip" lower-weight beats to meet the budget while preserving core story beats.
- [ ] **Blind Test Integration**: Connect the `BlindTestRunner` to the planning phase. If a blind test fails, the `Optimizer` analyzes the failure and sends corrective instructions back to the `ScriptWriter`.

### 4. Style-Variant Support

- [ ] Connect the output to the Casting system to ensure that a "Chibi" scene uses a "Chibi Reference Image" to prevent hallucinations.

## Acceptance Criteria

- [ ] The system can successfully merge 19 "tone-pure" beats into 15 scenes by sacrificing lower-weight moments.
- [ ] Scenes with different styles (Romantic vs. Gag) are physically separated into different generation jobs.
- [ ] Transitions between styles feel intentional and "directed."
- [ ] The "Critic Loop" (Blind Test) successfully identifies narrative gaps caused by scene merging and triggers a re-scripting.
