# Ssuljaengi v4 - Improvement Plan ("The 4 Hats Review")

This document analyzes the codebase from four distinct professional perspectives to identify key areas for improvement.

## 1. Product Manager View (PM)

_Focus: User Experience, Workflow Flexibility, Feature Gaps_

### Findings

- **High-Level Workflow**: The specific "Shot Types" (Romance, Drama, etc.) and "Blind Test" features are excellent differentiators. The workflow is logical (Plan -> Layout -> Render).
- **Rigid Heuristics**: The system relies heavily on hardcoded rules (e.g., "if more than 50% closeups, fail QC"). This might frustrate users who want a specific artistic style that breaks these rules.
- **Limited User Control**: Users can "override" prompts, but they cannot easily tweak the _layout_ or _panel plan_ without restarting the process.

### Recommendations

- **[Feature] Configurable QC Profiles**: Allow users to relax QC rules (e.g., "Experimental Mode" which allows 100% closeups).
- **[UX] Interactive Planning**: Break the "Planning" graph to allow user intervention _between_ `Panel Plan` and `Layout`. Let users drag-and-drop panel arrangements before image generation starts.
- **[Content] Genre Expansion**: The genre dictionary is hardcoded. Move this to a database config to allow adding new genres without code deploys.

## 2. Prompt Engineer View

_Focus: Prompt Structure, Context Management, Model Steering_

### Findings

- **Hardcoded Prompts**: Prompts are buried in `app/graphs/nodes/__init__.py` as Python string constants (e.g., `VISUAL_PROMPT_FORMULA`, `CHARACTER_STYLE_MALE_KID`). This makes A/B testing and iteration extremely difficult.
- **Good Generic Patterns**: The "Visual Prompt Formula" (Line 382) forces the model to follow a strict structure, which excellent for consistency.
- **Context Stuffing**: The `_compile_prompt` function injects a lot of context (layout text + character details + genre guide). There is a risk of the model forgetting the core instruction ("Make a webtoon panel") amidst the details.

### Recommendations

- **[Architecture] Externalize Prompts**: Move all prompts to `app/prompts/` as `.yaml` or `.jinja2` files. Use a library like `langchain-hub` or a simple loader pattern to manage them.
- **[Technique] Chain-of-Thought**: The current prompts are mostly "One-Shot". For complex tasks like "Panel Semantics", implementing a Chain-of-Thought (CoT) prompting strategy could improve adherence to the script.
- **[Optimization] Dynamic Few-Shot**: Instead of static rules, retrieve similar _successful_ past panels from a vector store to use as few-shot examples in the prompt.

## 3. Software Engineer View (SWE)

_Focus: Architecture, Scalability, Code Quality, Safety_

### Findings

- **Monolithic Node File**: `app/graphs/nodes/__init__.py` is **3000+ lines long**. It violates the Single Responsibility Principle, mixing database calls, string manipulation, prompt construction, and business logic.
- **Critical State Issue**: The LangGraph state dictionaries contain `db: Session`.
  - **Problem**: SQLAlchemy Sessions are **not serializable**.
  - **Consequence**: You cannot use LangGraph's persistent checkpointing (saving state to Redis/Postgres) because it tries to pickle the state. If the server restarts mid-job, the `Session` object is lost/invalid.
- **Type Safety**: While `TypedDict` is used, the heavy reliance on passing raw dictionaries (`payload` artifacts) reduces type safety between nodes.

### Recommendations

- **[Refactor] Split Nodes Module**: Decompose `nodes/__init__.py` into:
  - `app/graphs/nodes/planning.py`
  - `app/graphs/nodes/rendering.py`
  - `app/graphs/nodes/utils.py`
- **[Refactor] Remove Session from State**: Pass only `scene_id` (UUID) in the state. Each node should create/close its own short-lived DB session or use a dependency injection pattern that doesn't put the connection in the graph state.
- **[Testing] Unit Tests**: The current logic is hard to test because it requires a DB session. Decoupling logic from the DB would allow for easier unit testing.

## 4. LangChain Engineer View

_Focus: Framework Usage, Orchestration, Observability_

### Findings

- **Custom Client Implementation**: The project creates a custom `GeminiClient` wrapper around `google-genai`.
  - **Missed Opportunity**: `langchain-google-vertexai` already handles retries, safety settings, and standardizes the interface.
- **Manual Output Parsing**: The code manually repairs JSON (`_maybe_json_from_gemini`). LangChain's `PydanticOutputParser` or `.with_structured_output()` are more robust standard solutions.
- **Observability**: `trace_span` is manually implemented. LangSmith (or OpenTelemetry auto-instrumentation) could provide deeper visibility into token usage and latency without manual decorators.

### Recommendations

- **[Migration] Adopt Standard ChatModels**: Replace `GeminiClient` with `ChatVertexAI`. This enables swapping models (e.g., to GPT-4 or Claude) with zero code changes.
- **[Pattern] Structural Output**: Use `.with_structured_output(PydanticModel)` for nodes like "Character Extractor" to guarantee valid schema compliance without custom "repair" loops.
- **[Graph] Sub-Graphs**: The `pipeline.py` is getting complex. Explicitly defining "SubGraphs" (e.g., a dedicated `CharacterRefinementGraph`) would clean up the main definition.

## Summary Checklist

| Priority     | Category | Task                                                                     |
| :----------- | :------- | :----------------------------------------------------------------------- |
| **Critical** | SWE      | **Remove `Session` from Graph State** (Fixes serialization/persistence). |
| **High**     | SWE      | **Refactor `nodes/__init__.py`** (Split into smaller modules).           |
| **High**     | Prompt   | **Externalize Prompts** (Move out of code).                              |
| **Medium**   | LC       | **Adopt `ChatVertexAI`** (Standardize LLM interface).                    |
| **Medium**   | PM       | **Configurable QC Rules** (Allow user flexibility).                      |
