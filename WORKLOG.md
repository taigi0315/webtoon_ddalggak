# Work Log

## 2026-01-31

- **TASK-004: Scene Image Page Updates & Optimization**
  - Fixed backend serialization for `JobStatusRead` (converted datetime to ISO format strings) to resolve frontend polling issues.
  - Fixed frontend React syntax error in `frontend/app/studio/scenes/page.tsx`.
  - Implemented correct global polling for scene generation jobs in `ScenesPage`.
  - Removed outdated `waitingForImage` logic from `SceneDetail`.
  - Verified batch generation ("Generate All") triggers correctly and updates UI.
  - Investigated slow generation times: identified Google Vertex AI 429 Rate Limit as the cause causing backoff retries.
