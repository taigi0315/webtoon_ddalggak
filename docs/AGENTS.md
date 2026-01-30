# AGENTS & SKILLS: Guidelines for ssuljaengi_v4 🔧

Version: 2026-01-29

Purpose
- Provide a concise, actionable playbook for building, testing, and operating LLM-driven agents and skill modules used by the ssuljaengi_v4 pipeline (panel planning, template selection, semantics, image generation).

Scope
- Design principles for prompts, structured outputs, function/tool calling, JSON validation/repair, testing, monitoring, and safety/guardrails.

Key Principles (short)
- Prefer structured outputs (JSON/strict schemas) wherever possible. ✅
- Apply a three-stage parsing pipeline: 1) direct parse, 2) regex extraction for embedded JSON, 3) LLM-based repair when parsing fails. (See `utils._maybe_json_from_gemini`.) 🔁
- Keep tools/functions small and clearly typed; prefer strict schemas for reliability. 🧩
- Enforce guardrails (e.g., no >2 same layout templates in a row, pacing/cliffhanger overrides). ⚠️
- Test the agent code with deterministic mocked LLMs and unit tests for parsers/repairs. 🧪

Agent design guidelines
1. Roles & responsibilities
   - Panel Plan Agent: returns a `panel_plan` JSON (schema below). Should be idempotent and conservative.
   - Layout Resolver Agent: picks layout templates based on `panel_plan` + derived features (weights, hero_count, pace, scene_importance).
   - Semantics Filler Agent: enriches panels with `text` and visual cues for image generation.
   - Repair Agent (LLM): invoked only for repairing malformed JSON outputs.

2. Prompt engineering
   - Use a strong system prompt that enforces JSON-only responses and an explicit output schema (e.g., `system_prompt_json`).
   - Provide examples and edge cases in prompt when necessary, but avoid making the prompt so long it hits model context or performance limits.
   - For high-stakes structured outputs, prefer `strict`/structured-output features (OpenAI function/schema strict mode where available).

3. Functions & tools
   - Use functions for deterministic operations (e.g., `render_smoke`, `lookup_template`, `generate_image`).
   - Keep schema descriptions short and precise (beware token costs and context length) and enable `strict` mode when possible. Limit simultaneous tools to < 20.
   - For custom free-text tools, supply a concise grammar (Lark or regex) with limited, well-bounded terminals.

Structured output best practices
- Always include an explicit JSON output schema in the prompt or via the API's structured-output tooling.
- Enforce these checks on the client side:
  1. Direct json.loads(text)
  2. Regex extraction of JSON block(s) if direct parse fails
  3. If still invalid, call the repair LLM with the raw text and the expected schema and attempt to parse the repaired output
  4. If repair fails, return a clear error and fallback safely (e.g., heuristic plan) and log the raw output for manual analysis.
- Record and rate-limit repair attempts to avoid cascading LLM costs.

JSON repair & defensiveness
- Keep the repair prompt minimal and include the expected schema. Ask the repair LLM to return only the corrected JSON.
- Log both the malformed text and the repair attempt result; include which method succeeded (direct/regex/repair).
- If a repair attempt throws an exception, capture and report it safely — do not crash the pipeline.

Testing & validation
- Unit tests: parser, regex extraction, repair LLM simulation (mock LLMs that return malformed then repaired text), schema validation.
- Integration tests: run the pipeline end-to-end with a TestFakeGemini that returns deterministic responses; assert artifacts and derived_features are present.
- Add smoke tests that render template SVGs for quick visual inspection (we have `scripts/render_smoke.py`).
- Add E2E tests for guardrails (e.g., max 2 same templates, require_hero_single behavior).

Safety & guardrails (project-specific examples)
- Episode-level template guardrail: do not select the same template more than twice consecutively; provide a re-resolve with exclusions.
- Require hero single: optionally enforce at least one single-panel hero-shot per episode when requested.
- QC hard constraints: max closeup ratio, no more than 2 consecutive grammar repeats, enforce first panel establishing, last panel reaction/reveal.

Monitoring & telemetry
- Log prompts, raw LLM responses (careful with PII), parse method used, and whether a repair was required.
- Capture a small sample of raw LLM outputs (redact PII) for offline analysis and tests.
- Track metrics: parse success rates, repair success rate, average LLM tokens per call, rate of guardrail-triggered re-resolves.

Implementation checklist (short)
- [x] System prompt enforcing JSON-only responses (`system_prompt_json`).
- [x] Three-tier JSON extraction (`_maybe_json_from_gemini`).
- [x] LLM repair helper with logging and safe failure (`_repair_json_with_llm`).
- [x] Unit tests for parsing & repair (`tests/test_json_repair.py`).
- [x] Integration tests for pipeline and guardrails (`tests/test_debug_pipeline.py`, `tests/test_episode_guardrails.py`).

Example schemas (brief)
- Panel plan:
```json
{
  "panels": [{"panel_index": 1, "grammar_id": "establishing", "utility_score": 0.5}, ...]
}
```
- Panel semantics:
```json
{"panels": [{"grammar_id": "establishing", "text": "wide street", "visual_cues": ["rain","cars"]}]}
```

## Concrete prompt & function schema examples 🔧

Below are ready-to-use templates you can copy into `app/prompts` or use as examples when adding new tools.

### 1) System prompt for strict JSON responses (use as `system_prompt_json`)
```text
You are a strict JSON generator for the ssuljaengi_v4 pipeline.
Return ONLY valid JSON. No markdown, no commentary, no code fences.
Use double quotes for all keys and string values. Follow this exact schema:
{ "panels": [{"panel_index": int, "grammar_id": string, "panel_purpose": string, "utility_score": number}], "scene_importance": string | null }
If any value is unknown, use null or an empty list.
```

### 2) Panel plan prompt (example template)
```jinja
{{ global_constraints }}
Create a panel plan for a {{ panel_count }}-panel webtoon sequence.
Characters: {{ char_list }}
Scene text:
{{ scene_text }}

OUTPUT SCHEMA:
{
  "panels": [
    {"panel_index": int, "grammar_id": "establishing|dialogue_medium|emotion_closeup|action|reaction|object_focus|reveal|impact_silence", "panel_purpose": "setup|dialogue|emotion|action|reaction|focus|climax|transition", "utility_score": number}
  ],
  "scene_importance": "setup|build|release|climax|cliffhanger|null"
}

Return only JSON matching the schema above.
```

### 3) Example OpenAI-style function schema for `generate_image` (use in tool/function registration)
```json
{
  "type": "function",
  "name": "generate_image",
  "description": "Generate an image from a visual prompt and return a signed URL and metadata.",
  "parameters": {
    "type": "object",
    "properties": {
      "prompt": {"type": "string", "description": "The visual prompt for image generation."},
      "style_id": {"type": ["string","null"], "description": "Optional art style id."},
      "seed": {"type": ["integer","null"], "description": "Optional deterministic seed."}
    },
    "required": ["prompt"],
    "additionalProperties": false
  }
}
```
- Best practices: keep descriptions short, mark optional fields with `null` unions, set `additionalProperties: false` and use `strict` mode when available.

### 4) Example Lark/regex grammar for a custom `format_panel_line` tool (simple regex variant)
```
^(?P<panel_index>\d+)\s*:\s*(?P<grammar_id>establishing|dialogue_medium|emotion_closeup|action|reaction)\s*-\s*(?P<short_text>.{1,140})$
```
- Use only when outputs are short and easily bounded. Prefer JSON schemas for complex outputs.

### 5) Repair prompt template (used by `_repair_json_with_llm`)
```text
SYSTEM: {{ system_prompt_json }}

The following text was intended to be valid JSON matching this schema:
{{ expected_schema }}

Malformed text:
{{ malformed_text }}

Please return ONLY corrected JSON which conforms exactly to the schema. If fields are unknown, use null or an empty list. Do not add extra fields.
```

### 6) Quick checklist for new tool authors ✅
- Provide a strict JSON schema for the tool output.  
- Add unit tests that exercise direct, embedded (regex), and malformed inputs.  
- Add an integration test that uses a TestFakeGemini returning both valid and malformed outputs.  
- Limit function/tool descriptions to the minimum required; long descriptions may hit token limits.

References & reading
- OpenAI Function Calling & Structured Outputs: https://platform.openai.com/docs/guides/gpt/function-calling 🔗
- Azure OpenAI / Models & Structured Output guidance: https://learn.microsoft.com/en-us/azure/ai-services/openai/overview 🔗
- Local agent best-practices file (React skill example): `/.agent/skills/vercel-react-best-practices/AGENTS.md` 🔍
- LangChain agents overview and agent patterns (recommended): https://docs.langchain.com/oss/python/langchain/overview 🔗

Contact / ownership
- Maintainers: core devs in repo (see README contributors)
- When adding new agent behaviors, add tests that simulate malformed LLM outputs and validate repair paths.

---

If you'd like, I can also:
- Convert this into a shorter `SKILLS.md` with explicit role-based 'checks' for automated skill authors (e.g., token-cost limits, `strict` required) or
- Add in-line examples for our `prompt_*` functions and a small checklist for writing new tools and CFGs.

Which of the follow-ups do you want? (1) Generate `SKILLS.md` (short actionable checklist), (2) Add sample function schemas + prompt templates into `docs/AGENTS.md`, or (3) Crawl 3rd-party agent docs further and add more references.