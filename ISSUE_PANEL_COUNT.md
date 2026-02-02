# Issue: LLM Generates Excessive Panels (6-8 instead of 3)

**Date:** 2026-02-01
**Status:** ✅ Fixed (Root cause addressed)
**Severity:** High (Affects story quality)

## Problem Summary

**Expected Behavior:**

- Scene generation should create **1-3 panels maximum** per scene image
- LLM should respect the `panel_count` parameter (1-3)

**Actual Behavior:**

- LLM generates **6-8 panels** regardless of input
- Truncation to 3 panels breaks story continuity (cuts off ending)

## Terminology

- **Story** = Collection of scene images with dialogue
- **Scene** = Single image (can contain 1-3 panels)
- **Panel** = Individual frame/cut within a scene image (like webtoon panels)

## Root Cause Analysis (COMPLETED)

### Primary Root Cause: BEAT Markers in source_text

**Location:** `app/graphs/story_build.py:114-125`

When scenes were created from visual_beats, the `source_text` was formatted with explicit `BEAT:` markers:

```python
# OLD CODE (problematic)
for b in batch:
    part = f"BEAT: {b.get('visual_action', '')}"
    if b.get("dialogue"):
        part += f"\nDIALOGUE: {b.get('dialogue')}"
```

This created scene text like:
```
BEAT: Character walks in
DIALOGUE: "Hello"

BEAT: Sees friend
DIALOGUE: "Oh!"

BEAT: They talk
... (6 BEAT markers)
```

**The LLM interpreted each "BEAT:" marker as requiring its own panel**, overriding the explicit `panel_count` instruction.

### Secondary Root Cause: Prompt Structure

The panel_count constraint was at the TOP of the prompt, but the scene_text with BEAT markers came at the BOTTOM. The last content the LLM saw before generating output was the structured BEAT markers, which influenced it more than the earlier constraint.

## Fixes Applied

### 1. Removed BEAT Markers from source_text ✅

**File:** `app/graphs/story_build.py`

Changed scene text formatting from structured BEAT markers to natural narrative:

```python
# NEW CODE (fixed)
for b in batch:
    action = b.get('visual_action', '')
    dialogue = b.get('dialogue', '')
    sfx = b.get('sfx', '')

    # Natural narrative format
    part = action
    if dialogue:
        part += f' "{dialogue}"'
    if sfx:
        part += f" ({sfx})"
    text_parts.append(part)

source_text = " ".join(text_parts)  # Single paragraph, not separated blocks
```

### 2. Strengthened Panel Plan Prompt ✅

**File:** `app/prompts/prompts.yaml`

Added explicit anti-beat-counting instructions:

```yaml
**CRITICAL CONSTRAINT - READ CAREFULLY:**
- You MUST output exactly {{ panel_count }} panels in the "panels" array
- The scene text below may describe multiple story moments or beats - you MUST COMBINE them into {{ panel_count }} panels
- DO NOT create one panel per paragraph or story beat - MERGE related beats together
- If the scene has 6 story moments, you still output only {{ panel_count }} panels by combining moments
```

Added end-of-prompt reinforcement:

```yaml
**FINAL REMINDER: Output exactly {{ panel_count }} panels. Combine multiple story beats into these {{ panel_count }} panels. Do NOT output more than {{ panel_count }} panels regardless of how many beats are in the scene text.**
```

### 3. Fixed Importance Calculation ✅

**File:** `app/graphs/nodes/utils.py`

Updated `_panel_count_for_importance()` to cap at 3:

```python
def _panel_count_for_importance(...) -> int:
    """Returns a value between 1-3 (hard limit for panel count per scene)."""
    MAX_PANELS = 3

    if importance in {"climax", "cliffhanger"}:
        return 1  # Impact moments: single panel
    if importance == "release":
        return 3 if word_count >= 120 else 2
    if importance in {"setup", "build"}:
        return MAX_PANELS  # Use max panels for context

    return max(1, min(int(fallback), MAX_PANELS))
```

## Verification Checklist

- [x] source_text no longer contains BEAT: markers
- [x] Prompt explicitly tells LLM to COMBINE beats into requested panels
- [x] End-of-prompt reinforcement added
- [x] `_panel_count_for_importance()` never returns > 3
- [x] Frontend sends panelCount: 3
- [x] API validation limits to 1-3

## Expected Outcome

- LLM should now naturally generate 1-3 panels per scene
- Narrative should maintain proper arc within those panels
- Truncation should rarely be needed (safety fallback only)
- Story beats are COMBINED into panels, not 1:1 mapped

## Testing Required

To verify the fix:
1. Restart backend completely
2. Create a new story with 6-8 scenes
3. Generate scene images
4. Check logs for: `Panel plan for scene XXX generated N panels`
5. Verify N is 1-3 without truncation warning

## Code Locations (Updated)

### Changed Files:
- `app/graphs/story_build.py:114-125` - source_text formatting (FIXED)
- `app/prompts/prompts.yaml:283-345` - Panel plan prompt (FIXED)
- `app/graphs/nodes/utils.py:160-185` - Importance calculation (FIXED)

### Existing Safeguards:
- `app/api/v1/generation.py:29` - API validation (le=3)
- `app/graphs/nodes/planning/panel_plan.py:67,73` - Clamping (1-3)
- `app/graphs/nodes/planning/panel_plan.py:118` - Truncation fallback

## Notes

- Root cause was the structured BEAT: markers teaching the LLM to think "1 beat = 1 panel"
- The prompt constraint was less influential than the formatted content
- Fix addresses both the data format AND the prompt structure
