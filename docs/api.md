# Ssuljaengi API Documentation (v1)

This document complements the auto-generated OpenAPI docs (`/docs`) with:
- a workflow guide (how to generate a webtoon from story text)
- a resource hierarchy overview
- practical request/response examples per endpoint group
- an error reference (including request IDs)
- usage and rate-limiting guidelines

Base path: `/v1`

## Quick Links

- OpenAPI UI (Swagger): `/docs`
- OpenAPI schema: `/openapi.json`
- Health: `/health`
- Prometheus metrics: `/metrics`

## Resource Hierarchy

Primary hierarchy:

`Project -> Story -> Scene -> Artifact`

Related resources:
- `Story -> Episode` (an ordered list of scenes)
- `Story -> Characters` (characters are project-scoped but linked to stories)
- `Character -> Reference Images` (face/body refs; used for consistency)
- `Exports` (downloadable bundles for a scene or episode)
- `Jobs` (async execution for long-running operations)

## Common Conventions

### IDs
All `*_id` values are UUIDs.

### Request/Response Format
Requests and responses are JSON unless documented otherwise.

### Request IDs
Every request gets an `x-request-id`:
- Provide your own `x-request-id` header to correlate logs across services.
- If omitted, the server generates one.
- Responses echo `x-request-id`.

### Async Jobs (202 Accepted)
Endpoints ending with `_async` return `202 Accepted` and a `JobStatusRead`.
- Poll `GET /v1/jobs/{job_id}` until `status` becomes `succeeded` or `failed`.
- `progress` and `result` are JSON objects (shape depends on job type).

### Media URLs
Some responses include `image_url` / `output_url`. These are served under `MEDIA_URL_PREFIX` (defaults to `/media`).

## Workflow Guide: Generate A Webtoon From Story Text

This is the recommended API-first flow.

### 1) Create a project
```bash
curl -sS -X POST http://127.0.0.1:8000/v1/projects \
  -H "Content-Type: application/json" \
  -d '{"name":"My Project"}'
```

### 2) Create a story in the project
```bash
curl -sS -X POST http://127.0.0.1:8000/v1/projects/$PROJECT_ID/stories \
  -H "Content-Type: application/json" \
  -d '{
    "title":"Blue Couch Reunion",
    "default_story_style":"romance",
    "default_image_style":"soft_webtoon"
  }'
```

### 3) Generate a blueprint (scenes + characters)

Async (recommended for anything non-trivial):
```bash
curl -sS -X POST http://127.0.0.1:8000/v1/stories/$STORY_ID/generate/blueprint_async \
  -H "Content-Type: application/json" \
  -d '{
    "source_text":"<full story text>",
    "max_scenes":6,
    "panel_count":3,
    "max_characters":6,
    "generate_render_spec": true,
    "allow_append": false
  }'
```

Poll:
```bash
curl -sS http://127.0.0.1:8000/v1/jobs/$JOB_ID
```

If you prefer synchronous generation (risk: timeouts on long stories), use:
- `POST /v1/stories/{story_id}/generate/blueprint`

### 4) List scenes for the story
```bash
curl -sS http://127.0.0.1:8000/v1/stories/$STORY_ID/scenes
```

### 5) Generate full pipeline per scene (planning + render)

Async (recommended):
```bash
curl -sS -X POST http://127.0.0.1:8000/v1/scenes/$SCENE_ID/generate/full_async \
  -H "Content-Type: application/json" \
  -d '{
    "panel_count": 3,
    "style_id": "soft_webtoon",
    "genre": "romance"
  }'
```

You can also do it in two steps:
- `POST /v1/scenes/{scene_id}/plan`
- `POST /v1/scenes/{scene_id}/render`

### 6) Fetch rendered artifacts (images) for a scene
```bash
curl -sS http://127.0.0.1:8000/v1/scenes/$SCENE_ID/renders
```

### 7) Export

Export a single scene:
```bash
curl -sS -X POST http://127.0.0.1:8000/v1/scenes/$SCENE_ID/export
```

Export an episode (recommended for multi-scene output):
- create an episode for a story
- order scenes in the episode
- export the episode

## Endpoint Reference (By Tag)

The models referenced below live in `app/api/v1/schemas.py`.

### Projects

- `POST /v1/projects` -> `ProjectRead` (body: `ProjectCreate`)
- `GET /v1/projects` -> `list[ProjectRead]`
- `DELETE /v1/projects/{project_id}` -> 204

Example:
```bash
curl -sS http://127.0.0.1:8000/v1/projects
```

### Stories

- `POST /v1/projects/{project_id}/stories` -> `StoryRead` (body: `StoryCreate`)
- `GET /v1/projects/{project_id}/stories` -> `list[StoryRead]`
- `GET /v1/stories/{story_id}` -> `StoryRead`
- `POST /v1/stories/{story_id}/scenes/auto-chunk` -> `list[SceneRead]` (body: `SceneAutoChunkRequest`)
- `POST /v1/stories/{story_id}/generate/blueprint` -> `StoryGenerateResponse` (body: `StoryGenerateRequest`)
- `POST /v1/stories/{story_id}/generate/blueprint_async` -> `JobStatusRead` (body: `StoryGenerateRequest`, returns 202)
- `GET /v1/stories/{story_id}/progress` -> `StoryProgressRead`
- `POST /v1/stories/{story_id}/set-style-defaults` -> `StoryRead` (body: `StorySetStyleDefaultsRequest`)

Blueprint request example (`StoryGenerateRequest`):
```json
{
  "source_text": "Long story text...",
  "max_scenes": 6,
  "panel_count": 3,
  "style_id": "soft_webtoon",
  "max_characters": 6,
  "generate_render_spec": true,
  "allow_append": false,
  "require_hero_single": false
}
```

### Scenes

- `POST /v1/stories/{story_id}/scenes` -> `SceneRead` (body: `SceneCreate`)
- `GET /v1/stories/{story_id}/scenes` -> `list[SceneRead]`
- `GET /v1/scenes/{scene_id}` -> `SceneRead`
- `POST /v1/scenes/{scene_id}/planning/lock` -> `SceneRead` (body: `ScenePlanningLockRequest`)
- `POST /v1/scenes/{scene_id}/set-style` -> `SceneRead` (body: `SceneSetStyleRequest`)
- `POST /v1/scenes/{scene_id}/set-environment` -> `SceneRead` (body: `SceneSetEnvironmentRequest`)
- `GET /v1/scenes/{scene_id}/renders` -> `list[ArtifactRead]`

### Generation (scene pipeline)

- `POST /v1/scenes/{scene_id}/plan` -> `ScenePlanResponse`
- `POST /v1/scenes/{scene_id}/render` -> `SceneRenderResponse`
- `GET /v1/scenes/{scene_id}/status` -> `SceneWorkflowStatusResponse`
- `POST /v1/scenes/{scene_id}/generate/full` -> `GenerateFullResponse`
- `POST /v1/scenes/{scene_id}/generate/full_async` -> `JobStatusRead` (returns 202)

### Internal Generation (debug / unstable)

These are "node-level" endpoints useful for debugging and UI iteration. They are not stable.

All return `{"artifact_id":"<uuid>"}`:
- `POST /v1/internal/scenes/{scene_id}/generate/scene-intent`
- `POST /v1/internal/scenes/{scene_id}/generate/panel-plan`
- `POST /v1/internal/scenes/{scene_id}/generate/panel-plan/normalize`
- `POST /v1/internal/scenes/{scene_id}/generate/layout`
- `POST /v1/internal/scenes/{scene_id}/generate/panel-semantics`
- `POST /v1/internal/scenes/{scene_id}/generate/render-spec`
- `POST /v1/internal/scenes/{scene_id}/generate/render`
- `POST /v1/internal/scenes/{scene_id}/evaluate/qc`
- `POST /v1/internal/scenes/{scene_id}/evaluate/blind-test`

### Artifacts

- `GET /v1/scenes/{scene_id}/artifacts` -> `list[ArtifactRead]`
- `GET /v1/artifacts/{artifact_id}` -> `ArtifactRead`

### Styles

- `GET /v1/styles/story` -> `list[StyleItemRead]`
- `GET /v1/styles/image` -> `list[StyleItemRead]`

### Characters

Characters are project-scoped, and linked to a story via `StoryCharacter`.

- `POST /v1/stories/{story_id}/characters` -> `CharacterRead` (body: `CharacterCreate`)
- `GET /v1/stories/{story_id}/characters` -> `list[CharacterRead]`
- `PATCH /v1/characters/{character_id}` -> `CharacterRead` (body: `CharacterUpdate`)
- `POST /v1/characters/{character_id}/approve` -> `CharacterRead`
- `POST /v1/characters/{character_id}/refs` -> `CharacterRefRead` (body: `CharacterRefCreate`)
- `GET /v1/characters/{character_id}/refs` -> `list[CharacterRefRead]`
- `POST /v1/characters/{character_id}/approve-ref` -> `CharacterRefRead` (body: `CharacterApproveRefRequest`)
- `POST /v1/characters/{character_id}/set-primary-ref` -> `CharacterRefRead` (body: `CharacterSetPrimaryRefRequest`)
- `DELETE /v1/characters/{character_id}/refs/{reference_image_id}` -> `{"deleted": true}`
- `POST /v1/characters/{character_id}/generate-refs` -> `CharacterGenerateRefsResponse` (body: `CharacterGenerateRefsRequest`)

### Character Variants

- `POST /v1/stories/{story_id}/characters/{character_id}/variants` -> `CharacterVariantRead` (body: `CharacterVariantCreate`)
- `GET /v1/stories/{story_id}/characters/{character_id}/variants` -> `list[CharacterVariantRead]`
- `POST /v1/stories/{story_id}/characters/{character_id}/variants/{variant_id}/activate` -> `CharacterVariantRead` (body: `CharacterVariantActivate`)
- `GET /v1/stories/{story_id}/character-variant-suggestions` -> `list[CharacterVariantSuggestionRead]`
- `POST /v1/stories/{story_id}/character-variant-suggestions/refresh` -> `list[CharacterVariantSuggestionRead]`
- `POST /v1/stories/{story_id}/character-variant-suggestions/generate` -> `list[CharacterVariantGenerationResult]`

### Dialogue

- `POST /v1/scenes/{scene_id}/dialogue` -> `DialogueLayerRead` (body: `DialogueLayerCreate`)
- `PUT /v1/dialogue/{dialogue_id}` -> `DialogueLayerRead` (body: `DialogueLayerUpdate`)
- `GET /v1/scenes/{scene_id}/dialogue` -> `DialogueLayerRead`
- `GET /v1/scenes/{scene_id}/dialogue/suggestions` -> `DialogueSuggestionsRead`

### Environments

- `POST /v1/environments` -> `EnvironmentRead` (body: `EnvironmentCreate`)
- `GET /v1/environments/{environment_id}` -> `EnvironmentRead`
- `POST /v1/environments/{environment_id}/promote` -> `EnvironmentRead` (body: `EnvironmentPromoteRequest`)

### Layers

Layers are a generic per-scene "UI layer" container (e.g. dialogue bubbles, overlays).

- `POST /v1/scenes/{scene_id}/layers` -> `LayerRead` (body: `LayerCreate`)
- `PUT /v1/layers/{layer_id}` -> `LayerRead` (body: `LayerUpdate`)
- `GET /v1/scenes/{scene_id}/layers` -> `list[LayerRead]`

### Jobs

- `GET /v1/jobs/{job_id}` -> `JobStatusRead`
- `POST /v1/jobs/{job_id}/cancel` -> `JobStatusRead`

### Review

- `POST /v1/scenes/{scene_id}/review/regenerate` -> `{"artifact_id":"<uuid>"}` (render regeneration)
- `POST /v1/scenes/{scene_id}/review/approve` -> `{"artifact_id":"<uuid>"}` (approve a render_result artifact)

### Episodes

- `POST /v1/stories/{story_id}/episodes` -> `EpisodeRead` (body: `EpisodeCreate`)
- `GET /v1/stories/{story_id}/episodes` -> `list[EpisodeRead]`
- `GET /v1/episodes/{episode_id}` -> `EpisodeRead`
- `POST /v1/episodes/{episode_id}/scenes` -> `EpisodeRead` (body: `EpisodeScenesUpdate`)
- `POST /v1/episodes/{episode_id}/set-style` -> `EpisodeRead` (body: `EpisodeSetStyleRequest`)
- `GET /v1/episodes/{episode_id}/assets` -> `list[EpisodeAssetRead]`
- `POST /v1/episodes/{episode_id}/assets` -> `EpisodeAssetRead` (body: `EpisodeAssetCreate`)
- `DELETE /v1/episodes/{episode_id}/assets/{asset_id}` -> `dict`

### Episode Planning

- `POST /v1/episodes/{episode_id}/generate/plan` -> `EpisodePlanResponse`

### Exports

Exports support scene- and episode-level bundles and optional video generation.

- `POST /v1/scenes/{scene_id}/export` -> `ExportRead`
- `POST /v1/episodes/{episode_id}/export` -> `ExportRead`
- `GET /v1/exports/{export_id}` -> `ExportRead`
- `GET /v1/exports/{export_id}/download` -> file download
- `POST /v1/exports/{export_id}/finalize` -> `ExportRead`
- `POST /v1/exports/{export_id}/generate-video` -> `ExportRead`

### Gemini (raw helpers)

These endpoints are thin wrappers for testing Gemini configuration.

- `POST /v1/gemini/generate-text` -> `{"text":"..."}`
- `POST /v1/gemini/generate-image` -> `{"image_id":"...","image_url":"...","mime_type":"..."}`

## Error Reference

### Common Status Codes
- `200` / `201`: Success
- `202`: Accepted (async job started)
- `204`: Success (no body)
- `400`: Invalid request state or invalid business input (e.g. unknown style id)
- `404`: Resource not found
- `422`: Validation error (Pydantic request body/path/query validation)
- `500`: Server misconfiguration (e.g. Gemini not configured)
- `502`: Downstream runtime error (e.g. Gemini call failure surfaced as RuntimeError)

### Error Body Shapes

`HTTPException` responses follow FastAPI defaults:
```json
{"detail":"story not found"}
```

Certain unhandled exceptions are mapped to a request-ID-friendly body:
```json
{"detail":"<message>","request_id":"<x-request-id>"}
```

Validation errors (422) are FastAPI defaults; example:
```json
{
  "detail": [
    {
      "type": "missing",
      "loc": ["body", "source_text"],
      "msg": "Field required",
      "input": {}
    }
  ]
}
```

## Rate Limiting and Usage Guidelines

The API does not enforce rate limits by default.

Operational guidance:
- Treat generation endpoints as expensive; prefer `_async` + polling.
- Apply rate limiting at your gateway (e.g. N requests/min per user and a stricter limit for generation).
- Respect Gemini provider quotas; spikes can trigger retries/circuit breaker behavior in `app/services/vertex_gemini.py`.
- Keep `x-request-id` stable for multi-call workflows so logs are easy to correlate.

## Authentication

The API currently has no authentication/authorization layer enabled.

Production deployment recommendations:
- Put the service behind an API gateway with authentication (OIDC/JWT) and per-user rate limiting.
- Add an application-level auth dependency (FastAPI `Depends`) if you need per-tenant data isolation.
