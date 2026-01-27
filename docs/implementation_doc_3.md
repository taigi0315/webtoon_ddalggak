Webtoon Scene Image Generator
Technical Design Document – Phase 3 Implementation Plan (Production Grade)

24. Phase 3 Objectives
Phase 3 turns the tool into an end-to-end webtoon production system:
Generate and manage episodes (multiple scenes, ordered)
Full lettering pipeline (dialogue bubbles, narration, SFX)
Production-grade export (Webtoon formats, strips, zip packages)
Strong version history, rollback, and re-render workflows
Advanced quality analytics and pacing control
Optional: multi-agent modular pipeline (director/critic/etc.)
Phase 3 is about scale and publishing, not “better prompts.”

25. Phase 3 Scope Additions
Add
Episode builder + pacing controls
Dialogue + SFX + narration as first-class layers
Export compositor (server side) + templates
Asset library (characters/environments/styles) across episodes
Version history UI and branching model
Batch generation jobs (queue)
QC metrics & dashboards
Do NOT add (unless you decide later)
multi-panel-to-single-panel multi-render strategy
control signals / pose nets
collaborative real-time editing

26. Phase 3 Milestones

Milestone 3.1 — Episode Domain Model & APIs
(Foundational for everything else)
Goal
Support ordered sets of scenes with metadata and reusable assets.
Backend deliverables
New tables:
episodes
episode_scenes (ordering)
episode_assets (characters/environments/styles pinned for the episode)
exports (export jobs + outputs)
Episode schema:
{
  "episode_id": "uuid",
  "story_id": "uuid",
  "title": "Episode 1",
  "scene_ids_ordered": ["uuid", "uuid"],
  "default_story_style": "romance",
  "default_image_style": "soft_webtoon",
  "status": "draft | producing | final"
}

APIs
POST /v1/stories/{story_id}/episodes
GET /v1/episodes/{episode_id}
POST /v1/episodes/{episode_id}/scenes (add/reorder/remove)
POST /v1/episodes/{episode_id}/set-style
GET /v1/episodes/{episode_id}/assets
Acceptance criteria
You can create an episode, attach scenes, reorder them, and persist it.
Episode has default styles that scenes can inherit/override.

Milestone 3.2 — Episode Planner (Batch Planning & Consistency)
(Scaling planning across scenes)
Goal
Run planning across multiple scenes while enforcing continuity.
Backend deliverables
Add episode-level orchestration:
batch generate scene intents
batch generate panel plans
enforce continuity constraints at episode level:
avoid repeating grammar rhythms every scene
enforce environment anchor promotion rules
enforce character ref readiness gating
APIs
POST /v1/episodes/{episode_id}/generate/plan
Options: scenes=all|subset, mode=draft|final
Acceptance criteria
One API call can plan all scenes and create artifacts per scene.
Scenes are consistent in style and character identity usage.

Milestone 3.3 — Lettering System v2 (Dialogue + Narration + SFX)
(Beyond MVP dialogue bubbles)
Goal
Make lettering production-ready and exportable.
Deliverables
Introduce three layer types:
dialogue_layer
narration_layer
sfx_layer
Each layer contains objects:
{
  "layer_type": "dialogue",
  "objects": [
    {
      "id": "uuid",
      "panel_id": 2,
      "type": "speech_bubble | thought_bubble | box | sfx_text",
      "text": "string",
      "style": { "font": "default", "weight": "normal" },
      "geometry": { "x": 0.5, "y": 0.2, "w": 0.25, "h": 0.12 },
      "tail": { "x": 0.55, "y": 0.35 },
      "z_index": 3
    }
  ]
}

APIs
POST /v1/scenes/{scene_id}/layers
PUT /v1/layers/{layer_id}
GET /v1/scenes/{scene_id}/layers
Acceptance criteria
Users can author dialogue/narration/SFX separately.
Layers survive image regeneration (they reattach to panel layout).

Milestone 3.4 — Server-side Compositor & Export Engine
(Publishing-grade output)
Goal
Generate final images (scene + layers) in required formats.
Deliverables
A compositor service that:
takes render_result image + layers
draws text bubbles with consistent typography
supports “Webtoon strip export”
produces:
combined scene image(s)
per-episode zip
optional JSON manifest
Export outputs:
scene PNG/JPG with bubbles
episode package zip
manifest:
{
  "episode_id": "uuid",
  "scenes": [
    { "scene_id": "uuid", "final_image_url": "..." }
  ]
}

APIs
POST /v1/episodes/{episode_id}/export
GET /v1/exports/{export_id}
GET /v1/exports/{export_id}/download
POST /v1/exports/{export_id}/finalize (manual stub)
Temporary stub (Phase 2.9)
POST /v1/scenes/{scene_id}/export (returns queued export job without compositor)
Acceptance criteria
Export produces a deterministic package matching episode ordering.
Visual quality of text is consistent and crisp.

Milestone 3.5 — Version History & Branching (Creator Workflow)
(Professional iteration model)
Goal
Support rollback and branching of scene artifacts and renders.
Deliverables
Artifact graph UI/logic:
each artifact already has parent_id
add “branch labels”:
branch: "main" | "alt-a" | "alt-b"
Add endpoints:
POST /v1/scenes/{scene_id}/branches
POST /v1/artifacts/{artifact_id}/tag
POST /v1/scenes/{scene_id}/restore (set “active artifact pointer”)
Introduce “active pointers” per scene:
scene.active_panel_plan_id
scene.active_layout_id
scene.active_semantics_id
scene.active_render_spec_id
scene.active_render_result_id
Acceptance criteria
User can switch between alternative plans/renders without data loss.
Restoring a prior version is instant (no recompute).

Milestone 3.6 — Async Jobs + Queue
(Scaling and reliability)
Goal
Batch generation and export must be asynchronous.
Deliverables
job queue (Celery/RQ/Arq) + Redis
job types:
batch plan
batch render
export
job status model:
queued / running / succeeded / failed
progress: current/total
APIs
POST /v1/jobs (internal)
GET /v1/jobs/{job_id}
Acceptance criteria
Episode export and batch rendering can run without blocking requests.
Users can see progress and retry failed jobs.

Milestone 3.7 — Quality Analytics & Pacing Dashboard
(Episode-level quality control)
Goal
Provide actionable quality signals at scale.
Metrics
blind test per scene aggregated to episode
redundancy score (grammar pattern repetition)
dialogue reliance score (difference between dialogue on/off)
scene pacing (panel count vs beat count)
“variety score” (camera variety proxy from grammar)
APIs
GET /v1/episodes/{episode_id}/analytics
GET /v1/scenes/{scene_id}/analytics
Acceptance criteria
You can identify weak scenes quickly (ranked list).
Analytics suggest specific actions (re-panel, add object_focus, etc.)

Milestone 3.8 — Optional Multi-Agent Modularization
(Only if needed for maintainability)
Goal
Make it easier to debug and improve planning over time.
Agents (internal modules):
Story Writer
Director (panel plan)
Continuity Editor
Prompt Compiler
Critic (blind test + QC)
This is an internal refactor:
each agent has prompt templates + structured IO
better traceability
Acceptance criteria
Each module can be tested independently with recorded artifacts.

27. Phase 3 Build Order (Recommended)
Episode domain model + APIs
Export engine (compositor)
Layer system v2 (dialogue/narration/SFX)
Version pointers + branching
Async jobs + queue
Episode planner batch ops
Analytics dashboard
Optional multi-agent refactor
This order delivers value early (episodes + export), then adds scale.

28. Phase 3 Definition of Done
Phase 3 is done when:
✅ Users can build full episodes (scenes ordered)
✅ Lettering is editable and exportable
✅ Export produces publish-ready assets
✅ Versioning supports rollback and alternatives
✅ Batch generation works asynchronously
✅ Analytics highlight weak scenes & pacing issues
At that point, you have a complete webtoon creation pipeline.

If you want, I can now convert Phase 3 into:
Epics + user stories (copy into Jira/GitHub)
DB migration plan (tables + relationships)
Export compositor spec (fonts, bubble rendering, image pipeline)
