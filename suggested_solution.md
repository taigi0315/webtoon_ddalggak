Thanks — seeing the *actual* full prompt makes the problems very concrete. I’ll do two things:

1. **Review what’s wrong + what to take off** (specific lines/sections).
2. Give you a **cleaned “v2” prompt skeleton** that assumes you pass **character reference images**, and fixes panel/layout issues + reduces character dominance.

---

## What’s wrong in this prompt (and why it makes images character-heavy)

### 1) Layout is contradictory and will confuse the model

You say:

* **LAYOUT:** Three stacked vertical panels

…but you define **Panel 1–4** (4 panels). This is a hard inconsistency.

✅ Fix: set **LAYOUT: Four stacked vertical panels** (or remove Panel 4).

---

### 2) “CHARACTER VISUAL REFERENCES” is treated like text-only identity, not actual image refs

Even if you *do* pass images as references via API, the prompt still contains **enormous** character spec blocks. These dominate the token budget and bias composition toward character shots.

✅ Take off: almost all “Base style / Hair / Face / Build” blocks.

Keep only 1–2 lines per character for scene context + outfit.

---

### 3) You are explicitly forcing full-body framing

This line in TECHNICAL REQUIREMENTS is sabotaging shot variety:

* “Full body front view showing head to toe where applicable”

That pushes the model toward full-body character portraits even when panel grammar calls for object focus / negative space.

✅ Remove that line entirely.

Replace with: “Use shot variety; full-body only when it supports the beat.”

---

### 4) You repeatedly restate style and atmosphere per panel

You already have global style guidelines, then each panel repeats “intimate, gentle, pastel-tinted, soft_bokeh” etc. This is wasted tokens and reduces adherence to the actual story beat.

✅ Keep global style once. Per panel: keep only *what’s unique*.

---

### 5) Panel 4 is impossible as written

Panel 4 says:

* extreme close-up of smartphone screen
* “clearly legible: ‘Min-ji: Can’t sleep.’”

But your negative prompt and requirements say:

* “No text, speech bubbles, or watermarks”
* Negative includes “text”

So the model is being asked to both include and exclude text. It will either:

* ignore the “no text” rule, or
* ignore the intended reveal.

✅ Fix options:

* If you truly want no text in image: describe it as **an unreadable notification glow** (message content implied, not legible).
* If you allow text later in post: keep “no text” and treat this panel as “phone lights up with notification”.

---

### 6) Your “Min-ji Base style” contains extreme body instructions

Even if not unsafe, it is *artistically risky* and will bias outputs in unwanted ways and increase failure rate (odd anatomy, oversexualized framing, etc.). Also it contributes heavily to “character-heavy” shots.

✅ Remove the entire Min-ji Base style block.

---

## What to take off (exact sections)

### Remove entirely

* Ji-hoon **Base style** block (the long multi-line)
* Ji-hoon Hair / Face / Build (keep 1 combined line instead)
* Min-ji **Base style** block (entire)
* Min-ji Hair / Face / Build (keep 1 combined line instead)
* TECHNICAL: “Masterpiece best quality…” (noise)
* TECHNICAL: “Full body front view…” (harmful)
* Panel “Environment/Lighting/Atmosphere” repeated fields (keep inside semantics, but not in final render prompt)

### Rewrite

* Panel 4: remove legible text requirement (or relax no-text rule, but you said you want bubbles later, so better keep no text)

### Shorten

* Negative prompt can be shorter:

  * `text, watermark, logo, wrong aspect ratio, blurry, inconsistent characters`

---

## Clean “v2 prompt skeleton” (reference-image aware)

This is how your compiler should output it when you provide character reference images.

> **Key idea:** Text prompt should *not* re-describe the character in 40 lines if an image reference is provided.

### ✅ Version 2 (compact, model-friendly)

```text
CRITICAL: Vertical 9:16 aspect ratio, optimized for vertical scrolling webtoon.

STYLE: Soft Webtoon (soft lineart, pastel palette, gentle lighting).
GENRE: Romance (warm, intimate, emotional beats).
LAYOUT: Four stacked vertical panels (top-to-bottom reading).

IMPORTANT:
- Use shot variety: wide / medium / close / object-focus. Full-body only when needed.
- Leave negative space for later dialogue bubbles.
- No speech bubbles, no watermarks, no readable on-image text.

CHARACTER REFERENCES (provided as image references via API):
- Ji-hoon: young adult Korean male, runner outfit (grey tee + dark jacket + joggers). Emotion: anxious anticipation.
- Min-ji: young adult Korean female, messy bun, cozy casual outfit. Emotion: late-night vulnerability.
(Do NOT over-focus on character beauty shots; prioritize storytelling and environment when required.)

PANELS:
1) Establishing (wide): Ji-hoon in living room on beige sofa, modern lamp glow, phone in hands showing “typing dots” implied by UI glow (no readable text). Mood: quiet suspense.
2) Action/reaction (medium): he slumps and covers face; phone tossed onto sofa cushion; room slightly dimmer. Mood: frustration.
3) Impact silence (negative space): bedroom, Ji-hoon lying awake staring at ceiling; moonlight; lots of empty ceiling space. Mood: sleepless tension.
4) Object-focus reveal (extreme close): phone screen lights up in darkness with a notification glow (message NOT readable). His fingers barely visible. Mood: sudden relief/shock.

NEGATIVE: readable text, watermark, signature, logo, wrong aspect ratio, blurry, inconsistent character identity.
```

This will:

* reduce character dominance
* increase camera/composition variety
* preserve your “video-worthy” single-panel capability later

---

## Your “1 big hero panel” requirement (write-up + how to enforce)

You asked: in critical moments, you want **one full 9:16 panel** (hero image) because you’ll animate it later.

### Add a planning attribute (scene-level)

In your scene planning artifact:

```json
{
  "scene_importance": "setup|build|climax|release|cliffhanger",
  "preferred_layout": "auto|single_panel|2_panels|3_panels|4_panels|5_panels"
}
```

### LayoutResolver rule

* if `scene_importance in {climax, cliffhanger}` → `preferred_layout = single_panel` unless explicitly overridden
* if short episode pacing → distribute:

  * setup: 3–4 panels
  * build: 4–5 panels
  * climax: **1 panel**
  * release: 2–3 panels
  * cliffhanger: **1 panel**

This is not a prompt tweak — it’s a **graph/planning rule**.

---

## Quick checklist for your prompt compiler (so it stops over-describing characters)

If character reference images are supplied:

* ✅ Keep character text description to **<= 2 lines per character**
* ✅ Never include “base style” paragraphs
* ✅ Never include “full body head-to-toe” as global requirement
* ✅ Per panel, describe **environment + shot + action** first; character details last
* ✅ Avoid specifying exact heights (183cm) unless you truly need it

---

If you want, I can also provide a **diff-style rewrite** of your exact prompt (“remove these lines, replace with these”) so you can implement it in your compiler quickly.
