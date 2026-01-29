# WEBTOON LAYOUT & PACING: Weighted Layouts and Dynamic Templates ✅

## Summary
This document describes a compact implementation plan to fix repetitive, equal-panel layouts by introducing:

- Panel-level `weight` and `must_be_large` attributes in the panel plan
- A small `WeightedLayoutResolver` behavior that maps weights → final panel geometry (x,y,w,h)
- Selection rules that choose asymmetric templates when appropriate
- Episode-level guardrails to ensure layout variety

This aligns with the design issues described in `panel_issue.md` and `panel_design_solution.md`.

---

## Why this will work better 🔧

- Story-driven sizing: panel `weight` encodes narrative emphasis; the layout will reflect beat strength visually.
- Deterministic but flexible: our resolver produces repeatable layouts given the same panel plan, but templates and weights allow variety across scenes.
- Non-uniform templates + weight mapping allow hero frames and insets without requiring prompt engineering changes in the renderer.
- Supports future video use-cases: dominant panels are identifiable as keyframes.

---

## Implementation overview (what changed)

1. Panel plan now includes `weight` (float 0.1–1.0) and `must_be_large` (bool). We compute them from a panel utility score (existing) and scene importance.
2. `run_panel_plan_generator` now assigns weights via `_assign_panel_weights` before storing the artifact.
3. `run_layout_template_resolver` applies `_apply_weights_to_template` to selected templates. For full-width stacked templates it allocates vertical heights proportional to weights (with min height and gutters enforced). For asymmetric templates, `must_be_large` is mapped to the largest rect when possible.
4. Tests added: `tests/test_weighted_layout.py` validates weights are present and that weighted heights are applied.
5. Documentation added (`docs/layout_pacing_solution.md`).

---

## Acceptance criteria ✔️

- Panel artifacts include `weight` and `must_be_large` for every panel.
- Vertical stacked templates produce visibly larger panels when weights differ (unit tests check numeric heights).
- Climax/cliffhanger scenes produce one `must_be_large` panel when applicable.

---

## Next steps (implement + QA)

1. Run test suite and ensure CI passes.
2. Visually inspect several generated scenes (seeded panel plans) to confirm variety.
3. Add a decision-table step in `loaders.select_template` later to drive template selection by scene_importance/pace.

---

If you'd like, I can now:
- extend layout selection rules to consider panel_purpose distribution and scene_importance
- add an episode-level guardrail that enforces diversity during episode orchestration

