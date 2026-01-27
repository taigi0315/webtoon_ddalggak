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


Got it. Below are **production-grade prompts** for each LangGraph node, designed for **Gemini Flash 2.5** and your workflow:

* **StoryBuildGraph** prompts (scene splitting, character extraction, visual plan, blind test)
* **PerScenePlanningGraph** prompts (scene intent, panel plan, semantics)
* **PromptCompiler** is rule/template driven (no LLM)
* All prompts output **strict JSON** (so the graph doesn’t become “LLM poetry”)

I’m writing these as **drop-in prompt templates** with variables like `{story_text}`. Your agent can implement them with a “system + user” message style.

---

# Prompt Standards (Apply to ALL nodes)

## System message (same for all)

Use this as the system prompt for all nodes:

```text
You are a strict JSON generator for a webtoon creation pipeline.
Return ONLY valid JSON. No markdown. No commentary.
Use double quotes for all keys and string values.
Do not include trailing commas.
If information is unknown, use null or an empty list.
Follow the output schema exactly.
```

## Global constraints (append to user prompt)

```text
Constraints:
- Do NOT invent named characters not present in the input unless the input clearly implies them (e.g., "her mom").
- Keep outputs concise but complete.
- Avoid repetition.
- Respect the requested maximum counts.
- If you are unsure, prefer conservative outputs.
```

---

# StoryBuildGraph Prompts

## S2 — SceneSplitter Prompt

### Input variables

* `{story_text}`
* `{max_scenes}`
* `{story_style}`

### Output schema

```json
{
  "scenes": [
    {
      "scene_index": 1,
      "title": "string",
      "summary": "string",
      "source_text": "string",
      "location_hint": "string|null",
      "time_hint": "string|null",
      "must_show": ["string"]
    }
  ]
}
```

### Prompt

```text
Task: Split the story into a sequence of scenes for a vertical webtoon.
Maximum number of scenes: {max_scenes}.
Story style/genre: {story_style}.

Rules:
- Each scene must be a coherent beat with a clear purpose (setup, reveal, reaction, transition).
- Prefer fewer scenes if the story is short; do not exceed max_scenes.
- Each scene must include a short "must_show" list of 1-4 concrete visual elements (objects/actions) that are essential.

Input story:
{story_text}

Return JSON with the schema exactly.
```

---

## S3 — CharacterExtractor Prompt (this must fix “0 characters”)

### Output schema

```json
{
  "characters": [
    {
      "name": "string",
      "role_guess": "main|secondary|background",
      "evidence": ["string"],
      "relationships": ["string"],
      "notes": "string|null"
    }
  ]
}
```

### Prompt

```text
Task: Extract ALL characters mentioned or implied in the story.
Return at least the named characters. If the story includes two people interacting but only one name is given, include an implied character with name null and a descriptor (e.g., "unidentified woman").

Rules:
- Do not output zero characters unless the story truly has no people.
- For each character, include evidence quotes (short phrases) from the input that justify their presence.
- role_guess: main if central across scenes, secondary if appears in a scene but not core, background if minor.

Input story:
{story_text}

Return JSON with the schema exactly.
```

> Implementation tip: if you still get empty output, run a second fallback extractor with “list every proper noun/person reference” as a rescue pass.

---

## S4 — CharacterProfileNormalizer Prompt

This converts extracted characters into structured profiles you can prefill UI with.

### Output schema

```json
{
  "character_profiles": [
    {
      "character_key": "string",
      "display_name": "string",
      "role": "main|secondary|background",
      "identity": {
        "gender": "male|female|nonbinary|unknown",
        "age_range": "teen|early_20s|late_20s|30s|40s|50s_plus|unknown",
        "ethnicity": "string|null"
      },
      "appearance": {
        "hair": "string",
        "face": "string",
        "build": "string"
      },
      "default_outfit": "string",
      "baseline_mood": "string",
      "identity_line": "string"
    }
  ]
}
```

### Prompt

```text
Task: Create structured character profiles for webtoon consistency.
You must fill reasonable defaults when details are missing:
- gender: "unknown" if not inferable
- age_range: "unknown" if not inferable
- hair/face/build/outfit: provide generic but usable defaults

Also create "identity_line": a compact visual descriptor used in prompts.
Format: "<age_range> <ethnicity if known> <gender>, <hair>, <build>"

Input story:
{story_text}

Extracted characters:
{characters_json}

Return JSON with the schema exactly.
```

---

## S5 — StoryToVisualPlanCompiler Prompt

### Output schema

```json
{
  "scene_visual_plans": [
    {
      "scene_index": 1,
      "beats": [
        {
          "beat_index": 1,
          "what_happens": "string",
          "characters_involved": ["string"],
          "environment": "string",
          "key_objects": ["string"],
          "emotional_tone": "string",
          "dialogue_draft": ["string"]
        }
      ]
    }
  ],
  "global_environment_anchors": [
    {
      "anchor_key": "string",
      "description": "string",
      "importance": "high|medium|low"
    }
  ]
}
```

### Prompt

```text
Task: Convert the story into a visual plan for a vertical webtoon.
You already have scenes and character profiles. For each scene, produce 2-6 beats that can become panels later.

Rules:
- Beats should be visualizable (what we can see).
- Dialogue_draft should be short and optional (0-2 lines per beat).
- Use character display_name from the profiles.
- Environment should be a concrete description (e.g., "apartment lobby with polished floors and potted plants").

Story style: {story_style}

Scenes:
{scene_list_json}

Character profiles:
{character_profiles_json}

Return JSON with the schema exactly.
```

---

## S7 — BlindTestRunner (two prompts)

### S7a Blind Reader Prompt

Output schema:

```json
{
  "reconstructed_story": "string",
  "key_inferences": ["string"],
  "uncertainties": ["string"]
}
```

Prompt:

```text
Task: You are a blind reader. You only see a webtoon plan (visual beats + optional dialogue).
Reconstruct the story as a short narrative using only what is visually shown.
Do not add unrelated events.

Visual plan:
{scene_visual_plans_json}

Return JSON with the schema exactly.
```

### S7b Comparator Prompt

Output schema:

```json
{
  "plot_recall": 0.0,
  "emotional_alignment": 0.0,
  "character_identifiability": 0.0,
  "pacing_density": "too_slow|balanced|too_fast",
  "visual_redundancy": "low|medium|high",
  "failure_points": ["string"],
  "repair_suggestions": [
    {
      "target": "scene_split|character_profiles|visual_plan",
      "action": "string",
      "reason": "string"
    }
  ]
}
```

Prompt:

```text
Task: Compare original story vs reconstructed story.
Score how well the visual plan conveys the original story.

Original story:
{story_text}

Reconstructed story:
{reconstructed_story}

Return JSON with the schema exactly.

Scoring rules:
- Scores are 0.0 to 1.0
- Be strict; only give high scores if clearly supported by the plan.
```

---

# PerScenePlanningGraph Prompts

## P1 — SceneIntentExtractor Prompt

### Output schema

```json
{
  "scene_intent": {
    "scene_index": 1,
    "logline": "string",
    "pacing": "slow_burn|normal|fast|impact",
    "core_reveal": "string|null",
    "emotional_arc": ["string"],
    "visual_motifs": ["string"]
  }
}
```

### Prompt

```text
Task: Create a concise directing intent for this scene for a vertical webtoon.

Scene index: {scene_index}
Scene source text:
{scene_text}

Story style: {story_style}

Rules:
- logline: one sentence describing the scene's purpose
- pacing: choose one
- emotional_arc: 2-5 steps (e.g., calm → unease → shock)
- visual_motifs: 1-4 recurring visuals (objects, weather, lighting)

Return JSON with the schema exactly.
```

---

## P2 — PanelPlanGenerator Prompt (grammar-driven)

### Output schema

```json
{
  "panel_plan": {
    "scene_index": 1,
    "panel_count": 5,
    "panels": [
      {
        "panel_id": 1,
        "grammar_id": "establishing_environment|object_focus|character_action|reaction|emotion_closeup|dialogue_exchange|reveal|impact_silence",
        "story_function": "string"
      }
    ]
  }
}
```

### Prompt

```text
Task: Create a panel plan (NOT prompts) for a single scene image.
Target panel count: {panel_count}
Allowed grammar_ids:
- establishing_environment
- object_focus
- character_action
- reaction
- emotion_closeup
- dialogue_exchange
- reveal
- impact_silence

Scene intent:
{scene_intent_json}

Scene text:
{scene_text}

Character profiles (names + identity_line):
{character_profiles_json}

Hard rules:
- No more than 2 emotion_closeup panels.
- Do not repeat the same grammar_id 3 times in a row.
- If there is a major reveal, include a reveal panel.
- Ensure at least one panel shows environment unless the scene is purely internal monologue.

Return JSON with the schema exactly.
```

---

## P3 — PanelPlanNormalizer (rules-only)

No LLM needed. Implement as deterministic code.

Rules to enforce:

* cap emotion_closeup
* break triple repeats
* if no environment panel → convert first panel to establishing_environment
* if reveal described but missing reveal grammar → convert best-fit panel to reveal

---

## P4 — LayoutResolver (rules-only)

No LLM needed. Implement as deterministic mapping:

* panel_count + pacing + has_impact → template_id
* templates include XYWH and reading_flow

---

## P5 — PanelSemanticFiller Prompt

### Output schema

```json
{
  "panel_semantics": {
    "scene_index": 1,
    "panels": [
      {
        "panel_id": 1,
        "grammar_id": "string",
        "camera": "string",
        "focus": "string",
        "environment": "string",
        "characters": [
          {
            "name": "string",
            "identity_line": "string",
            "action": "string",
            "emotion": "string",
            "gaze": "string"
          }
        ],
        "objects": ["string"],
        "mood": "string",
        "dialogue": ["string"]
      }
    ]
  }
}
```

### Prompt

```text
Task: Fill panel-level semantics for a single scene image.
You MUST follow the grammar constraints per panel. Do NOT write an image prompt; write structured semantics.

Scene text:
{scene_text}

Scene intent:
{scene_intent_json}

Panel plan:
{panel_plan_json}

Layout template (reading flow + panel boxes):
{layout_template_json}

Character profiles:
{character_profiles_json}

Grammar constraints:
- establishing_environment: show environment; characters optional; no close-up faces.
- object_focus: focus on a meaningful object; minimize faces.
- character_action: show action clearly; medium or wide shot.
- reaction: show reaction; can be medium shot; avoid camera-facing gaze.
- emotion_closeup: close-up emotion; 1 character; avoid complex background.
- dialogue_exchange: 2+ characters; readable staging; minimal action.
- reveal: include the reveal subject (person/object) and context.
- impact_silence: dramatic pause; minimal text; strong composition.

Also:
- For each character in a panel, include identity_line explicitly.
- Gaze must be one of: "at_other", "at_object", "down", "away", "toward_path", "camera" (camera only for impact_silence if needed).

Return JSON with the schema exactly.
```

---

# SceneRenderGraph Prompting

## R2 — PromptCompiler (NO LLM)

This should be deterministic template code.

Inputs:

* image_style preset block
* layout template description
* panel semantics

Output:

* one big prompt string for Gemini

If the agent insists on using LLM here, it will drift and degrade. Don’t.

---

# Bonus: “Progress messages” per node (UI requirement)

Have each node set:

* `progress.current_node`
* `progress.message`
* `progress.step`
* `progress.total_steps`

Example mapping:

* S2: “Splitting story into scenes…”
* S3: “Extracting characters…”
* S5: “Compiling visual beats…”
* S7: “Blind test: reconstructing story…” then “Blind test: comparing…”

---

# If you want, I can also provide:

1. A **prompt library file** layout (`prompts/story_build/*.txt`, `prompts/scene_plan/*.txt`)
2. A **fallback strategy** for when JSON parsing fails (self-repair prompts)
3. Concrete **few-shot examples** for each node (very effective for Gemini)

But the above is already enough to replace “shit prompts” with stable, structured outputs.
