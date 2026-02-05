# TASK-001: Webtoon Research Architecture Alignment Overhaul

## Goal Summary
Transform the GossipToon story generation system into a research-aligned engine that applies webtoon-specific narrative principles (Closure, Transition Taxonomy, Vertical Rhythm, Dialogue Minimalism) instead of generic cinematic/animation logic.

## Assumptions
- Existing LangGraph structure (`StoryBuildGraph`) is stable enough to add new nodes.
- Pydantic v2 is used for all schema definitions.
- LLM models (GPT-4o/Claude 3.5 Sonnet) can handle the increased complexity of specific taxonomy classifications.

## Scope Summary
- **In Scope**:
    - Creation of 8+ new LangGraph nodes (`TransitionTypeClassifier`, `ClosurePlanningNode`, `VerticalRhythmPlanner`, etc.).
    - Schema updates for `StoryBuildState` and related artifacts.
    - Implementation of research-based heuristic rules for layout and text constraints.
    - Enhanced evaluation and QC nodes.
- **Out of Scope**:
    - External UI development.
    - Image generation model retraining.
- **Definition of Done**: 
    - The enhanced graph successfully processes a story from start to finish.
    - Generated `panel_plan` contains new metadata (`transition_type`, `vertical_rhythm`, `metaphor`).
    - QC checks pass the "25% text rule" and "one action per panel" rule.

## Phases & Checklist

### Phase 1: Core Narrative Grammar (Foundational Nodes)
- [ ] **Task 1.1: Create TransitionTypeClassifier Node**
    - [ ] Define `TransitionType` Enum (6 types: Moment-to-moment, Action-to-action, etc.).
    - [ ] Implement node in `app/graphs/nodes/planning.py`.
    - [ ] Design LLM prompt to classify panel-to-panel transitions.
    - [ ] Add `transition_map` artifact to the graph state.
- [ ] **Task 1.2: Create ClosurePlanningNode**
    - [ ] Define `ClosurePlan` schema (spatial/temporal/causal inference).
    - [ ] Implement heuristic rules for intermediate panel injection (Inference Difficulty > 0.8).
    - [ ] Integrate between script writer and scene optimizer.
- [ ] **Task 1.3: Enhance webtoon_script_writer with Beat Classification**
    - [ ] Update `Beat` schema to include `beat_type`, `emotional_intensity`, `action_complexity`.
    - [ ] Implement "One Action per Panel" validation in the script writer.

### Phase 2: Vertical Rhythm & Pacing System
- [ ] **Task 2.1: Create VerticalRhythmPlanner Node**
    - [ ] Map pixel distances (px) to dramatic weight based on `emotional_intensity` and `transition_type`.
    - [ ] Define `RhythmEntry` schema.
- [ ] **Task 2.2: Implement Panel Width Hierarchy**
    - [ ] Add rules for 100% (Impact), 80% (Standard), 50-60% (Intimate) widths.
    - [ ] Update `rule_layout` node to ingest hierarchy constraints.

### Phase 3: Dialogue Minimalism Engine
- [ ] **Task 3.1: Create DialogueMinimizer Node**
    - [ ] Enforce "25% text rule" (< 25 words per panel).
    - [ ] Split panels if bubbles > 2.
    - [ ] Implement "Show, Don't Tell" prompt logic (convert adverbs to visual cues).
- [ ] **Task 3.2: Create SilentPanelClassifier**
    - [ ] Identify Action, Continuity, or Reaction panels that should be wordless.
    - [ ] Add `is_silent` flag to `panel_plan`.

### Phase 4: Visual Metaphor System
- [ ] **Task 4.1: Create Visual Metaphor Lexicon Database**
    - [ ] Implement as a JSON/Postgres registry mapping emotions to symbols (Plewds, flame eyes, etc.).
- [ ] **Task 4.2: Create MetaphorRecommender Node**
    - [ ] Use Lexicon to suggest background treatments and character modifications.
    - [ ] Add `metaphor_direction` to `panel_semantics`.

### Phase 5: Enhanced Scene Planning
- [ ] **Task 5.1: Enhance llm_scene_intent with Narrative Arc Mapping**
    - [ ] Add `narrative_arc` and `character_presence_map` to `scene_intent`.
- [ ] **Task 5.2: Create CharacterPresenceOptimizer Node**
    - [ ] Decide "Shown" vs "Implied" (Shadow, Hand, Voice-only) for each character.

### Phase 6: Episode-Level Improvements
- [ ] **Task 6.1: Genre-Aware Panel Count Constraints**
    - [ ] Set target panel counts based on genre (Action: 60-70, Romance: 40-50, etc.).
- [ ] **Task 6.2: Cliffhanger Enhancement**
    - [ ] Implement `cliffhanger_spec` validation at episode end.

### Phase 7: Quality and Validation (QC)
- [ ] **Task 7.1: Enhance qc_check with Hard Rules**
    - [ ] Add failure conditions for word count, multi-action, and layout monotony.
- [ ] **Task 7.2: Enhance blind_test_critic with Emotional Delivery Check**
    - [ ] Measure "Emotional Gap" between intended and conveyed feelings.

### Phase 8: Final Integration & Refactoring
- [ ] **Task 8.1: Reconstruct StoryBuildGraph**
    - [ ] Connect all new nodes according to the proposed Mermaid diagram.
    - [ ] Implement feedback loops (e.g., Fail QC -> return to DialogueMinimizer).
- [ ] **Task 8.2: Integration Testing**
    - [ ] End-to-end run with sample stories to verify research alignment.

## Dependencies & Ordering
1. **Core Foundation**: Phase 1 & 3 are necessary before Phase 2 & 5.
2. **Logic Sequence**: `TransitionTypeClassifier` (Ph 1) -> `VerticalRhythmPlanner` (Ph 2).
3. **Validation**: QC (Ph 7) must be updated last to validate all new features.

## Skill / Tool Annotation
- **Backend / LangGraph**: High expertise in `langgraph` nodes and state management.
- **Prompt Engineering**: Highly specialized prompts for webtoon taxonomy.
- **Pydantic**: Schema management for complex artifacts.
