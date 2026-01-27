Below is a **bottom-up implementation plan** for **“Webtoon Scene Image Generator — TDD v1 MVP”** that you can hand to an agent. It’s organized as **milestones**, each with **deliverables, tasks, and acceptance criteria**, and it maps directly to the APIs and artifacts we defined.

Assumptions (MVP-aligned):

* Backend: **Python** (FastAPI recommended)  
* Orchestration: **LangGraph**  
* LLM \+ Image: **Gemini Flash 2.5** (text \+ image)  
* Storage: Postgres \+ S3/GCS (or local filesystem in dev)  
* Frontend out of scope for this plan (we’ll do after)

---

# **Implementation Plan — MVP (Backend \+ Graph)**

## **Milestone 0 — Repo & Foundations (Day 0–1)**

### **Deliverables**

* Running service skeleton  
* CI/lint/test scaffolding  
* Local dev environment

### **Tasks**

1. Create repo structure:  
   * `app/` (FastAPI)  
   * `app/db/` (models \+ migrations)  
   * `app/services/` (gemini, artifacts, orchestration)  
   * `app/graphs/` (langgraph nodes)  
2. Add tooling:  
   * `ruff` (lint), `black` (format), `mypy`  
   * `pytest`  
3. Add config:  
   * `.env` support  
   * settings object (pydantic-settings)

### **Acceptance criteria**

* `uvicorn app.main:app` runs  
* `/health` returns ok  
* Tests run in CI

---

## **Milestone 1 — Data Model \+ Artifact Store (Day 1–3)**

### **Deliverables**

* Postgres schema \+ migrations  
* Artifact versioning works end-to-end

### **Tables (minimum)**

* `projects`  
* `stories`  
* `scenes`  
* `characters`  
* `character_reference_images` (metadata only for MVP)  
* `artifacts` (the core)  
* `images` (generated images \+ URLs)

### **Artifact table shape (recommended)**

* `artifact_id` (uuid pk)  
* `scene_id` (fk)  
* `type` (enum/string)  
* `version` (int)  
* `parent_id` (nullable fk to artifacts)  
* `payload` (jsonb)  
* `created_at`

### **Tasks**

1. Implement SQLAlchemy models \+ alembic migrations  
2. Implement `ArtifactService`:  
   * `create_artifact(scene_id, type, payload, parent_id=None)`  
   * `list_artifacts(scene_id, type=None)`  
   * `get_artifact(artifact_id)`  
3. Versioning rules:  
   * if creating a new artifact of same type for same scene:  
     * compute next version  
     * set parent\_id to previous artifact of that type (optional but recommended)

### **Acceptance criteria**

* Create scene → create 3 artifacts versions → list shows correct order/version  
* Payload round-trips with no loss

---

## **Milestone 2 — Core CRUD APIs (Day 3–5)**

### **Deliverables**

* REST endpoints for:  
  * projects, stories, scenes  
  * characters  
  * artifact retrieval/listing

### **Tasks**

1. Implement endpoints:  
   * `POST /v1/projects`  
   * `GET /v1/projects`  
   * `POST /v1/projects/{project_id}/stories`  
   * `GET /v1/stories/{story_id}`  
   * `POST /v1/stories/{story_id}/scenes`  
   * `GET /v1/scenes/{scene_id}`  
   * `POST /v1/stories/{story_id}/characters`  
   * `GET /v1/stories/{story_id}/characters`  
   * `GET /v1/scenes/{scene_id}/artifacts?type=...`  
   * `GET /v1/artifacts/{artifact_id}`  
2. Add request/response models (Pydantic)  
3. Add basic validation (ids exist, etc.)

### **Acceptance criteria**

* Can create a project → story → scene  
* Can create a character profile  
* Can store & retrieve artifacts

---

## **Milestone 3 — Gemini Service (Text \+ Image) (Day 5–7)**

### **Deliverables**

* `GeminiClient` wrapper  
* Stable logging \+ retries  
* “prompt → image” returns stored image record

### **Tasks**

1. Create `GeminiClient`:  
   * `generate_text(prompt, model=...)`  
   * `generate_image(prompt, model=...)`  
2. Add retry policy:  
   * transient errors retry N times with backoff  
3. Store image results:  
   * If Gemini returns base64 or URL:  
     * store in object storage (S3/GCS/local)  
     * create `images` row with `image_url` and metadata  
4. Logging:  
   * store request\_id, model name, prompt hash (optional)

### **Acceptance criteria**

* Given a simple prompt, image is generated and accessible via URL  
* Text generation works

---

## **Milestone 4 — Grammar \+ Layout Libraries (Static Config) (Day 7–8)**

### **Deliverables**

* Versioned JSON config files in repo:  
  * `panel_grammar_library_v1.json`  
  * `layout_templates_9x16_v1.json`  
  * `layout_selection_rules_v1.json`  
  * `continuity_rules_v1.json`  
  * `grammar_to_prompt_mapping_v1.json`

### **Tasks**

1. Put the libraries into `app/config/`  
2. Create loaders:  
   * `get_grammar(grammar_id)`  
   * `get_layout_template(template_id)`  
   * `select_template(panel_plan, derived_features)`  
3. Add unit tests:  
   * selecting template for known cases  
   * grammar mapping exists for all grammar ids

### **Acceptance criteria**

* Can load config and validate schema  
* Template selection is deterministic

---

## **Milestone 5 — LangGraph Node Implementations (Day 8–12)**

### **Deliverables**

* Implement **each node** as a pure function:  
  * input artifact(s) → output artifact payload  
* Nodes create artifacts via `ArtifactService`

### **Node list (MVP)**

#### **Node A: `SceneIntentExtractor` (LLM)**

* Input: scene `source_text`, story genre (optional)  
* Output artifact: `scene_intent`

#### **Node B: `PanelPlanGenerator` (LLM \+ constraints)**

* Input: `scene_intent`, `panel_count`  
* Output: `panel_plan` (list of grammar ids \+ story functions)  
* Enforce simple constraints in post-pass (max emotion\_closeup, no triple repeats)

#### **Node C: `PanelPlanNormalizer` (rules)**

* Input: `panel_plan`  
* Output: normalized `panel_plan` version  
* Adjust sequences if illegal (swap to object\_focus/reaction as needed)

#### **Node D: `LayoutTemplateResolver` (rules)**

* Input: `panel_plan` \+ derived features (pacing, has impact)  
* Output: `layout_template` (template\_id \+ layout\_text \+ XYWH)

#### **Node E: `PanelSemanticFiller` (LLM)**

* Input: scene text \+ scene intent \+ panel plan \+ layout template \+ character list  
* Output: `panel_semantics`

#### **Node F: `PromptCompiler` (rules)**

* Input: `panel_semantics` \+ `layout_template` \+ style\_id  
* Output: `render_spec` with a single `prompt` string for Gemini

#### **Node G: `ImageRenderer` (Gemini image)**

* Input: `render_spec`  
* Output: `render_result` with `image_id` \+ URL \+ metadata

#### **Node H: `BlindTestEvaluator` (LLM)**

* Input: `panel_semantics` \+ original scene text  
* Output: `blind_test_report`

### **Acceptance criteria**

* Each node can be run independently with stored artifacts  
* Output artifacts are created and retrievable

---

## **Milestone 6 — LangGraph Wiring \+ Orchestration Endpoints (Day 12–15)**

### **Deliverables**

* Graph definition:  
  * generate plan → render → evaluate  
* “Generate” endpoints that run nodes and return artifact IDs

### **Endpoints (MVP)**

* `POST /v1/scenes/{scene_id}/generate/scene-intent`  
* `POST /v1/scenes/{scene_id}/generate/panel-plan`  
* `POST /v1/scenes/{scene_id}/generate/panel-plan/normalize`  
* `POST /v1/scenes/{scene_id}/generate/layout`  
* `POST /v1/scenes/{scene_id}/generate/panel-semantics`  
* `POST /v1/scenes/{scene_id}/generate/render-spec`  
* `POST /v1/scenes/{scene_id}/generate/render`  
* `POST /v1/scenes/{scene_id}/evaluate/blind-test`

### **Orchestration patterns**

Support two modes:

1. **Step-by-step** (UI-friendly)  
2. **One-shot** “plan+render+eval”  
   * `POST /v1/scenes/{scene_id}/generate/full`

### **Acceptance criteria**

* Can run full pipeline for a scene and get:  
  * render\_result image URL  
  * blind\_test\_report scores

---

## **Milestone 7 — Human Review & Regeneration (Day 15–16)**

### **Deliverables**

* Review endpoints  
* Regenerate image without replanning

### **Endpoints**

* `POST /v1/scenes/{scene_id}/review/approve`  
* `POST /v1/scenes/{scene_id}/review/regenerate`

### **Behavior**

* regenerate creates a new `render_result` artifact linked to same `render_spec`  
* approve marks the render\_result as approved (store in artifact payload or separate table)

### **Acceptance criteria**

* User can regenerate multiple times without changing plan artifacts  
* Approvals are persisted and queryable

---

## **Milestone 8 — Hardening & Observability (Day 16–18)**

### **Deliverables**

* Better errors  
* Logging and traceability  
* Minimal cost controls

### **Tasks**

1. Structured logs:  
   * include `scene_id`, `artifact_id`, `node_name`, `model`  
2. Store model usage metadata:  
   * token usage if available  
   * image generation count  
3. Timeouts and retries  
4. Input validation and safe defaults (panel\_count caps, etc.)

### **Acceptance criteria**

* Failures show actionable error messages  
* You can reproduce a render using stored artifacts

---

# **Implementation Order (Bottom-to-Top Coding Strategy)**

If you want the agent to code bottom-up, instruct them in this order:

1. **DB \+ ArtifactService**  
2. **CRUD endpoints**  
3. **GeminiClient**  
4. **Static libraries loaders \+ tests**  
5. **PromptCompiler (no LLM needed)**  
6. **SceneIntentExtractor (LLM)**  
7. **PanelPlanGenerator \+ Normalizer**  
8. **LayoutResolver**  
9. **PanelSemanticFiller**  
10. **Renderer**  
11. **BlindTestEvaluator**  
12. **LangGraph wiring \+ orchestration endpoints**  
13. **Review/regenerate endpoints**

This order ensures you always have something testable at each step.

---

# **MVP Test Plan (Must run before UI work)**

### **Unit tests**

* layout decision table chooses correct template  
* grammar mapping exists for all grammar ids  
* prompt compiler produces deterministic output

### **Integration tests**

* create story \+ scene  
* run scene-intent → panel-plan → layout → semantics → render-spec  
* run render (image generation mocked in CI)  
* run blind test (text generation mocked)

### **Manual test**

* run end-to-end with one scene and inspect image

---

# **“Definition of Done” for MVP**

You are MVP-done when:

✅ Given a scene text, your API can produce:

* scene\_intent artifact  
* panel\_plan artifact  
* layout\_template artifact  
* panel\_semantics artifact  
* render\_spec artifact (single Gemini prompt)  
* render\_result artifact with image URL  
* blind\_test\_report artifact

✅ And you can:

* regenerate image without replanning  
* approve a render result

---

If you want, I can now convert this into:

* a **GitHub Issues / Epics breakdown** (copy-paste)  
* or an **agent instruction doc** (“build these modules in this order, here are acceptance tests”)
