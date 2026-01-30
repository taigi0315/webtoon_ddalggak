# TASK-002: Webtoon Script Writer Node Implementation

## Context

Current system simply splits raw user text into scenes. This fails to capture the "Visual Language" of webtoons, which relies on imagery, dialogue, and SFX rather than long narrative descriptions. We need a dedicated node to "translate" raw stories into professional webtoon scripts.

## Objectives

Implement a `WebtoonScriptWriter` node in the `story_build` graph.

### 1. Script Translation Logic

- [ ] **Narrative to Visuals**: Convert descriptive paragraphs into visual "beats" (Focus on what characters are doing, not what they are thinking).
- [ ] **Dialogue Expansion**: Elaborate on flat dialogue to make it feel more "webtoon-like" (Intense, emotional, or punchy).
- [ ] **SFX Mapping**: Automatically suggest on-screen SFX text (e.g., _THUMP_, _WHOOSH_, _GASP_).
- [ ] **Genre Alignment**: Ensure the script follows the tropes and pacing of the selected "Project Category" (e.g., Romance, Action).

### 2. Integration

- [ ] Insert the node after `ValidateInputs` and before `SceneSplitter`.
- [ ] Output a structured `WebtoonScript` object that `SceneSplitter` can use as the new source of truth.

### 3. Prompting

- [ ] Create `prompt_script_writer.yaml` with specific instructions for visual-first storytelling.
- [ ] Use "Show, Don't Tell" as the primary heuristic for the writer agent.

### 4. Iterative Loop Support

- [ ] **Feedback Integration**: Support receiving "Condense" or "Re-visualize" requests from the Tone Planner/Optimizer.
- [ ] **Review Remediation**: Support receiving "Critical Review Points" from the Blind Test node.
- [ ] **State Preservation**: Ensure the agent can see its previous drafts and the specific reasons for rejection to avoid repeating mistakes.

## Acceptance Criteria

- [ ] Raw user input like "He was angry" is transformed into specific visual actions (e.g., "His fist trembles, eyes narrowing").
- [ ] Generated scenes are based on the _rewritten script_, not the raw input.
- [ ] Script contains hints for SFX and visual atmosphere.
- [ ] The Script Writer successfully adapts the script based on feedback from the Tone Planner or Blind Tester.
