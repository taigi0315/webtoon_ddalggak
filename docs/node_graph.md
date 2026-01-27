Yes. Below is a **clean, non-messy LangGraph specification** you can hand to the agent to rebuild the graph. It’s structured as **two graphs + shared libraries**, because mixing “story generation”, “character refs”, “scene rendering”, and “blind test” into one spaghetti graph is exactly how implementations become a mess.

This matches our development plan and your corrected workflow:

* **Agents decide** planning
* Humans only **Generate / Regenerate / Approve**
* **Blind test happens early** (story-writing stage), not in scene render

---

# LangGraph Architecture Spec (Clean + Implementable)

## Core Principle

Build **separate graphs** for separate lifecycle stages:

1. **StoryBuildGraph** (story → scenes + characters + per-scene plans + blind test)
2. **SceneRenderGraph** (approved plan → compile prompt → render image)
3. *(Optional later)* **DialogueLayerGraph** (does not need LangGraph; it’s UI-driven)

Do **not** create one monolithic graph that tries to do everything.

---

# Shared State & Artifact Model

## Shared State Keys (minimum)

These keys live in LangGraph state and are persisted to DB via artifacts.

```json
{
  "project_id": "...",
  "story_id": "...",
  "scene_id": "...",

  "story_text": "...",
  "max_scenes": 12,
  "story_style": "romance",
  "image_style": "soft_webtoon",

  "characters": [...],
  "scenes": [...],

  "scene_intent": {...},
  "panel_plan": {...},
  "layout_template": {...},
  "panel_semantics": {...},
  "render_spec": {...},
  "render_result": {...},

  "blind_test_report": {...},

  "progress": {
    "current_node": "PanelSemanticFiller",
    "message": "Generating panel semantics for Scene 3/12",
    "step": 8,
    "total_steps": 18
  }
}
```

### Artifact rule (critical)

Every meaningful output must be stored as an artifact (versioned).
The graph state is *transient*; DB artifacts are the truth.

---

# Graph 1: StoryBuildGraph (Phase 2-style “Generate Story”)

## Goal

Given:

* story_style + image_style
* story_text
* max_scenes

Produce:

* scenes (readable summaries + per-scene text chunks)
* character profiles (non-empty!)
* per-scene planning artifacts (intent/plan/layout/semantics) **optional in v1**
* blind test report (early)

This is the graph that runs when user clicks **Generate Story**.

---

## StoryBuildGraph Nodes & Responsibilities

### Node S1 — `ValidateStoryInputs`

**Input:** story_text, max_scenes, style selections
**Output:** validated config (caps, defaults)
**Rules:**

* enforce `1 <= max_scenes <= hard_cap` (e.g. 30)

**Progress:** “Validating inputs…”

---

### Node S2 — `SceneSplitter`

**Input:** story_text, max_scenes
**Output artifact:** `scene_list`

* list of scenes: `{scene_index, title, summary, source_text}`

**Requirement:**

* UI must show readable summary + text, never scene IDs.

**Progress:** “Splitting story into scenes (N max)…”

---

### Node S3 — `CharacterExtractor`

**Input:** full story text + scene_list + story_style
**Output artifact:** `character_profiles`

* MUST be non-empty if story contains named characters
* produces structured character profiles: appearance, identity_line, role guess

**Progress:** “Extracting characters from story…”

---

### Node S4 — `CharacterProfileNormalizer` (rules)

**Input:** character_profiles
**Output artifact:** normalized character_profiles

* dedupe similar names
* enforce required fields (gender/age/hair/outfit fallback)
* generate `identity_line` for each character

**Progress:** “Normalizing character profiles…”

---

### Node S5 — `StoryToVisualPlanCompiler` (high-level)

**Purpose:** convert story into a scene-by-scene *visual plan* without rendering images.
**Input:** scenes + characters + story_style
**Output artifact:** `visual_plan_bundle` with per-scene:

* key beats / objects / environment anchors
* dialogue draft (optional)
* “must-show” items list

**Progress:** “Converting story to visual beats…”

> This is where you avoid the failure you saw (story has scenes but no characters).
> This node must always reference the character profiles.

---

### Node S6 — `PerScenePlanningLoop` (subgraph call, optional)

For each scene, generate planning artifacts. This is optional in early v1, but recommended if you want scenes immediately ready to render.

Subgraph (reused from SceneRender planning stage):

* SceneIntentExtractor
* PanelPlanGenerator
* LayoutResolver
* PanelSemanticFiller

**Progress:** “Planning scene i / N…”

---

### Node S7 — `BlindTestRunner` (EARLY QUALITY CHECK)

**Input:** original story + the compiled visual plan (panel-style descriptions + dialogue)
**Output artifact:** `blind_test_report`

**Exact steps inside node (2 LLM calls):**

1. **Blind Reader:** reconstruct story from visual descriptions (+ dialogue) only
2. **Comparator:** compare reconstructed story vs original story

**Progress:**

* “Blind test: reconstructing story from visuals…”
* “Blind test: comparing with original…”

**Important placement:**
✅ This runs during story generation, before any image rendering.

---

### Node S8 — `PersistStoryBundle`

**Input:** scene_list, character_profiles, visual_plan_bundle, blind_test_report
**Output:** DB writes + returns IDs

* create/update scene records
* create character records
* attach artifacts to story/scenes

**Progress:** “Saving story bundle…”

---

## StoryBuildGraph Edges

```
S1 ValidateStoryInputs
  → S2 SceneSplitter
  → S3 CharacterExtractor
  → S4 CharacterProfileNormalizer
  → S5 StoryToVisualPlanCompiler
  → (optional) S6 PerScenePlanningLoop
  → S7 BlindTestRunner
  → S8 PersistStoryBundle
  → END
```

### Conditional branches

* If `CharacterExtractor` returns empty AND story has named entities → retry with stricter prompt OR fallback to heuristic extraction.
* If blind test fails thresholds → return failure report + suggested repairs (do not render images).

---

# Graph 2: SceneRenderGraph (Per-scene “Generate Image”)

## Goal

Given an already planned scene (semantics + layout), produce:

* render_spec (compiled prompt)
* render_result (image)

This is what runs when user clicks **Generate Image** for a scene.

---

## SceneRenderGraph Nodes & Responsibilities

### Node R1 — `LoadActiveSceneArtifacts`

**Input:** scene_id
**Output:** best available artifacts:

* panel_semantics (required)
* layout_template (required)
* image_style/story_style (from story defaults or scene override)
* character identity_lines (always)

**Progress:** “Loading scene plan…”

---

### Node R2 — `PromptCompiler`

**Input:** panel_semantics + layout_template + image_style + character identity_line
**Output artifact:** `render_spec`

* single prompt string for Gemini multi-panel image
* includes global style block + layout instructions + per-panel compiled text

**Progress:** “Compiling prompt…”

---

### Node R3 — `GeminiRenderImage`

**Input:** render_spec
**Output artifact:** `render_result` (image_url + metadata)

**Progress:** “Generating image…”

---

### Node R4 — `QuickQC` (rules-only, cheap)

**Input:** render_spec + (optional render_result metadata)
**Output artifact:** `qc_report`

* checks like: too many closeup grammars, missing environment grammar, etc.
* *Not blind test.*

**Progress:** “Quality checks…”

---

### Node R5 — `PersistRender`

Store render_result and mark it as latest for the scene.

**Progress:** “Saving render…”

---

## SceneRenderGraph Edges

```
R1 LoadActiveSceneArtifacts
  → R2 PromptCompiler
  → R3 GeminiRenderImage
  → R4 QuickQC
  → R5 PersistRender
  → END
```

### Regenerate flow

Regenerate image should **skip planning** and reuse same render_spec:

```
R1 LoadActiveSceneArtifacts (or load render_spec directly)
  → R3 GeminiRenderImage
  → R4 QuickQC
  → R5 PersistRender
  → END
```

---

# Subgraph: PerScenePlanningGraph (Reusable building block)

This is the planning slice used in StoryBuildGraph loop OR on-demand per scene.

### Nodes

1. `SceneIntentExtractor` (LLM)
2. `PanelPlanGenerator` (LLM)
3. `PanelPlanNormalizer` (rules)
4. `LayoutResolver` (rules)
5. `PanelSemanticFiller` (LLM)

### Edges

```
P1 SceneIntentExtractor
 → P2 PanelPlanGenerator
 → P3 PanelPlanNormalizer
 → P4 LayoutResolver
 → P5 PanelSemanticFiller
 → END
```

---

# How “Progress UI” should work (fix the “takes forever” issue)

Every node must emit progress events. In LangGraph you can:

* update `state.progress` at node start/end
* stream events to frontend via:

  * SSE endpoint (`/events/{job_id}`)
  * or WebSocket

### Minimum fields for UI

* `current_node`
* `message`
* `step`, `total_steps`

Example messages:

* “Splitting story into scenes (3/12)…”
* “Extracting characters…”
* “Planning scene 4/12…”
* “Blind test: reconstructing story…”

---

# Why your current graph likely became a mess

Common failure modes:

1. Putting blind test inside scene rendering graph
2. Mixing “create story”, “create characters”, “render scenes” in one loop
3. Not persisting artifacts per step → UI loses state when navigating
4. Letting UI drive planning decisions (panel plan controls exposed)
5. No job/progress abstraction → UI blocks and times out

The separation above fixes all of these.

---

# What to tell the agent to rebuild (copy/paste instruction)

> Rebuild LangGraph into two graphs: StoryBuildGraph and SceneRenderGraph.
> StoryBuildGraph runs when user clicks “Generate Story” and must produce scene_list + character_profiles + blind_test_report (early).
> SceneRenderGraph runs per scene and only compiles prompt and renders image from existing semantics/layout.
> Use a reusable PerScenePlanningGraph subgraph for intent/plan/layout/semantics generation.
> Every node must emit progress events. Every output is stored as a versioned artifact.

---

If you want, paste me (or summarize) the **current node list / edges** from the messy implementation and I’ll rewrite it into the above structure with a concrete mapping: “old node X becomes S3”, “old node Y removed”, etc.
