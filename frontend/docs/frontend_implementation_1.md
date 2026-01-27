I’ll assume the recommended stack:

* **Next.js + React + TypeScript**
* **TailwindCSS**
* **Zustand** (state)
* **react-konva** (bubble editor canvas)
* Optional: **TanStack Query** for API caching (highly recommended)

---

# Webtoon Scene Image Generator

## Frontend Implementation Plan (Phase F1–F3)

---

## F0. Goals

Frontend must enable creators to:

1. manage story/scenes
2. create and approve character refs
3. view planning artifacts before paying generation cost
4. generate and iterate renders (history + regenerate)
5. place dialogue bubbles via drag/drop
6. export episode assets

---

## F1. Tech Stack & Project Setup

### Recommended stack

* Next.js (App Router) + React + TypeScript
* TailwindCSS
* Zustand (global state)
* TanStack Query (server-state: artifacts, renders, jobs)
* react-konva (canvas editor)
* zod (runtime validation of API payloads)

### Deliverables

* Running frontend app with routing and auth placeholder
* API client wrapper with typed contracts
* Layout + navigation shell

### Tasks

1. Create app skeleton
2. Add Tailwind + theme tokens (spacing, typography)
3. Add API client:

   * `GET/POST` wrappers
   * error handling
4. Add TanStack Query and global providers
5. Add Zustand stores:

   * `projectStore`, `sceneStore`, `editorStore`
6. Add base components:

   * Button, Card, Modal, Tabs, Toast, Spinner

### Acceptance criteria

* App loads, has sidebar navigation, can call `/health`
* Basic page routing works

---

## F2. Data Model in Frontend (State Strategy)

### Split state into two kinds

1. **Server state** (TanStack Query):

* projects, stories, scenes
* artifacts (intent, plan, layout, semantics, render_spec, render_result)
* blind test reports
* jobs and exports

2. **UI/editor state** (Zustand):

* selected story/scene
* active artifact IDs (the “current working set”)
* editor selections (selected panel, selected bubble)
* drag state, zoom/pan state

### Deliverables

* Strong typing for artifact payloads (zod schemas)
* Scene “active pointers” stored in UI state

### Acceptance criteria

* Scene page can fetch artifacts and pick latest versions reliably

---

## F3. Screen-by-Screen Implementation Plan

---

# Screen 1 — Project Dashboard

### Features

* List projects
* Create project
* Recent projects

### Components

* `ProjectCard`
* `CreateProjectModal`

### API usage

* `GET /v1/projects`
* `POST /v1/projects`

### Acceptance criteria

* User can create and open project

---

# Screen 2 — Story Editor + Scene Builder

### Features

* Edit story text
* Create scenes from text chunk
* List scenes

### Components

* `StoryEditor`
* `SceneList`
* `CreateSceneModal`

### API usage

* `POST /v1/projects/{project_id}/stories`
* `POST /v1/stories/{story_id}/scenes`
* `GET /v1/stories/{story_id}`
* `GET /v1/stories/{story_id}/scenes` (add this endpoint or reuse scenes listing)

### Acceptance criteria

* User can create story, paste text, create scenes

---

# Screen 3 — Character Studio (Ref Generation + Approval)

### Features

* Create character profile
* Generate reference batches (image generation call)
* Approve “face ref”
* Mark role (main/secondary)
* Identity line preview

### Components

* `CharacterList`
* `CharacterProfileForm`
* `ReferenceGallery`
* `ReferenceImageCard` (Approve/Reject/SetPrimary)

### API usage

* `POST /v1/stories/{story_id}/characters`
* `POST /v1/characters/{id}/reference-images`
* `POST /v1/characters/{id}/set-primary-ref`
* `POST /v1/characters/{id}/approve-ref`

### Acceptance criteria

* Main character can be marked “Ready ✅” only after primary face ref exists

---

# Screen 4 — Styles Picker

### Features

* Select story style (genre) and image style
* Apply to story default
* Override per scene

### Components

* `StyleGrid`
* `StyleCard`
* `SceneStyleOverrideDropdown`

### API usage

* `GET /v1/styles/story`
* `GET /v1/styles/image`
* `POST /v1/scenes/{id}/set-style` (or story-level setter)

### Acceptance criteria

* Selected style affects RenderSpec compilation for next renders

---

# Screen 5 — Scene Planner (Panel plan + layout + semantics)

### Features

* Show scene source text
* Generate scene-intent
* Generate panel-plan
* Normalize plan
* Select layout template
* Generate semantics
* Manual edits:

  * panel count
  * swap grammar for a panel
  * lock panel

### Components

* `SceneSourcePane`
* `ArtifactTimeline` (intent/plan/layout/semantics)
* `PanelPlanTimeline` (grammar chips)
* `LayoutPreview` (box diagram)
* `PanelSemanticCards`

### API usage

* `POST /generate/scene-intent`
* `POST /generate/panel-plan`
* `POST /generate/panel-plan/normalize`
* `POST /generate/layout`
* `POST /generate/panel-semantics`

### Acceptance criteria

* A user can reach a complete plan without image generation
* Artifacts show versions and “latest” is selectable

---

# Screen 6 — Scene Renderer (Render + history + blind test)

### Features

* Compile RenderSpec
* Generate image
* Show render history
* Regenerate image only
* Run blind test
* Approve

### Components

* `RenderHistoryStrip`
* `SceneImageViewer`
* `PanelOverlayToggle`
* `BlindTestPanel` (scores + suggestions)
* `RenderControls` (Render / Regenerate / Approve)

### API usage

* `POST /generate/render-spec`
* `POST /generate/render`
* `POST /evaluate/blind-test`
* `POST /review/approve`
* `POST /review/regenerate`

### Acceptance criteria

* Multiple render results can be browsed
* Regenerate does not change plan artifacts unless user requests it

---

# Screen 7 — Dialogue Editor (Bubble Drag/Drop + Tails)

This is the most important “pro-grade” editor screen.

## 7.1 Key design decisions

* Use **react-konva**
* Store bubble objects as JSON (normalized coordinates)
* Keep bubble layer separate from the image

## 7.2 Features

* show scene image as background
* show optional panel boundaries overlay
* right-side dialogue list (draggable lines)
* drag onto canvas creates a bubble
* bubble selection, move, resize
* tail handle dragging
* edit text inline (textarea modal or side inspector)
* undo/redo
* auto snap bubble into a panel
* reading order hint (small numbering)

## 7.3 Components

* `DialogueEditorLayout`
* `BubbleCanvasStage` (Konva Stage)
* `SceneImageLayer`
* `PanelBoundaryLayer`
* `BubbleLayer`
* `SpeechBubble` (Group: shape + tail + text)
* `BubbleTransformer` (resize handles)
* `DialogueList` (drag source)
* `BubbleInspector` (edit text, speaker, style)
* `EditorToolbar` (select/move, bubble types)

## 7.4 Data model (frontend)

```ts
type Bubble = {
  id: string;
  panelId: number;
  type: "speech" | "thought" | "narration" | "sfx";
  text: string;
  x: number; y: number; w: number; h: number; // normalized 0..1
  tail?: { x: number; y: number }; // normalized
  style?: { fontSize?: number; bold?: boolean };
  zIndex: number;
};
```

## 7.5 API usage

* `GET /v1/scenes/{scene_id}/dialogue`
* `POST /v1/scenes/{scene_id}/dialogue`
* `PUT /v1/dialogue/{dialogue_layer_id}`

## 7.6 Acceptance criteria

* A user can place and edit bubbles reliably
* Saved dialogue layer reloads identically
* Drag/drop feels smooth and professional

---

# Screen 8 — Episode Builder + Export

### Features

* create episode
* add scenes and reorder (drag list)
* export with dialogue layers applied
* download zip

### Components

* `EpisodeSceneList` (sortable)
* `ExportPanel` (options + job progress)

### API usage

* `POST /episodes`
* `POST /episodes/{id}/scenes` (reorder)
* `POST /episodes/{id}/export`
* `GET /exports/{id}`

### Acceptance criteria

* Export job produces downloadable artifact
* Order matches UI

---

## F4. Frontend Implementation Milestones

### Milestone F1 — Shell + Projects/Stories/Scenes

* navigation + routing
* story editor
* scene creation/listing

### Milestone F2 — Character Studio

* create characters + upload/generate refs
* approve refs

### Milestone F3 — Scene Planner

* artifact display + generate buttons
* layout preview + panel semantics cards

### Milestone F4 — Scene Renderer

* render spec + render + history
* blind test + approve/regenerate

### Milestone F5 — Dialogue Editor

* Konva editor + drag/drop
* save/load dialogue layer

### Milestone F6 — Episode + Export

* reorder scenes
* export jobs + download

---

## F5. Testing Plan

### Unit tests

* bubble geometry normalization (resize/move)
* panel hit-testing (drop bubble into correct panel)
* artifact version selection logic

### Integration tests

* load a scene → generate artifacts → render → open dialogue editor → save layer

### Manual QA checklist (important)

* bubble drag smoothness
* text legibility
* undo/redo works
* regeneration does not delete dialogue layer

---

## F6. Definition of Done (Frontend)

Frontend is “done” when:

* user can complete an end-to-end workflow:
  story → characters → scene plan → render → dialogue bubbles → export

And:

* everything maps cleanly to stored artifacts (no hidden state)

---


Got it — we’ll do **(2) wireframe first**, then **(1) Dialogue Editor technical spec**.

---

# (2) Frontend Wireframes (ASCII)

These are “layout + components” wireframes you can hand to an agent. All pages share the same **App Shell**.

## Global App Shell

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ Top Bar: [Project/Story Breadcrumbs] [Scene dropdown] [Generate ▼] [User]     │
├───────────────┬──────────────────────────────────────────────────────────────┤
│ Sidebar       │ Main Content                                                  │
│ - Dashboard   │                                                              │
│ - Story       │                                                              │
│   - Editor    │                                                              │
│   - Characters│                                                              │
│   - Styles    │                                                              │
│   - Scenes    │                                                              │
│ - Episodes    │                                                              │
│ - Exports     │                                                              │
└───────────────┴──────────────────────────────────────────────────────────────┘
```

---

## Screen A — Dashboard

```
Main Content
┌──────────────────────────────────────────────────────────────────────────────┐
│ [New Project]  [New Story]                                                    │
├──────────────────────────────────────────────────────────────────────────────┤
│ Projects Grid                                                                 │
│ ┌───────────────┐ ┌───────────────┐ ┌───────────────┐                         │
│ │ Project Card  │ │ Project Card  │ │ Project Card  │                         │
│ │ progress bar  │ │ progress bar  │ │ progress bar  │                         │
│ └───────────────┘ └───────────────┘ └───────────────┘                         │
├──────────────────────────────────────────────────────────────────────────────┤
│ Recent Activity                                                               │
│ - Scene rendered…                                                             │
│ - Character approved…                                                         │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## Screen B — Story Editor + Scene Builder

```
Main Content
┌───────────────────────────────┬──────────────────────────────────────────────┐
│ Story Editor                  │ Scenes                                       │
│ ┌───────────────────────────┐ │ ┌──────────────────────────────────────────┐ │
│ │ (text area / markdown)    │ │ │ [Extract Scenes] [New Scene]            │ │
│ │                           │ │ │------------------------------------------│ │
│ │                           │ │ │ Scene 01  (status)  [Open]              │ │
│ │                           │ │ │ Scene 02  (status)  [Open]              │ │
│ │                           │ │ │ ...                                      │ │
│ └───────────────────────────┘ │ └──────────────────────────────────────────┘ │
│ [Save]                        │ (optional: scene boundary highlight preview) │
└───────────────────────────────┴──────────────────────────────────────────────┘
```

---

## Screen C — Character Studio (Ref generation + approval)

```
Main Content
┌─────────────────┬─────────────────────────────────────┬──────────────────────┐
│ Character List  │ Character Profile                    │ Reference Gallery    │
│ ┌─────────────┐ │ Name, Role, Age, Gender, Hair...     │ ┌──────────────────┐ │
│ │ Ji-hoon ✅   │ │ Identity Line (auto + editable)      │ │ [img] [img] [img]│ │
│ │ Min-ji  ⚠️   │ │ [Generate Refs] [Save]               │ │ [img] [img] [img]│ │
│ │ ...          │ │                                     │ └──────────────────┘ │
│ └─────────────┘ │ Ref Status: Face ✅ / Body optional   │ Actions per image:   │
│                 │                                       │ [Set Face] [Add] [X] │
└─────────────────┴─────────────────────────────────────┴──────────────────────┘
```

---

## Screen D — Styles Picker (Story style + Image style)

```
Main Content
┌──────────────────────────────────────────────────────────────────────────────┐
│ Story Style (Genre)                                                          │
│ [ Romance ] [ Horror ] [ Comedy ] [ Action ] [ Slice-of-life ]               │
├──────────────────────────────────────────────────────────────────────────────┤
│ Image Style                                                                  │
│ ┌───────────────┐ ┌───────────────┐ ┌───────────────┐                       │
│ │ Soft Webtoon   │ │ Noir Drama    │ │ Dynamic Ink   │  ...                  │
│ │ preview + icon │ │ preview + icon│ │ preview + icon│                       │
│ └───────────────┘ └───────────────┘ └───────────────┘                       │
│ [Apply to Story Defaults]   [Save]                                           │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## Screen E — Scene Planner (Plan before rendering)

```
Main Content
┌─────────────────────────────┬───────────────────────────────────────────────┬──────────────────────┐
│ Scene Source Text           │ Plan + Layout Preview                          │ Panel Semantics      │
│ ┌─────────────────────────┐ │ ┌───────────────────────────────────────────┐ │ ┌──────────────────┐ │
│ │ (read-only scene chunk) │ │ │ Artifacts: Intent | Plan | Layout | Sem   │ │ │ Panel 1 Card      │ │
│ │ highlight linked beats  │ │ │ [Generate Plan] [Refine] [Run Blind Test] │ │ │ env/objects/chars │ │
│ └─────────────────────────┘ │ │-------------------------------------------│ │ ├──────────────────┤ │
│                             │ │ Panel Plan Timeline (grammar chips)       │ │ │ Panel 2 Card      │ │
│                             │ │ [establish] [object] [reaction] ...       │ │ │ ...              │ │
│                             │ │-------------------------------------------│ │ ├──────────────────┤ │
│                             │ │ Layout Preview (boxes)                    │ │ │ Panel 3 Card      │ │
│                             │ │ [Template dropdown] [Lock layout]         │ │ │ ...              │ │
│                             │ │-------------------------------------------│ │ └──────────────────┘ │
│                             │ │ [Render Scene Image]                      │ │                      │
│                             │ └───────────────────────────────────────────┘ │                      │
└─────────────────────────────┴───────────────────────────────────────────────┴──────────────────────┘
```

---

## Screen F — Scene Renderer (Image + history + evaluation)

```
Main Content
┌─────────────────┬───────────────────────────────────────────────┬──────────────────────────┐
│ Render History  │ Scene Image Viewer (9:16)                      │ Evaluation & Controls    │
│ ┌─────────────┐ │ ┌───────────────────────────────────────────┐ │ ┌──────────────────────┐ │
│ │ v1 thumbnail │ │ │              (scene image)               │ │ │ [Compile Prompt]     │ │
│ │ v2 thumbnail │ │ │   [toggle panel overlay] [zoom/pan]      │ │ │ [Render] [Regen]     │ │
│ │ v3 thumbnail │ │ └───────────────────────────────────────────┘ │ │ [Approve]            │ │
│ └─────────────┘ │                                                 │ ├──────────────────────┤ │
│                 │                                                 │ │ Blind Test Scores     │ │
│                 │                                                 │ │ plot/emotion/clarity  │ │
│                 │                                                 │ │ suggestions           │ │
│                 │                                                 │ └──────────────────────┘ │
└─────────────────┴───────────────────────────────────────────────┴──────────────────────────┘
```

---

## Screen G — Dialogue Editor (Bubble drag/drop)

```
Main Content
┌──────────────────────┬───────────────────────────────────────────────┬───────────────────────┐
│ Toolbar              │ Canvas (Konva Stage)                           │ Dialogue List         │
│ [Select] [Bubble]    │ ┌───────────────────────────────────────────┐ │ ┌───────────────────┐ │
│ [Tail]   [Delete]    │ │  scene image background                    │ │ │ Panel 1           │ │
│ [Undo/Redo]          │ │  (optional panel overlay)                  │ │ │ - line 1 (drag)   │ │
│ Bubble Inspector:    │ │                                           │ │ │ Panel 2           │ │
│ - type, font, size   │ │  bubbles draggable + resizable + tails     │ │ │ - line 1 (drag)   │ │
│ - panel assignment   │ └───────────────────────────────────────────┘ │ └───────────────────┘ │
│ [Save Layer]         │ [Preview Export]                               │ [Auto-place] (optional)│
└──────────────────────┴───────────────────────────────────────────────┴───────────────────────┘
```

---

## Screen H — Episode Builder + Export

```
Main Content
┌───────────────────────────────┬──────────────────────────────────────────────┐
│ Episode Scenes (sortable)     │ Export                                         │
│ ┌───────────────────────────┐ │ ┌──────────────────────────────────────────┐  │
│ │ Scene 01  [drag]          │ │ │ Export format: [Webtoon strip ▼]         │  │
│ │ Scene 02  [drag]          │ │ │ Include dialogue: [x]                    │  │
│ │ Scene 03  [drag]          │ │ │ [Start Export]                            │  │
│ └───────────────────────────┘ │ │ Status: queued/running/done + download    │  │
│ [Add Scene]                   │ └──────────────────────────────────────────┘  │
└───────────────────────────────┴──────────────────────────────────────────────┘
```

---

# (1) Dialogue Editor Technical Spec (Konva-based)

This is the “agent-ready” spec: what to build, how interactions work, what math to use, and how to persist.

## 1. Purpose

A canvas editor that lets users place, edit, and manage dialogue bubbles (and later narration/SFX) **as a separate layer** on top of an approved scene image.

## 2. Inputs

* `render_result.image_url` (background image)
* `layout_template` (panel boundaries + reading flow)
* `panel_semantics.dialogue[]` (initial dialogue lines grouped by panel)
* optional existing `dialogue_layer` (load & edit)

## 3. Output

A `dialogue_layer` artifact payload:

* list of bubble objects in **normalized coordinates** (0..1 relative to the full 9:16 image)

### Bubble object schema (v1)

```json
{
  "bubble_id": "uuid",
  "panel_id": 3,
  "type": "speech | thought | narration | sfx",
  "text": "string",
  "geom": { "x": 0.62, "y": 0.18, "w": 0.24, "h": 0.12 },
  "tail": { "x": 0.58, "y": 0.30 },
  "style": { "font_family": "default", "font_size": 18, "bold": false },
  "z_index": 10
}
```

## 4. Coordinate system

**Always store normalized coordinates**:

* `x, y, w, h, tail.x, tail.y` are in `[0,1]` relative to the full image size.

At runtime:

* `px = norm * stageWidth` (and height accordingly)

This makes the layer resolution-independent and export-safe.

## 5. Konva layer structure

Use these layers in order (bottom → top):

1. `ImageLayer`: the scene image
2. `PanelOverlayLayer` (optional): panel boxes/lines
3. `BubbleLayer`: all bubbles
4. `UIOverlayLayer`: selection boxes, transformers, hover outlines

## 6. Bubble rendering

A bubble is a Konva `Group` with:

* `Shape` (rounded rect or ellipse)
* `Path` (tail)
* `Text`

### Bubble types

* speech: rounded rect + tail
* thought: ellipse + small “bubble dots” tail (can be v2)
* narration: rectangular box no tail
* sfx: text only (can be v2)

## 7. Core interactions

### 7.1 Drag dialogue line → drop to create bubble

**Drag source**: DialogueList item
**Drop target**: Canvas stage

Algorithm on drop:

1. Convert pointer position to normalized `(nx, ny)`
2. Determine `panel_id` by hit-testing against layout panel boxes:

   * Each panel has `(x,y,w,h)` normalized.
   * Find first panel where `nx,ny` inside bounds.
   * If none, set `panel_id=null` and show warning badge.
3. Create bubble:

   * default size based on text length
   * position centered at drop point
   * default tail anchor = slightly below bubble center
4. Add bubble to state; set as selected.

**Default sizing rule (simple, works well):**

* `w = clamp(0.18 + 0.006 * len(text), 0.18, 0.42)`
* `h = clamp(0.10 + 0.002 * lines(text), 0.10, 0.24)`
  (Use line breaks after measuring text in Konva as needed.)

### 7.2 Select bubble

Click bubble → set selected id
Shift-click optional for multi-select (v2)

### 7.3 Move bubble (drag)

Dragging bubble updates `geom.x/y` (normalized).
While dragging:

* optionally “snap” inside its panel bounds with padding.

**Snap rule (recommended):**

* When bubble is within a panel, clamp bubble box inside panel with `padding=0.02` normalized.

### 7.4 Resize bubble

Use Konva `Transformer` on selected bubble.
On transform end:

* compute new pixel bounds → convert to normalized `w/h`
* enforce min size:

  * `w >= 0.12`, `h >= 0.08`

### 7.5 Tail editing

Tail is a draggable handle point.

* Show tail handle only when bubble selected.
* Tail anchor updates `tail.x/y` (normalized).
* Tail should remain within same panel bounds unless user forces it (warn if outside).

### 7.6 Edit text

Two UX options (choose v1 simplest):

* Right inspector panel text area edits selected bubble text
* Auto-resize bubble height after text changes

### 7.7 Z-order

Buttons:

* bring forward / send backward (optional v1)
  Or simplest:
* newest bubble has higher `z_index`

### 7.8 Delete bubble

Delete key / toolbar button → remove selected bubble

### 7.9 Undo/Redo (must-have)

Implement command history in Zustand:

* `ADD_BUBBLE`
* `MOVE_BUBBLE`
* `RESIZE_BUBBLE`
* `EDIT_TEXT`
* `MOVE_TAIL`
* `DELETE_BUBBLE`

Store inverse operations for undo.

## 8. Reading flow assist (professional touch)

Given reading flow is top-to-bottom:

* In each panel, show small bubble order numbers (1,2,3) based on `(y then x)` of bubble positions.

Optional warning:

* if bubble order conflicts with expected reading order (e.g., bubble 2 is above bubble 1)

## 9. Panel overlay assist

Overlay toggle:

* show panel rectangles as thin lines
* hovering DialogueList panel highlights that panel region

## 10. Persistence model

### Save

`POST /v1/scenes/{scene_id}/dialogue` (or `PUT` if exists)
Payload = `dialogue_layer`

### Load

`GET /v1/scenes/{scene_id}/dialogue`

**Autosave** optional:

* debounce 500–1000ms after edits (v2)
  For v1: explicit “Save Layer” button is fine.

## 11. Export preview (optional v1)

* Client-side “Preview Export” composes bubbles over the image in-canvas (no server call)
* Final export remains server-side in Phase 3 export job

## 12. Acceptance Criteria (Dialogue Editor)

* Create bubble by drag/drop works reliably
* Bubble move/resize/tail edit stable
* Save → reload round-trips exactly
* Panel assignment correct with layout hit test
* Undo/redo for core actions works

---

If you want, next I can turn this into:

* a **component tree + file structure** (Next.js /app routes + components)
* and a **Zustand store spec** (types + actions) that an agent can implement directly.



No worries at all — and yep, you’ve got it: **Next.js is React**.

You asked for **(1) Next.js folder structure** → then **(2) DialogueEditor component tree + Zustand store**. Here you go.

---

# 1) Next.js App Router Folder Structure (Implementation-Ready)

This structure matches your screens, keeps things readable for agents, and isolates the Konva editor cleanly.

## Repo layout (frontend)

```
webtoon-frontend/
  app/
    layout.tsx
    globals.css
    page.tsx                          # redirect or dashboard

    (auth)/
      login/page.tsx                  # optional

    dashboard/
      page.tsx

    projects/
      page.tsx                        # list projects
      [projectId]/
        page.tsx                      # project overview
        stories/
          new/page.tsx
          [storyId]/
            page.tsx                  # story overview
            editor/page.tsx           # story editor + scene builder
            characters/page.tsx       # character studio
            styles/page.tsx           # style picker
            scenes/
              [sceneId]/
                page.tsx              # scene overview (tabs: planner/render)
                planner/page.tsx      # scene planner
                render/page.tsx       # scene renderer/review
                dialogue/page.tsx     # dialogue editor (Konva)
    episodes/
      page.tsx
      [episodeId]/
        page.tsx                      # episode builder + export

    exports/
      page.tsx
      [exportId]/page.tsx

  components/
    shell/
      AppShell.tsx                    # sidebar + topbar layout
      SidebarNav.tsx
      TopBar.tsx
      Breadcrumbs.tsx
      SceneSwitcher.tsx

    common/
      Button.tsx
      Card.tsx
      Modal.tsx
      Tabs.tsx
      Toast.tsx
      Spinner.tsx
      Badge.tsx
      Dropdown.tsx
      ConfirmDialog.tsx

    story/
      StoryEditor.tsx
      SceneList.tsx
      SceneCreateModal.tsx

    characters/
      CharacterStudio.tsx
      CharacterList.tsx
      CharacterForm.tsx
      IdentityLinePreview.tsx
      ReferenceGallery.tsx
      ReferenceImageCard.tsx

    styles/
      StyleGrid.tsx
      StyleCard.tsx
      SceneStyleOverride.tsx

    scene/
      ArtifactTimeline.tsx
      PanelPlanTimeline.tsx
      LayoutPreview.tsx
      PanelSemanticCards.tsx
      RenderHistoryStrip.tsx
      SceneImageViewer.tsx
      BlindTestPanel.tsx
      RenderControls.tsx

    dialogue/
      DialogueEditorLayout.tsx
      BubbleCanvasStage.tsx
      DialogueList.tsx
      BubbleInspector.tsx
      EditorToolbar.tsx
      bubbles/
        SpeechBubble.tsx
        BubbleTail.tsx
        BubbleTransformer.tsx
      utils/
        normalize.ts                   # px<->normalized
        hitTestPanels.ts               # panel detection
        bubbleSizing.ts                # default sizing heuristics
        readingOrder.ts                # order numbering per panel

  lib/
    api/
      client.ts                        # fetch wrapper
      endpoints.ts                     # typed endpoint funcs
      schemas.ts                       # zod schemas for payloads
    query/
      queryClient.ts
      keys.ts
    utils/
      ids.ts
      dates.ts

  stores/
    projectStore.ts                    # minimal UI state
    sceneStore.ts                      # active scene + selected artifacts
    dialogueEditorStore.ts             # Konva editor state + undo/redo

  public/
    icons/
    style-previews/

  package.json
  tsconfig.json
  next.config.js
```

## Key conventions (so agents don’t mess it up)

### A) AppShell everywhere

Use `app/layout.tsx` to wrap pages with `AppShell`.

### B) Editor pages are client pages

Any page that needs drag/drop, canvas, or heavy interactivity should be a client component:

* `app/.../dialogue/page.tsx` → `"use client";`
* likely also `planner` and `render` pages (depending on UI)

### C) API calls are not sprinkled everywhere

All calls go through `lib/api/endpoints.ts` and are consumed with TanStack Query hooks.

### D) Artifacts are first-class

Scene pages load artifacts and let the user select “active” versions.

---

# 2) DialogueEditor Component Tree + Zustand Store Spec

This is the implementation blueprint for the trickiest part: **bubble drag/drop + tail + resize + undo/redo**.

---

## 2.1 DialogueEditor Page Layout

### Route

`app/projects/[projectId]/stories/[storyId]/scenes/[sceneId]/dialogue/page.tsx`

### Page tree

```
DialogueEditorPage
  └─ DialogueEditorLayout
      ├─ EditorToolbar (left)
      ├─ BubbleCanvasStage (center)
      │    ├─ SceneImageLayer
      │    ├─ PanelOverlayLayer (toggle)
      │    ├─ BubbleLayer
      │    │    ├─ SpeechBubble (many)
      │    │    └─ BubbleTransformer (only for selected)
      │    └─ UIOverlayLayer (hover, guides)
      ├─ DialogueList (right, draggable source)
      └─ BubbleInspector (left-bottom or right-bottom)
```

---

## 2.2 Responsibilities per component

### `DialogueEditorLayout`

* 3-column layout
* Save button
* Keyboard shortcuts (Delete, Ctrl+Z/Ctrl+Shift+Z)

### `EditorToolbar`

* select tool
* bubble tool (speech/narration)
* tail tool (optional; can always show tail handle when selected)
* undo/redo buttons
* toggle panel overlay

### `BubbleCanvasStage`

* owns Konva Stage sizing
* converts pointer positions
* handles drop events
* zoom/pan (optional v1; can skip)

### `DialogueList`

* groups lines by panel
* each line is draggable
* dragging includes payload:

  * text
  * panel_id (optional) as hint

### `SpeechBubble`

* renders:

  * rounded rectangle
  * tail path
  * text
* supports:

  * drag move
  * click select

### `BubbleTransformer`

* Konva Transformer for resizing selected bubble
* onTransformEnd updates store with normalized geom

### `BubbleInspector`

* edit text
* type selector
* font size (optional v1)
* panel assignment dropdown (debug tool)

---

## 2.3 Zustand Store: `dialogueEditorStore`

### Store state (v1)

```ts
type Norm = number; // 0..1

export type BubbleType = "speech" | "thought" | "narration" | "sfx";

export type Bubble = {
  id: string;
  panelId: number | null;
  type: BubbleType;
  text: string;
  geom: { x: Norm; y: Norm; w: Norm; h: Norm };
  tail?: { x: Norm; y: Norm };
  style?: { fontSize?: number; bold?: boolean; fontFamily?: string };
  zIndex: number;
};

export type PanelBox = { id: number; x: Norm; y: Norm; w: Norm; h: Norm };

type ToolMode = "select" | "add_speech" | "add_narration"; // keep small for v1

type DialogueEditorState = {
  sceneId: string;
  imageUrl: string;
  panels: PanelBox[];
  showPanelOverlay: boolean;

  bubbles: Bubble[];
  selectedBubbleId: string | null;
  toolMode: ToolMode;

  // stage sizing (pixels)
  stagePx: { w: number; h: number };

  // undo/redo
  history: { past: any[]; future: any[] };

  // flags
  isDirty: boolean;
  lastSavedAt?: string;
};
```

### Store actions (v1)

```ts
type Actions = {
  init(params: { sceneId: string; imageUrl: string; panels: PanelBox[]; bubbles?: Bubble[] }): void;

  setToolMode(mode: ToolMode): void;
  togglePanelOverlay(): void;

  setStageSize(px: { w: number; h: number }): void;

  selectBubble(id: string | null): void;

  addBubbleFromDrop(params: { text: string; dropNx: number; dropNy: number; panelHintId?: number | null }): void;

  moveBubble(params: { id: string; nx: number; ny: number }): void;
  resizeBubble(params: { id: string; nw: number; nh: number; nx?: number; ny?: number }): void;

  moveTail(params: { id: string; tailNx: number; tailNy: number }): void;

  editBubbleText(params: { id: string; text: string }): void;
  setBubblePanel(params: { id: string; panelId: number | null }): void;

  deleteSelected(): void;

  undo(): void;
  redo(): void;

  markSaved(timestampIso: string): void;
};
```

---

## 2.4 Core Algorithms (must implement)

### A) Panel hit-testing

Given drop point `(nx, ny)` find panel:

* first panel where `x <= nx <= x+w` and `y <= ny <= y+h`
* if multiple (rare), pick smallest area

### B) Default bubble sizing heuristic

Simple, works:

* `w = clamp(0.18 + 0.006 * text.length, 0.18, 0.42)`
* `h = clamp(0.10 + 0.02 * estimatedLines, 0.10, 0.26)`
* `estimatedLines = ceil(text.length / 22)` (tune)

### C) Clamp bubble inside panel

If bubble has `panelId`, clamp `(x,y)` so bubble remains within panel with padding:

* `pad = 0.02`
* `x ∈ [panel.x + pad, panel.x + panel.w - bubble.w - pad]`
* same for y

### D) Normalized <-> pixel conversion

* `px = nx * stageW`
* `nx = px / stageW`

Always store normalized in Zustand; Konva uses pixels.

---

## 2.5 Undo/Redo (practical approach)

### Command-based history

Store commands like:

* `{ type: "ADD", bubble }`
* `{ type: "MOVE", id, from, to }`
* `{ type: "RESIZE", id, from, to }`
* `{ type: "EDIT_TEXT", id, from, to }`
* `{ type: "MOVE_TAIL", id, from, to }`
* `{ type: "DELETE", bubble }`

Undo applies inverse command.

This is much more reliable than snapshotting the entire state.

---

## 2.6 API integration (for save/load)

### Load on entry

* `GET /v1/scenes/{sceneId}/dialogue`

  * if none, start empty

### Save

* If no layer exists: `POST /v1/scenes/{sceneId}/dialogue`
* Else: `PUT /v1/dialogue/{layerId}`

Store `layerId` in sceneStore or editorStore.

### What to send

* full bubble list (normalized), sorted by `zIndex`

---

## 2.7 Acceptance Criteria (Dialogue Editor)

MVP of editor is complete when:

* drag dialogue line → bubble appears
* click bubble → select + resize handles
* bubble move updates saved state
* tail moves and persists
* save → reload restores identical placement
* undo/redo works for add/move/edit/delete

---

Perfect — I’ll continue **as if this is a handoff document to a coding agent**, filling in the **remaining frontend pieces needed to actually build and ship** without ambiguity.

What follows is **pure implementation guidance**, not design discussion.

---

# Frontend Development Continuation

## Agent-Facing Implementation Guide (Final Sections)

This document assumes:

* **Next.js (App Router)**
* **React + TypeScript**
* **Tailwind CSS**
* **Zustand**
* **TanStack Query**
* **react-konva**

You can give this directly to a coding agent.

---

# F7. Global State Architecture (Critical)

## Why this matters

Without strict separation, frontend code becomes unmaintainable very fast.

---

## F7.1 State Layers (Do NOT mix)

### 1️⃣ Server State (TanStack Query)

**What belongs here**

* projects
* stories
* scenes
* artifacts (intent, plan, layout, semantics, render_spec, render_result)
* dialogue layers
* exports
* jobs

**Rules**

* NEVER mutate server state directly
* Always refetch or invalidate after mutations
* Cache by IDs

---

### 2️⃣ UI / Editor State (Zustand)

**What belongs here**

* currently selected project/story/scene
* active artifact IDs
* editor-only state (selection, zoom, drag)
* dialogue editor bubbles + history
* UI toggles

**Rules**

* This state can be reset safely
* This state is never the source of truth for persistence

---

## F7.2 Zustand Stores (Required)

### `sceneStore.ts`

Handles scene-wide context.

```ts
type SceneStore = {
  sceneId: string | null;

  activeArtifacts: {
    intentId?: string;
    panelPlanId?: string;
    layoutId?: string;
    semanticsId?: string;
    renderSpecId?: string;
    renderResultId?: string;
  };

  setScene(sceneId: string): void;
  setActiveArtifact(type: keyof SceneStore["activeArtifacts"], id: string): void;
};
```

---

### `dialogueEditorStore.ts`

Already specified in detail earlier — this remains **isolated**.

---

### `projectStore.ts`

Lightweight navigation state.

```ts
type ProjectStore = {
  projectId?: string;
  storyId?: string;

  setProject(id: string): void;
  setStory(id: string): void;
};
```

---

# F8. API Layer (Frontend-Side)

## F8.1 API Client Wrapper

### `lib/api/client.ts`

```ts
export async function api<T>(
  url: string,
  options?: RequestInit
): Promise<T> {
  const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}${url}`, {
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    ...options,
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.message || "API error");
  }

  return res.json();
}
```

---

## F8.2 Endpoint Functions (Typed)

### `lib/api/endpoints.ts`

```ts
export const getSceneArtifacts = (sceneId: string) =>
  api<Artifact[]>(`/v1/scenes/${sceneId}/artifacts`);

export const generatePanelPlan = (sceneId: string) =>
  api(`/v1/scenes/${sceneId}/generate/panel-plan`, { method: "POST" });

export const renderScene = (sceneId: string) =>
  api(`/v1/scenes/${sceneId}/generate/render`, { method: "POST" });

export const saveDialogueLayer = (sceneId: string, payload: DialogueLayer) =>
  api(`/v1/scenes/${sceneId}/dialogue`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
```

---

## F8.3 Query Keys (Consistency)

### `lib/query/keys.ts`

```ts
export const qk = {
  projects: ["projects"],
  story: (id: string) => ["story", id],
  scenes: (storyId: string) => ["scenes", storyId],
  artifacts: (sceneId: string) => ["artifacts", sceneId],
  dialogue: (sceneId: string) => ["dialogue", sceneId],
};
```

---

# F9. Scene Planner Implementation Notes

## Artifact Timeline (Important UX)

### `ArtifactTimeline.tsx`

* Displays:

  * Intent v1, v2
  * Panel Plan v1, v2
  * Layout v1
  * Semantics v1
* Clicking a version:

  * updates `sceneStore.activeArtifacts`
* Latest version auto-selected on load

**Rule**

> Never auto-overwrite active artifacts without user action.

---

## Layout Preview

* Render using simple `<div>` boxes
* Use normalized coordinates
* Clicking a panel highlights corresponding semantic card

---

# F10. Scene Renderer Implementation Notes

## Render History Strip

* Thumbnails fetched from `render_result.image_url`
* Clicking sets active render
* Active render highlighted

## Regenerate Button

* Calls regenerate endpoint
* DOES NOT reset dialogue layer
* DOES NOT reset plan artifacts

---

# F11. Dialogue Editor – Integration Checklist

Before coding starts, agent must confirm:

* [ ] Stage size tracked and normalized
* [ ] All bubble data stored normalized
* [ ] Undo/redo implemented via command stack
* [ ] Panel hit-test implemented
* [ ] Save/load round-trip tested
* [ ] Bubble selection is single-source-of-truth
* [ ] Deleting bubble cleans selection state

---

# F12. Export UI Integration

## Export Page Flow

1. User selects episode
2. Clicks “Export”
3. Job starts
4. Poll `/v1/jobs/{jobId}`
5. Show progress bar
6. Show download button on completion

---

# F13. Error Handling & UX Rules

### Global rules

* All API errors show toast
* All destructive actions require confirmation
* Long operations show spinner + disable buttons

### Specific rules

* Cannot render scene if:

  * no approved character refs (for main characters)
* Cannot export episode if:

  * any scene missing approved render

---

# F14. Frontend Testing Strategy

## Unit tests (Jest / Vitest)

* bubble normalization math
* panel hit-test logic
* undo/redo command inverses

## Manual QA checklist (agent must run)

* Create story → scene → plan → render
* Regenerate image without losing dialogue
* Save dialogue → reload page → verify
* Export episode → verify order and bubbles

---

# F15. Frontend Definition of Done (Agent Contract)

Frontend work is complete when:

✅ User completes full workflow without dev tools
✅ No bubble data loss on refresh
✅ Regeneration never destroys planning or dialogue
✅ UI matches artifact state (no phantom state)
✅ Agent can explain where every piece of data lives

---

# Final Notes for Agent (Important)

Tell the agent explicitly:

> “This is a professional canvas editor + planning UI, not a toy app. Follow normalized coordinates, artifact versioning, and separation of server/UI state strictly.”

If they follow this doc, they **will not paint themselves into a corner**.

---

## If you want next (optional)

I can still provide:

* a **day-by-day frontend sprint plan**
* a **checklist for backend ↔ frontend contract testing**
* or a **short README.md** for onboarding new engineers/agents

Just say the word.
