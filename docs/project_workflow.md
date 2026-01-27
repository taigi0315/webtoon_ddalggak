# Webtoon Workflow - One-Page Testing Checklist

This is a minimal end-to-end checklist for testing the current app (backend + frontend).

## Prereqs
- Backend running: `make dev-back`
- Frontend running: `make dev-front`
- API base URL: `http://127.0.0.1:8000`

## Valid style IDs
Story styles: `default`, `romance`, `horror`, `comedy`, `action`, `slice_of_life`
Image styles: `default`, `soft_webtoon`, `clean_lineart`, `dramatic_lighting`, `flat_color`

---

## Step 1 - Create Project (UI)
Page: `/projects`
- Click "New Project"
- Name: `Test Project A`
Expected:
- Project appears in list
- Backend logs show `POST /v1/projects 200`

Alternative (API):
```
curl -X POST http://127.0.0.1:8000/v1/projects \
  -H "Content-Type: application/json" \
  -d '{"name":"Test Project A"}'
```

---

## Step 2 - Create Story (UI)
Page: `/studio/story`
- Select the project from dropdown
- Story title: `Blue Couch Reunion`
- Story style: `romance`
- Image style: `soft_webtoon`
- Click "Create Story"
Expected:
- Status shows `Story ready: <story_id>`
- Story appears in the story dropdown
- Backend logs show `POST /v1/projects/{project_id}/stories 200`

---

## Step 3 - Create Scene (UI)
Same page: `/studio/story`
- Select the story in the dropdown
- Scene text:
  "Min-ji enters the room looking worried. Ji-hoon turns from the window. They hesitate before speaking."
- Click "Create Scene"
Expected:
- Status shows `Scene ready: <scene_id>`
- Scene list shows the scene ID
- Backend logs show `POST /v1/stories/{story_id}/scenes 200`

---

## Step 4 - Open Scene Planner (UI)
- Click "Open" on the scene card
Expected:
- Navigates to `/studio/planner?scene_id=...`
- Scene text loads

---

## Step 5 - Generate Intent
In `/studio/planner`
- Click "Generate Intent"
Expected:
- Intent summary appears
- Backend logs show `POST /v1/scenes/{scene_id}/generate/scene-intent 200`

---

## Step 6 - Generate Plan
- (Optional) Panel count: 3
- Click "Generate Plan"
Expected:
- Plan chips appear (grammar ids)
- Backend logs show `POST /v1/scenes/{scene_id}/generate/panel-plan 200`

---

## Step 7 - Normalize Plan (optional)
- Click "Normalize"
Expected:
- Backend logs show `POST /v1/scenes/{scene_id}/generate/panel-plan/normalize 200`

---

## Step 8 - Generate Layout
- Click "Generate Layout"
Expected:
- Layout preview shows panel boxes
- Backend logs show `POST /v1/scenes/{scene_id}/generate/layout 200`

---

## Step 9 - Generate Semantics
- Click "Generate Semantics"
Expected:
- Panel descriptions appear
- Backend logs show `POST /v1/scenes/{scene_id}/generate/panel-semantics 200`

---

## Known current limitations
- "Create Story" does not auto-split long text into multiple scenes.
- Rendering, dialogue editor, and export are not fully wired in the UI yet.

## Quick troubleshooting
- If dropdowns are empty: verify `/v1/styles/story` and `/v1/styles/image` return 200.
- If "Generate Plan" fails: run "Generate Intent" first.
- If UI says "Unable to load projects": verify backend is running and CORS is enabled.
