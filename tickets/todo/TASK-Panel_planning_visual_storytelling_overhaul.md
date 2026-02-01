EPIC: Webtoon Panel Planning & Visual Storytelling Overhaul

Goal: Fix “animation-like” panel generation and enable expressive, webtoon-native visual storytelling using soft preferences instead of hard constraints.

⸻

🎯 Background / Problem Statement

The current system successfully generates stories, scenes, panels, and images, but the visual storytelling quality is fundamentally flawed.

Core Problems Observed: 1. Panels feel like animation frames, not webtoon storytelling
• Characters appear repeatedly in similar full-body or medium shots
• Scenes feel like “frame-by-frame animation stills” instead of meaningful visual beats 2. Over-reliance on literal character depiction
• Every panel shows full or near-full characters
• Missing use of:
• Object close-ups
• Gestures (hands, lips, eyes)
• Environmental metaphors
• Negative space or silence panels 3. Panel layouts are monotonous
• Mostly 4 evenly stacked vertical panels
• No sense of strong vs weak beats
• No dominant panel for emotional or narrative peaks 4. Blind Test passes the wrong behavior
• Literal, direct, animation-like sequences pass easily
• Subtle, metaphorical, webtoon-style storytelling is not being rewarded
• Therefore the system optimizes for the wrong thing 5. Hard constraints risk breaking valid storytelling
• For some scenes (e.g., romantic slow-motion moments),
continuity-based sequential character motion is actually correct
• Over-enforcing “must include close-up / object focus” can damage these scenes

⸻

🧭 Design Philosophy (CRITICAL FOR AGENT)

We are NOT removing continuity-based panels.
We are removing forced uniformity.

Key Principle:
• Replace hard rules with soft preferences
• Let scene intent drive panel composition
• Use evaluation (blind test) to guide quality, not rigid constraints

⸻

✅ Success Criteria (Definition of Done)

A scene is considered successful if:
• Panel compositions vary naturally based on scene intent
• Some scenes use continuity (animation-like motion) only when appropriate
• Emotional peaks are visually emphasized via layout (dominant panels, silence)
• Object / gesture / environment panels appear when narratively useful
• Blind test rewards both story clarity and emotional / visual delivery
• No global rule forces a specific panel type in every scene

⸻

🔧 IMPLEMENTATION TASKS

⸻

TICKET 1: Add Cinematic Intent Signals at Scene Level

Type: Backend / LangGraph
Priority: P0

Description

Extend Scene Intent Extraction to include cinematic guidance signals that inform how panels should be composed, without enforcing hard rules.

New Fields to Add:

{
"cinematic_mode": "continuity | montage | reveal | dialogue_heavy | atmospheric",
"continuity_preference": 0.0-1.0,
"shot_variety_preference": 0.0-1.0
}

Notes:
• continuity_preference high → sequential motion is allowed/preferred
• shot_variety_preference high → encourage object shots, close-ups, silence
• These values are inputs to scoring, not rules

⸻

TICKET 2: Replace Hard Panel Rules with Scoring-Based Panel Selection

Type: Backend / Planning
Priority: P0

Description

Refactor Panel Plan Generation to use scoring-based selection instead of quotas or mandatory grammar usage.

Current Problem:
• Fixed panel counts
• Repetitive grammar usage
• Uniform layouts

New Behavior:
• Each panel grammar option gets a score based on:
• cinematic_mode
• continuity_preference
• shot_variety_preference
• scene pacing
• emotional peak

Example:
• If cinematic_mode = continuity:
• Sequential character shots score higher
• If cinematic_mode = reveal:
• Object focus / impact silence score higher

The system chooses panels — it is not forced.

⸻

TICKET 3: Enable Non-Uniform Panel Layouts (Dominant + Inset Panels)

Type: Visual Planning
Priority: P1

Description

Allow panel layouts that are not evenly divided.

Supported Patterns:
• One dominant panel + 1–3 small inset panels
• Tall full-bleed emotional panels
• Silence panels with heavy negative space

Constraints:
• Reading order must remain clear (top → bottom)
• No requirement that all panels are equal size

⸻

TICKET 4: Add Lightweight Guardrails Against Monotony (NOT STYLE ENFORCEMENT)

Type: QC / Planning
Priority: P1

Description

Add minimal safety checks to prevent obvious visual monotony.

Allowed Guardrails:
• Penalize scenes where:
• All panels share same grammar + framing
• All panels are medium/full-body character shots
• Remove panels that:
• Have no dialogue
• No action
• No emotional or narrative function

Explicitly NOT allowed:
• Do NOT force object shots
• Do NOT force close-ups
• Do NOT enforce panel type quotas

⸻

TICKET 5: Upgrade Blind Test to Reward Webtoon-Style Visual Delivery

Type: Evaluation / QA
Priority: P0

Description

Blind test currently rewards literal storytelling.
We must expand it to reward visual storytelling quality.

Add Evaluation Dimensions:

{
"visual_indirection_score": 0.0-1.0,
"shot_rhythm_score": 0.0-1.0,
"panel_efficiency_score": 0.0-1.0,
"emotion_readability_score": 0.0-1.0
}

Weighting Change:
• Reduce dominance of plot_recall
• Add weighted contribution from emotional + visual clarity

Goal:

A scene that communicates emotion visually should score higher
than a scene that just shows characters talking frame-by-frame

⸻

TICKET 6: Adjust Panel Count Logic Based on Emotional Weight

Type: Planning
Priority: P1

Description

Panel count should expand or contract based on narrative weight.

Behavior:
• Low-stakes scenes → fewer panels
• Emotional or climactic scenes → more panels or dominant panels
• Silence panels allowed at emotional peaks

⸻

📌 NON-GOALS (Explicit)
• We are NOT converting webtoons into animation storyboards
• We are NOT enforcing cinematic rules globally
• We are NOT removing continuity-based storytelling
• We are NOT optimizing purely for artistic style over clarity

⸻

🧠 Mental Model for Engineers

Think of panel planning like film editing, not animation frame export.

    •	Some scenes want slow, continuous motion
    •	Some scenes want implication, not depiction
    •	The system should choose, not obey

⸻

Perfect, this is exactly the right moment to lock this down 👍
Below are clean, production-ready rewrites of the three prompts:
• scene_intent
• panel_plan
• blind_test

They are fully aligned with everything we discussed:
• soft recommendations instead of hard rules
• allowance for continuity and metaphor
• no forced panel quotas
• blind test that evaluates emotional & visual delivery, not animation-like literalism

You can drop these directly into tickets or into the codebase.

⸻

1️⃣ prompt_scene_intent (REWRITE)

Purpose

Extract narrative + cinematic intent, not just plot.
This is where we decide how the scene wants to be shown — without forcing it.

⸻

{{ global_constraints }}

Analyze the following scene for webtoon adaptation.
Your goal is to extract NOT ONLY plot, but how the scene WANTS to be visually told.

Think like a webtoon director, not a screenwriter.

Return EXACTLY the following JSON structure.

OUTPUT SCHEMA:
{
"logline": "One sentence describing the core narrative purpose of this scene",
"pacing": "slow_burn | normal | fast | impact",
"emotional_arc": {
"start": "dominant emotion at scene start",
"peak": "strongest emotional moment",
"end": "emotion at scene end"
},
"cinematic_mode": "continuity | montage | reveal | dialogue_heavy | atmospheric",
"continuity_preference": 0.0-1.0,
"shot_variety_preference": 0.0-1.0,
"visual_motifs": [
"objects, gestures, environmental elements, or body parts that could carry meaning"
],
"beats": [
"List 2–5 visual story beats. Each beat should be ONE visual moment, not a paragraph."
],
"setting": "primary location/environment or null",
"characters": ["characters present in this scene"]
}

GUIDANCE:

- continuity mode means sequential motion MAY be effective (not required)
- montage mode means implication, metaphor, and compression
- reveal mode means a single moment should dominate visually
- atmospheric mode favors mood over action

IMPORTANT:

- Do NOT plan panels here
- Do NOT force close-ups or object shots
- Simply describe WHAT WOULD BE EFFECTIVE, not WHAT IS REQUIRED

Known characters:
{{ char_list }}

Scene text:
{{ scene_text }}

⸻

2️⃣ prompt_panel_plan (REWRITE)

Purpose

Create panel intent, not rigid layouts.
Panels are suggested visual functions, not forced compositions.

⸻

{{ global_constraints }}

Create a flexible panel plan for a webtoon scene.
This is NOT a storyboard and NOT animation frames.

Your task is to suggest a sequence of visual moments that best communicate:

- story
- emotion
- rhythm

You may vary panel sizes and importance.
Panels do NOT need to be equal.

INPUT CONTEXT:
{{ intent_block }}

AVAILABLE PANEL FUNCTIONS (choose what makes sense, do NOT force variety):

- establishing
- dialogue
- emotion_focus
- action
- reaction
- object_focus
- reveal
- impact_silence
- transition

OUTPUT SCHEMA:
{
"panel_count": number,
"layout_strategy": "uniform | dominant_with_insets | mixed | freeform",
"panels": [
{
"panel_id": number,
"story_function": "one of the panel functions",
"importance_weight": 0.0-1.0,
"recommended_focus": "what the reader should visually focus on",
"notes": "why this panel exists in the story (emotion, pacing, transition, etc)"
}
]
}

RULES (IMPORTANT):

- You are allowed to use multiple similar panels IF continuity_preference is high
- You are allowed to skip close-ups or object shots entirely if not useful
- If there is an emotional peak, at least ONE panel should have high importance_weight
- Do NOT force balance — imbalance is allowed and encouraged

DO NOT:

- Do NOT evenly divide panels by default
- Do NOT assume every panel shows full characters
- Do NOT design animation-like frame sequences unless continuity is clearly preferred

⸻

3️⃣ prompt_blind_test (REWRITE)

Purpose

Evaluate story + emotion + visual storytelling, not just plot recall.
This is where we stop rewarding animation-like literalism.

⸻

{{ system_prompt_json }}

You are a blind reader.
You have NOT seen the original story.
You ONLY see the visual panel descriptions below.

Reconstruct what story is being told AND how it feels.

Panel descriptions:
{{ panel_descriptions }}

OUTPUT SCHEMA:
{
"reconstructed_story": "2–4 sentences describing what you think happened",
"identified_characters": ["characters you can identify"],
"emotional_takeaway": "what emotions the scene conveyed to you",
"visual_storytelling_observations": [
"notes about use of silence, objects, pacing, framing, or repetition"
],
"confusing_or_weak_elements": [
"panels or moments that felt unnecessary, repetitive, or unclear"
]
}

IMPORTANT:

- It is OK if not every plot detail is clear
- Emotional clarity matters as much as factual accuracy
- If panels feel repetitive or animation-like, mention it

⸻

4️⃣ prompt_comparator (UPDATED SCORING LOGIC)

{{ system_prompt_json }}

Compare the blind reader’s reconstruction with the original story.

ORIGINAL STORY:
{{ original_text }}

BLIND READER RESULT:
{{ reconstructed_story }}

SCORING RUBRIC:

- plot_recall (30%): Did the reader understand the main events?
- emotional_alignment (30%): Did the reader feel the intended emotions?
- visual_delivery (25%): Did the panels use visual storytelling effectively?
- character_identifiability (15%): Could the reader distinguish characters?

OUTPUT SCHEMA:
{
"scores": {
"plot_recall": 0.0-1.0,
"emotional_alignment": 0.0-1.0,
"visual_delivery": 0.0-1.0,
"character_identifiability": 0.0-1.0
},
"weighted_score": 0.0-1.0,
"failure_points": [
"specific panels or patterns that weakened storytelling"
],
"repair_suggestions": [
"concrete, actionable fixes (e.g., reduce repetition, add visual implication)"
]
}

⸻

🧠 Why This Works (for your ticket)
• No hard constraints → avoids breaking valid continuity scenes
• Soft scoring pressure → nudges toward webtoon-native storytelling
• Blind test now punishes animation-like repetition
• Panel variety becomes emergent, not enforced

This is exactly the shift you described:

“강제보다는 추천 + 평가 구조로 방향을 잡는 것”
