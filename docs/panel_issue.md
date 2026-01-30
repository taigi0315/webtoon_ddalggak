Absolutely — this is a **planning + layout resolver gap**, not an “image model” gap. What you’re seeing (everything turns into 4 equal stacked panels) happens when:

* panel count is treated as a fixed template, not a pacing outcome
* panel “weights” aren’t actually used to drive geometry
* there’s no layout variety library + selection policy

Below are **Jira-ready tickets** that fix this cleanly.

---

# EPIC: Improve Webtoon Pacing & Layout Variety (Dynamic Panel Sizes + Weighted Layout)

**Epic ID:** WEBTOON-LAYOUT-PACING
**Priority:** P0
**Goal:** Stop generating uniform 4-panel stacked scenes; introduce weighted panel sizing, asymmetric layouts, and per-scene layout selection to create dynamic pacing (strong/weak beats).

---

## TICKET 1 — Add Panel Weight to Panel Grammar (Planning Output)

**Title:** Panel plan missing “weight” → cannot size panels dynamically
**Priority:** P0
**Type:** Backend / Schema + LLM output enforcement

### Problem

Scenes are rendered as evenly distributed panels because panel plans don’t include a usable **importance/weight** field per panel.

### Change

Extend panel schema to include:

```json
{
  "panel_id": 1,
  "panel_role": "main|support|inset",
  "panel_purpose": "establishing|dialogue|reaction|reveal|action|silent_beat",
  "weight": 0.0,
  "must_be_large": false
}
```

**Rules for `weight`:**

* range: `0.1 – 1.0`
* higher = larger panel area
* `must_be_large=true` for reveal/climax frames

### Acceptance Criteria

* PanelPlanGenerator outputs weight for every panel
* Weights correlate with story beat strength (reveal/reaction > filler)

---

## TICKET 2 — Replace Fixed Panel Count with Beat-Driven Panel Count Policy

**Title:** Panel count locked to 4 → scenes become repetitive and dense
**Priority:** P0
**Type:** Planning / Layout selection

### Problem

Even when you provide “7–9 scenes per episode”, each scene defaults to 4 panels. That creates a samey rhythm and removes pacing variety.

### Change

Add scene-level pacing tags and let panel count vary:

**Scene metadata:**

```json
{
  "scene_importance": "setup|build|climax|release|cliffhanger",
  "pace": "fast|balanced|slow",
  "target_panel_count": 1
}
```

**Policy defaults:**

* setup → 3–4 panels
* build → 4–5 panels (but allow asymmetry/insets)
* climax → 1 panel (hero) or 1 big + 1 inset
* release → 2–3 panels
* cliffhanger → 1 panel (hero)

### Acceptance Criteria

* Episode includes a mix of 1, 2–3, 4–5 panel scenes
* At least one **hero single-panel** scene appears for climax/cliffhanger

---

## TICKET 3 — Layout Library: Add Non-Uniform Panel Templates (x,y,w,h)

**Title:** Only “stacked equal panels” template exists → plain layouts
**Priority:** P0
**Type:** Layout engine

### Problem

Even with good panel text, the renderer uses only one geometry layout: 4 equal stacked rectangles.

### Change

Create a layout template library with normalized coordinates `(x, y, w, h)` for 9:16:

**Must include at minimum:**

1. `stacked_equal_4` (existing)
2. `stacked_weighted_3` (big + two small)
3. `dominant_with_inset` (hero + inset)
4. `two_panel_uneven` (70/30)
5. `single_panel_full` (hero)
6. `split_top_then_stack` (wide top + two bottom)

### Acceptance Criteria

* LayoutResolver can return a template ID + panel rects
* Templates are valid in 9:16 and preserve reading flow (top→bottom)

---

## TICKET 4 — Weighted Layout Resolver (Map weights → panel geometry)

**Title:** Panel weights not applied to sizing → all panels equal
**Priority:** P0
**Type:** Rule-based algorithm

### Problem

Panel weights exist (or will exist), but no logic converts them into actual panel sizes.

### Change

Implement a `WeightedLayoutResolver` that:

* sorts panels by reading order (top→bottom)
* allocates vertical height proportional to weight
* optionally assigns “dominant panel” if `must_be_large`

**Constraints:**

* min panel height: e.g. `0.12` of frame
* max panel height for non-hero: e.g. `0.70`
* preserve total height ≤ 1.0 with small gutters

### Acceptance Criteria

* Panels with higher weight appear visibly larger in final scene image
* Reveal/climax panel gets dominant area (hero frame)

---

## TICKET 5 — Layout Selection Decision Table (Make it predictable)

**Title:** Layout choice is not driven by story → repeated templates
**Priority:** P1
**Type:** Rules / Heuristics + config

### Problem

Even with many templates, the system will still pick the same one unless selection is rule-driven.

### Change

Create a deterministic decision table:

Inputs:

* scene_importance
* pace
* #characters in scene
* panel_purpose distribution (dialogue vs reveal vs action)
* presence of “object reveal” (phone, letter, ring, etc.)

Output:

* layout_type/template_id

Example rules:

* if importance in {climax, cliffhanger} → `single_panel_full` OR `dominant_with_inset`
* if reveal exists → `dominant_with_inset` (inset for object)
* if mostly dialogue → `two_panel_uneven` or `stacked_weighted_3`
* if action → `stacked_weighted_4` with skewed weights

### Acceptance Criteria

* Same scene plan yields same layout template (repeatable)
* Variety increases across episode naturally

---

## TICKET 6 — Add “Plainness Guardrail”: Enforce Variety Over Episode

**Title:** Episode-level pacing too uniform → force layout diversity
**Priority:** P1
**Type:** Episode orchestration

### Problem

Even if per-scene logic works, an episode can still end up with repeated layouts.

### Change

Track layout usage across episode and enforce diversity:

* no more than 2 consecutive scenes with same layout template
* require at least:

  * 1 hero single panel scene
  * 1 dominant+inset scene
  * 1 uneven 2–3 panel scene

### Acceptance Criteria

* Episode output has obvious pacing variation
* Visual rhythm feels “webtoon-like”, not grid-like

---

## TICKET 7 — UI/Config: Expose “Pacing” Controls (Optional but useful)

**Title:** Provide simple pacing knobs (fast/balanced/cinematic)
**Priority:** P2
**Type:** Frontend + Backend config

### Requirements

User can choose:

* Episode pacing: fast / balanced / cinematic
* “Hero panels”: off / normal / frequent

### Acceptance Criteria

* LayoutResolver respects user pacing preference

---

## Quick note on your “7–9 scenes” question

7–9 scenes per episode is not “too small”. The issue is:

* **each scene becomes 4 equal panels**, so total panels are huge and repetitive.
  Once you introduce:
* 1-panel hero scenes,
* 2–3 panel scenes,
* weighted panels,
  you’ll get the dynamic pacing you want **even at 7–9 scenes**.

---

If you want, I can also provide:

* a starter set of **actual 9:16 panel templates** with concrete `(x,y,w,h)` values
* and the **layout decision table** in a copy/paste JSON format for your agent
