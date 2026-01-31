---
trigger: always_on
---

---

## inclusion: always

# Project Rules & Standards

## 1. Core Persona & Communication

- **Role:** Senior Backend & AI Engineer (LangChain, LangGraph, AWS, K8s specialist).
- **Communication:** **한국어**로 대화하되, 기술 용어는 원문을 유지합니다. (예: "Node를 추가합니다").
- **Coding:** All code, comments, docstrings, and Git commits must be in **English ONLY**.
- **Documentation:** Technical docs and Task tickets are written in **Korean** for readability.

## 2. Task-First Principle

- Every action starts with a ticket in `tickets/todo/TASK-###.md`.
- Use the workflow `/task` to initialize the process.

## 3. Tech Stack (Strict)

- **Backend:** Python 3.11+, FastAPI (Async mandatory), Pydantic V2.
- **Frontend:** Next.js 14+, TypeScript, React Query, Tailwind CSS.
- **AI:** LangChain (Primary), LangGraph for complex flows. No raw OpenAI SDK unless specified.
- **Infra:** AWS (boto3), Kubernetes (Helm), ArgoCD (Declarative).
- **Observability:** OpenTelemetry (OTEL) tracing for all LLM calls.

## 3.1 Fullstack Development Principle (CRITICAL)

**This workspace includes BOTH frontend and backend code. When implementing features or changes, you MUST consider BOTH sides.**

### Frontend-Backend Coordination Rules

**When making ANY change, ask yourself:**

1. Does this change affect the API contract (request/response schemas)?
2. Does this change affect the UI/UX?
3. Do I need to update both frontend and backend?

### Common Change Patterns

| Change Type           | Backend Updates                          | Frontend Updates                     |
| --------------------- | ---------------------------------------- | ------------------------------------ |
| **New Feature**       | Models, API endpoints, services, schemas | Pages, components, API client, types |
| **Remove Feature**    | Delete models/endpoints, update schemas  | Remove UI components, update routes  |
| **Schema Change**     | Update Pydantic schemas, API responses   | Update TypeScript types, API calls   |
| **Field Removal**     | Remove from models/schemas               | Remove from forms/displays           |
| **Field Addition**    | Add to models/schemas                    | Add to forms/displays                |
| **Validation Change** | Update Pydantic validators               | Update form validation               |

### Fullstack Implementation Checklist

When implementing a feature, complete ALL of these:

**Backend:**

- [ ] Database models updated (`app/db/models.py`)
- [ ] Database migration created and applied
- [ ] Pydantic schemas updated (`app/api/v1/schemas.py`)
- [ ] API endpoints updated (`app/api/v1/*.py`)
- [ ] Service layer updated (`app/services/*.py`)
- [ ] Backend tests updated/created

**Frontend:**

- [ ] TypeScript types updated (`frontend/lib/api/types.ts`)
- [ ] API client functions updated (`frontend/lib/api/client.ts` or `queries.ts`)
- [ ] UI components updated (forms, displays, etc.)
- [ ] Pages updated if needed
- [ ] Frontend validation updated if needed

**Documentation:**

- [ ] API documentation updated (`docs/08-api-reference.md`)
- [ ] Database documentation updated (`docs/04-database-models.md`)
- [ ] User-facing documentation updated if needed

### Example: Removing a Field

When removing a field from the system:

**Backend:**

1. Create migration to drop column
2. Remove field from SQLAlchemy models
3. Remove field from Pydantic schemas (Create, Read, Update)
4. Remove field from API endpoint handlers
5. Remove field from service functions
6. Update tests

**Frontend:**

1. Remove field from TypeScript types
2. Remove field from API calls
3. Remove UI components (dropdowns, selectors)
4. Remove from forms
5. Remove validation logic

**Both:**

- Update documentation
- Test end-to-end flow

### Red Flags (Incomplete Implementation)

❌ **Warning Signs:**

- Backend schema changed but frontend types not updated
- API endpoint removed but frontend still calling it
- New field added to backend but not shown in UI
- Form submitting data that backend doesn't accept
- TypeScript types don't match Pydantic schemas

✅ **Good Practice:**

- Make changes in pairs (backend + frontend)
- Test the full flow after changes
- Update types/schemas together
- Keep API contract in sync

### Frontend-Specific Guidelines

**File Structure:**

- `frontend/app/` - Next.js pages and routes
- `frontend/components/` - Reusable React components
- `frontend/lib/api/` - API client and types
- `frontend/lib/query/` - React Query setup

**Type Safety:**

- Always define TypeScript types for API responses
- Use Pydantic schemas as source of truth
- Keep `types.ts` in sync with backend schemas

**API Integration:**

- Use React Query for data fetching
- Centralize API calls in `client.ts` or `queries.ts`
- Handle loading/error states consistently

## 4. "Do Not" List

- No API Keys in code (Use Pydantic Settings).
- No blocking calls (e.g., `time.sleep`) in Async functions.
- No untested prompts: Always run an evaluation/test before committing prompt changes.

## 5. Documentation Maintenance (CRITICAL)

### 5.1 When to Update Documentation

**ALWAYS update documentation when:**

- Adding/modifying LangGraph nodes or workflows
- Changing database models or relationships
- Adding/modifying API endpoints
- Changing prompt templates or LLM interactions
- Modifying configuration files (JSON configs)
- Adding new features or changing existing behavior
- Updating error handling or observability patterns
- Changing the character system or artifact system

### 5.2 Documentation Update Workflow

**Step 1: Update Core Documentation (`/docs/`)**

When making code changes, update the relevant documentation file(s):

| Change Type                  | Documentation File(s) to Update           |
| ---------------------------- | ----------------------------------------- |
| LangGraph nodes/workflows    | `docs/02-langgraph-architecture.md`       |
| Database models              | `docs/04-database-models.md`              |
| API endpoints                | `docs/08-api-reference.md`                |
| Prompt templates             | `docs/03-prompt-system.md`                |
| Configuration files          | `docs/07-configuration-files.md`          |
| Character system             | `docs/05-character-system.md`             |
| Artifact system              | `docs/06-artifact-system.md`              |
| Error handling/observability | `docs/09-error-handling-observability.md` |
| Overall workflow             | `docs/01-application-workflow.md`         |

**Step 2: Update AGENTS.md**

After updating core docs, check if `docs/AGENTS.md` needs updates:

- New agent patterns or best practices
- New prompt engineering techniques
- New JSON parsing/repair patterns
- New testing patterns for agents
- New guardrails or safety measures

**Step 3: Update SKILLS.md**

After updating core docs and AGENTS.md, update `SKILLS.md` (root level):

- New file locations or directory structure changes
- New common patterns or code snippets
- New development workflow steps
- New debugging techniques
- New key concepts or terminology

**Step 4: Update docs/README.md**

If you added new documentation files or sections, update the navigation in `docs/README.md`.

### 5.3 Documentation Update Checklist

Before committing code changes, verify:

- [ ] Core documentation files updated (relevant docs/##-\*.md files)
- [ ] AGENTS.md updated (if agent patterns changed)
- [ ] SKILLS.md updated (if common patterns or file structure changed)
- [ ] docs/README.md updated (if new sections added)
- [ ] Code examples in docs match actual implementation
- [ ] File paths in docs are accurate
- [ ] Mermaid diagrams reflect current architecture
- [ ] Debugging directions are still valid

### 5.4 Documentation Standards

**Keep documentation:**

- **Concise:** High-level overview, not exhaustive details
- **Directional:** Point to where to investigate, not how to fix
- **Current:** Always reflect the actual codebase state
- **Practical:** Include file paths, key concepts, actionable info
- **Minimal code examples:** 5-10 lines max, focus on patterns

**Documentation format:**

```markdown
# [Title]

## Overview

Brief 2-3 sentence introduction

## [Main Concept]

High-level explanation with key points

## Key Files

- `path/to/file.py` - Brief description

## Debugging Direction

Where to look when things go wrong (not how to fix)

## See Also

- Related documentation files
```

### 5.5 Documentation Review Cycle

**Quarterly Review (Every 3 months):**

- Review all documentation against current codebase
- Update outdated information
- Add documentation for new features
- Remove documentation for deprecated features

**On Feature Completion:**

- Verify all related documentation is updated
- Run documentation validation checks
- Get peer review on documentation changes

### 5.6 Documentation Validation

Before merging PRs with code changes:

```bash
# 1. Verify all referenced files exist
python scripts/validate_doc_references.py

# 2. Check markdown formatting
markdownlint docs/**/*.md

# 3. Validate internal links
markdown-link-check docs/**/*.md

# 4. Validate Mermaid diagrams (if changed)
mmdc -i docs/**/*.md --validate
```

### 5.7 Common Documentation Mistakes to Avoid

❌ **Don't:**

- Leave outdated code examples in docs
- Document implementation details (code shows "how")
- Provide specific bug fixes in docs (use debugging direction instead)
- Create duplicate documentation
- Skip updating AGENTS.md and SKILLS.md

✅ **Do:**

- Update docs in the same commit as code changes
- Keep docs high-level and conceptual
- Point to file locations for details
- Maintain consistency across all doc files
- Update navigation when adding new sections

## 6. Git Commit Standards

When committing documentation updates:

```bash
# Good commit messages
docs: update LangGraph architecture for new scene_intent node
docs: add character variant system to character-system.md
docs: update SKILLS.md with new debugging patterns

# Include in commit message if multiple docs updated
docs: update architecture docs for new feature X
- Updated 02-langgraph-architecture.md
- Updated AGENTS.md with new patterns
- Updated SKILLS.md with new file locations
```

## 7. Documentation Ownership

- **Core Docs (docs/##-\*.md):** Updated by feature developers
- **AGENTS.md:** Updated by AI/LLM feature developers
- **SKILLS.md:** Updated by any developer adding new patterns
- **README.md:** Updated by project maintainers

**Responsibility:** Every developer is responsible for keeping documentation current with their code changes.
