Below is a well-scoped Jira ticket that matches what you discovered and fits the architecture we designed (Actor → Variant → EpisodeCast/Scene usage). It’s written so the coding agent can implement without needing “product intuition”.

⸻

TICKET: Scene-Level Outfit / Variant Override for Character References

Priority: P0
Type: Backend (LangGraph + Prompt Compiler) + Data Model linkage
Owner: Backend / LLM pipeline
Goal: Prevent wrong outfits in scene images when characters require outfit changes (e.g., casual → swimwear) while still using reference images for identity consistency.

⸻

Problem

Scene image prompts currently include a static “character description” block at the top that was originally used to generate the character reference image (e.g., “wearing casual clothes”). When the scene requires a different outfit (e.g., swimming pool scene), the model generates the character still wearing casual clothes, because:
• The prompt explicitly asserts the outfit as part of identity
• The reference image also shows casual outfit
• Scene-level instructions (“wearing swimwear”) lose to the stronger identity block

This breaks story continuity and causes scenes to be visually incorrect.

⸻

Desired Behavior

When a scene requires a different outfit or look, the system should: 1. Keep identity consistent using reference images (face/hair/body) 2. Allow scene-specific variant overrides (outfit, accessories, condition like wet hair, etc.) 3. Avoid prompt conflicts where the global “character identity” block overrides the scene.

⸻

Root Cause (Implementation-Level)

Currently the prompt compiler treats outfit as part of stable identity, and places it in a high-priority character description header used for every scene.

We must separate:
• Stable identity traits (face, hair, body proportions)
from
• Scene-dependent traits (outfit, accessories, condition, hair state, makeup, injuries, wetness, etc.)

⸻

Solution Overview

A) Refactor Character Identity Lines into Two Layers

1. Identity Anchor (never changes across scenes)
   • gender, age range, ethnicity (optional), facial features, hair shape/color, body build
   • NO outfit text here

2. Scene Variant Overrides (per scene / per panel)
   • outfit, shoes, accessories, hair state (wet/dry), mood/emotion intensity, special props held
   • these are applied by the prompt compiler based on scene semantics

⸻

Required Data Model Updates (Minimal)

Add a “scene_variant” field in panel/scene spec

At scene or panel level, for each character present:

{
"role_name": "Min-ji",
"actor_id": "uuid",
"base_variant_id": "uuid",
"scene_variant": {
"outfit": "black one-piece swimsuit with light cover-up",
"hair_state": "wet",
"accessories": ["goggles"],
"notes": "pool scene"
}
}

Important: scene_variant is an override layer; it does NOT create a new permanent variant unless user explicitly saves it.

⸻

LangGraph Changes

1. Add/Update Node: VariantNeedDetector (LLM or rule-based)

Input: scene_text + panel plan + environment
Output: per character, whether outfit/variant change is required.

Examples:
• “swimming pool”, “beach”, “shower” → swimwear/wet hair likely
• “office”, “meeting” → office attire
• “night”, “pajamas” → sleepwear

This node should output scene_variant overrides per character.

2. Update Node: PromptCompiler (Rule-based)

Modify prompt assembly:
• Top-level character section should include:
• stable identity only
• “Reference images provided; identity must match references”
• Outfit must be removed from identity header
• Outfit and scene variant must be injected:
• inside each panel description
• or inside a per-panel character directive block

⸻

Prompt Compiler Rules (Must Implement)

Rule 1 — Remove Outfit from Identity Header

The “CHARACTERS” header must not contain outfit if the outfit can change across scenes.

✅ Allowed in identity header:
• hair, face, body, age, gender, key identity cues

❌ Not allowed in identity header:
• outfit, shoes, accessories (unless permanent like glasses), scene-specific props

Rule 2 — Outfit is always panel-level

If panel semantics says “pool scene”, then in that panel:
• explicitly state “Min-ji is wearing swimwear”
• explicitly state “Ji-hoon is in swim trunks”
• and optionally “wet hair / water droplets / towel”

Rule 3 — Resolve Prompt Conflicts Automatically

If there is a mismatch:
• identity header outfit says casual
• panel says swimwear
→ compiler must strip the outfit from header and keep panel override only.

⸻

UI / User Workflow Impact (No New UI Required in Phase 1)
• Existing “suggested variant generation” UX can remain
• But scene render must work correctly even without user pre-generating a variant
• Optionally later: “Save this look as a variant” button after a successful scene

⸻

Acceptance Criteria

Functional
• In a test episode:
• Character base reference is casual outfit
• Scene is swimming pool
→ Generated scene must show swimwear (not casual clothes)

Consistency
• Face/hair/body proportions remain consistent with reference images
• Outfit changes correctly per scene

Non-regression
• Scenes that do not require outfit change should still match the base reference
• Existing character generation flows remain unchanged

⸻

Test Cases 1. Casual → Swimwear

    •	Base variant: casual clothes
    •	Scene: pool
    •	Expect: swimwear, wet hair optional

    2.	Office → Pajamas

    •	Scene: bedroom late night
    •	Expect: sleepwear/pajamas

    3.	No change

    •	Scene: cafe
    •	Expect: casual remains

    4.	Two characters, different variants

    •	One changes (swimwear), one does not (spectator on chair)
    •	Expect: different outfits in same scene

⸻

Implementation Notes (Important for Agent)
• This is primarily a prompt authority / conflict issue.
• Treat reference images as identity anchor, but explicitly allow outfit override.
• The most important code change is in prompt composition:
• Don’t state outfit as identity
• Do state outfit inside panel-level instructions

⸻

If you want, paste the current “CHARACTERS” block used in your scene prompt, and I’ll rewrite it into the new Identity Anchor + Scene Variant Override format so the agent can copy-paste it into the PromptCompiler template.
