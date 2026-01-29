Yep — you’ve identified a real gap: **“image style” (line/color/lighting) is not enough** to match a specific webtoon’s *character design language* (proportions, face shapes, eye style, silhouette, fashion bias, etc.).

So you want a second style artifact:

> **Character Style Profile** = “how this webtoon draws people”

Then character generation uses:

* **Image Style** (rendering look)
* **Character Style** (anatomy/face/silhouette conventions)

Below are **two prompts** you can use with a set of reference images from a webtoon:

1. Extract **Character Style Grammar** (JSON)
2. Generate a **new character prompt pack** using that grammar + your character profile

Both are designed for your app pipeline.

---

# 1) Prompt: Extract Character Style Grammar (from images)

Use this when you downloaded multiple panels from the webtoon.

## SYSTEM

```text
You are a webtoon character design analyst and style system designer.

Analyze the provided images and extract ONLY the reusable character design style
(how people are drawn), not the overall rendering, not the story content.

Return ONLY valid JSON. No markdown. No commentary.
Do not mention copyrighted artists or the title of the webtoon.
Do not describe specific scenes or events.
Generalize into reusable rules.
```

## USER

```text
I am building a webtoon generator.

I provided multiple reference images from ONE webtoon style.
Your task: extract a reusable "Character Style Grammar" that describes
how characters are designed in this style.

Focus on:
- body proportions & silhouette tendencies
- face shape tendencies and stylization level
- eye style, nose/mouth simplification, eyebrows
- hair design language (strand vs shape, volume, highlights)
- typical fashion bias / styling (simple, chic, ornate, streetwear, etc.)
- how age is visually encoded (teen vs adult)
- how emotions are expressed (subtle vs exaggerated)

Do NOT focus on:
- background style
- panel layout
- lighting/color grading (those belong to image_style)
- specific characters from the images

Return JSON using this schema exactly.
```

## OUTPUT JSON SCHEMA

```json
{
  "character_style_id": "string",
  "character_style_name": "string",

  "proportions": {
  "overall_stylization": "realistic|slightly_idealized|stylized",

  "height_tendency": "short|average|tall|very_tall",
  "build_tendency": "slim|average|athletic|curvy|varied",

  "limb_proportion": "balanced|elongated|shortened",
  "head_to_body_ratio": "realistic|slightly_large|large",

  "shoulder_width_tendency_male": "narrow|average|broad|very_broad",
  "chest_volume_tendency_female": "small|medium|full|varied",

  "shoulder_to_hip_bias": "masculine_v|feminine_hourglass|neutral|varied",

  "notes": ["string"]
},

  "faces": {
    "face_shape_tendency": ["oval", "v_shape", "round", "square", "heart", "varied"],
    "jaw_emphasis": "low|medium|high",
    "nose_detail": "minimal|moderate|detailed",
    "mouth_detail": "minimal|moderate|expressive",
    "cheek_detail": "none|subtle|pronounced",
    "notes": ["string"]
  },

  "eyes_and_brows": {
    "eye_emphasis": "low|medium|high",
    "eye_shape_tendency": ["almond", "round", "droopy", "sharp", "varied"],
    "iris_detail": "minimal|moderate|high",
    "lash_emphasis": "low|medium|high",
    "brow_style": "soft|defined|graphic",
    "notes": ["string"]
  },

  "hair_design": {
    "strand_detail": "minimal|moderate|high",
    "shape_language": "chunky_shapes|soft_clumps|fine_strands|mixed",
    "volume_tendency": "low|medium|high",
    "highlight_style": "none|simple|gloss_bands|painterly",
    "notes": ["string"]
  },

  "clothing_bias": {
    "fashion_level": "simple|casual|chic|ornate|varied",
    "silhouette_bias": "fitted|oversized|layered|varied",
    "detail_density": "low|medium|high",
    "common_accessories": ["string"],
    "notes": ["string"]
  },

  "age_cues": {
    "teen_style_bias": ["string"],
    "adult_style_bias": ["string"],
    "notes": ["string"]
  },

  "expression_language": {
    "expression_range": "subtle|moderate|exaggerated",
    "emotion_markers": ["string"],
    "notes": ["string"]
  },

  "do": ["string"],
  "avoid": ["string"]
}
```

This gives you a **character-only style artifact**.

---

# 2) Prompt: Generate Character Prompt Pack (uses character_style + image_style)

Use this when you want to generate a new character (reference sheet / profile image) that matches the webtoon.

## SYSTEM

```text
You are a webtoon character designer.
Return ONLY valid JSON. No markdown. No commentary.
Do not include copyrighted names or references.
The goal is a clean character generation prompt that matches the provided style grammars.
```

## USER (Template)

```text
I want to generate a NEW character reference image that matches a specific webtoon style.

You are given:
1) image_style (rendering look: line/color/lighting)
2) character_style_grammar (how people are designed: proportions/face/eyes/hair/clothes)
3) character_profile (who the character is)

Task:
Write a compact, high-quality character generation prompt pack:
- a single "positive_prompt"
- a "negative_prompt"
- a small set of "prompt_tags" for the UI
- a "composition_spec" for a character reference sheet

Rules:
- The character MUST follow the character_style_grammar for body proportions and face/eye/hair stylization.
- The rendering MUST follow image_style.
- Avoid over-describing; be precise.
- Do NOT force full-body if not needed; but for reference images use a clean full-body neutral pose.
- No text, watermark, or speech bubbles.

Inputs:
image_style:
{IMAGE_STYLE_JSON}

character_style_grammar:
{CHARACTER_STYLE_JSON}

character_profile:
{CHARACTER_PROFILE_JSON}

Return JSON using this schema exactly.
```

## OUTPUT JSON SCHEMA

```json
{
  "composition_spec": {
    "aspect_ratio": "9:16",
    "shot": "full_body_front|half_body|three_quarter",
    "pose": "neutral_standing|neutral_sitting|turnaround",
    "background": "plain|simple_gradient|minimal_room",
    "lighting": "string",
    "notes": ["string"]
  },

  "positive_prompt": "string",
  "negative_prompt": "string",
  "prompt_tags": ["string"]
}
```

---

# How this plugs into your app (recommended)

### New artifact types

* `image_style` (rendering)
* `character_style` (how people are designed)

### Character generation uses

* `image_style + character_style + character_profile`
  → produces **character reference image(s)**

### Scene generation uses

* `image_style + character_style + character registry + refs`
  → produces **scene image**

This is how you get “this webtoon draws tall/slim/fashionable characters” consistently, not just “pastel lighting”.

---

# One practical tip (to reduce identity drift later)

When generating character refs:

* generate **2–4 variants**
* user selects one as canonical
* store it as `reference_image_id`
* later scene prompts use **Reference Image Authority** block (like we discussed)

---

If you want, paste one webtoon’s images + your current image_style JSON, and I can show you what the **character_style_grammar** output should look like (example), so you can validate your extraction pipeline quickly.
