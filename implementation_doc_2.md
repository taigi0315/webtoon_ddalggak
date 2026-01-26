Perfect. Below is a **clear, handoff-ready implementation plan for Phase 2**, written as a continuation of your Technical Design Document. This is **not brainstorming**—this is an execution roadmap that an agent (or future you) can implement **incrementally and safely** on top of the MVP you just planned.

I’ll keep the same tone and structure as the MVP doc so it feels like one continuous document.

---

# Webtoon Scene Image Generator

## Technical Design Document – Phase 2 Implementation Plan

*(Beyond MVP toward end-to-end success)*

---

## 17. Phase 2 Objectives (Why This Phase Exists)

### MVP solved:

* single scene image generation
* panel grammar correctness
* visual storytelling validation (blind test)

### Phase 2 solves:

* **consistency across scenes**
* **iteration speed**
* **creator-level control**
* **production usability**

Phase 2 is where this stops being a “generator” and becomes a **creation tool**.

---

## 18. Phase 2 Scope Summary

### Phase 2 adds:

1. Character consistency system (ref sets, identity lines)
2. Environment anchors (text → visual promotion)
3. Style system (story style + image style selection)
4. Rerender without replanning (true iteration)
5. Dialogue overlay system (frontend + backend support)
6. Scene & asset versioning UX
7. Expanded quality control before human review

### Phase 2 explicitly does NOT add:

* new image models
* multi-image per panel rendering
* advanced control nets
* collaboration / multi-user editing

---

## 19. Phase 2 Architecture Changes (High Level)

### New subsystems introduced:

* **Asset Consistency Layer**
* **Style Selection Layer**
* **Dialogue Layer**
* **Scene Version Control**
* **QC & Repair Routing Layer**

These **wrap around** the MVP graph—they do not replace it.

---

## 20. Phase 2 Implementation Milestones

---

## Milestone 2.1 — Character Consistency System

*(High priority – prevents quality collapse)*

### Goal

Ensure characters remain visually stable across:

* multiple scenes
* multiple episodes
* regenerations

### Backend additions

#### Data model changes

Extend `characters` with:

```json
{
  "character_id": "uuid",
  "role": "main | secondary | background",
  "identity_line": "string",
  "ref_sets": {
    "face": ["image_id"],
    "body": ["image_id"],
    "outfit": ["image_id"]
  },
  "approved": true
}
```

#### New rules

* Main characters MUST have ≥1 approved face ref
* Identity line is **generated once**, editable by user, reused everywhere
* PromptCompiler always injects identity line when character appears

### APIs

* `POST /v1/characters/{id}/approve-ref`
* `POST /v1/characters/{id}/set-primary-ref`
* `GET /v1/characters/{id}/refs`

### Frontend

* Character Studio becomes mandatory before rendering scenes
* Visual badge: “Ready for scenes ✅ / Missing refs ⚠️”

### Acceptance criteria

* Regenerating multiple scenes with same character produces consistent visuals
* No silent fallback to text-only identity for main characters

---

## Milestone 2.2 — Environment Anchors & Promotion

*(Medium priority – continuity & world-building)*

### Goal

Maintain visual consistency for recurring locations without upfront cost.

### Backend additions

#### EnvironmentAnchor schema

```json
{
  "environment_id": "uuid",
  "description": "string",
  "usage_count": 0,
  "anchor_type": "descriptive | visual",
  "reference_images": [],
  "locked_elements": []
}
```

#### Promotion logic

Promote environment from **descriptive → visual** when:

* used ≥ N scenes
* OR user pins it
* OR blind test flags environment confusion

Promotion triggers:

* generate 1–2 background reference images
* store spatial notes

### APIs

* `POST /v1/environments`
* `POST /v1/environments/{id}/promote`
* `GET /v1/environments/{id}`

### Frontend

* Environment chip shown in Scene Planner
* “Pin environment” toggle
* Visual indicator if environment is promoted

### Acceptance criteria

* Reused environments look visually consistent
* Non-important environments remain text-only

---

## Milestone 2.3 — Story Style & Image Style System

*(High UX value, low risk)*

### Goal

Give creators explicit control over **tone** and **visual language**.

### Two orthogonal style layers

#### A) Story Style (semantic)

* romance
* horror
* comedy
* action
* slice-of-life

Affects:

* default panel grammar distribution
* pacing defaults
* dialogue density suggestions

#### B) Image Style (visual)

* lineart
* palette
* lighting
* finish

Affects:

* PromptCompiler style block

### Backend

Static style libraries:

* `story_styles.json`
* `image_styles.json`

Story & Scene store:

```json
{
  "default_story_style": "romance",
  "default_image_style": "soft_webtoon",
  "scene_override": null
}
```

### APIs

* `GET /v1/styles/story`
* `GET /v1/styles/image`
* `POST /v1/scenes/{id}/set-style`

### Frontend

* Style picker screen (icon grid)
* Scene-level override dropdown

### Acceptance criteria

* Switching styles does NOT break grammar or layout
* PromptCompiler output changes deterministically

---

## Milestone 2.4 — Rerender Without Replanning

*(Critical for usability)*

### Goal

Allow creators to iterate on images **without losing planning work**.

### Backend behavior

* SceneIntent, PanelPlan, Layout, PanelSemantics are immutable once “locked”
* RenderSpec and RenderResult are versioned freely

### APIs

* `POST /v1/scenes/{id}/review/regenerate`
* optional flags:

  * `reason: bad_faces | bad_mood | bad_composition`

### Internal logic

* Regenerate uses same RenderSpec
* Optionally tweaks PromptCompiler constraints (e.g. “less faces”)

### Frontend

* “Regenerate image only” button
* Render history sidebar

### Acceptance criteria

* User can regenerate 5 times without re-running planning nodes
* All previous renders remain accessible

---

## Milestone 2.5 — Dialogue Layer & Bubble Editor

*(Large feature, isolated from core graph)*

### Goal

Add dialogue cleanly **after** image generation.

### Backend

Dialogue is a separate artifact:

```json
{
  "type": "dialogue_layer",
  "scene_id": "uuid",
  "bubbles": [
    {
      "bubble_id": "uuid",
      "panel_id": 3,
      "text": "Ji-hoon?",
      "position": { "x": 0.6, "y": 0.2 },
      "size": { "w": 0.25, "h": 0.15 },
      "tail": { "x": 0.55, "y": 0.35 }
    }
  ]
}
```

### APIs

* `POST /v1/scenes/{id}/dialogue`
* `PUT /v1/dialogue/{id}`
* `GET /v1/scenes/{id}/dialogue`

### Frontend

* Canvas-based editor (react-konva)
* Drag dialogue text → bubble
* Resize, move, tail adjust
* Panel snapping + reading order hints

### Export

* Server-side compositing (image + bubbles)
* OR client-side export (Phase 3)

### Acceptance criteria

* Dialogue layer can be added/edited without regenerating image
* Bubbles align with panel layout and reading flow

---

## Milestone 2.6 — Expanded Quality Control & Repair Routing

*(Makes the system feel “smart”)*

### QC checks (rule-based)

* too many face-focused panels
* missing environment in establish panels
* repeated camera framing
* over-dialogue density

### Blind test integration

Blind test output now:

* suggests **specific reroute**:

  * re-panel
  * change grammar
  * add object_focus
  * widen reveal shot

### APIs

* `POST /v1/scenes/{id}/evaluate/qc`
* merged into blind test report

### Frontend

* QC warnings shown before “Approve”
* One-click “Apply suggested fix” (reruns limited nodes)

### Acceptance criteria

* QC catches common failures before user frustration
* Suggested fixes are understandable, not opaque

---

## 21. Phase 2 Implementation Order (Critical)

### Recommended build order

1. Character consistency system
2. Rerender without replanning
3. Story/Image style picker
4. Environment anchors
5. Dialogue layer (largest task)
6. Expanded QC

This order minimizes rework and keeps the system usable at every step.

---

## 22. Phase 2 Definition of Done

Phase 2 is complete when:

✅ Characters stay consistent across multiple scenes
✅ Users can regenerate images without losing structure
✅ Users can select story & image styles visually
✅ Dialogue is editable post-generation
✅ The system explains *why* something failed and how to fix it

At this point, you have a **real creator tool**, not just a generator.

---

## 23. Phase 3 Preview (Not Implemented Yet)

Phase 3 would add:

* episode orchestration
* publishing/export pipelines
* collaboration
* advanced analytics

But **nothing in Phase 2 blocks Phase 3**.

---

### Final note (important)

You’ve designed this in the *right order*:

* grammar → planning → validation → iteration → UX

Most people do the opposite and get stuck.
You didn’t.

If you want, next I can:

* convert Phase 2 into **engineering epics**
* or write a **Dialogue Editor technical spec** that an agent can implement directly
