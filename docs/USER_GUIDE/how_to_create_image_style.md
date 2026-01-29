Perfect — now I fully understand the exact workflow you want 👍
You want **one single prompt** that you can:

* attach **multiple images from one webtoon / art style**
* run **once**
* and get back a **hybrid style definition**:

  * structured enough to be controllable (not too coarse)
  * but still rich and expressive
* that you can **register as a new image style** in your app

Below is the **final, correct prompt** for that purpose.
This is the one I’d actually ship.

---

# Webtoon Art Style Registration Prompt

### (Image → Style Grammar Generator, Hybrid Control)

You will provide:

* **Multiple images** (same webtoon / same artist / same style)
* **This prompt**
* The output becomes a **new style entry** in your system

---

## SYSTEM PROMPT

```text
You are a senior webtoon art director and visual style system designer.

Your task is to analyze multiple reference images that share the same art style
and convert that style into a reusable, controllable style grammar
for an AI-powered webtoon generation system.

You must:
- Focus ONLY on how the images are drawn and rendered
- Ignore characters, story, clothing, or specific scenes
- Generalize the style so it can be reused for any story or characters
- Convert subjective visual impressions into consistent, reusable rules

Return ONLY valid JSON.
No markdown.
No explanations.
No commentary.
No references to specific characters or copyrighted artists.
```

---

## USER PROMPT

```text
I am building a webtoon creation application.

I have provided multiple images that represent ONE consistent webtoon art style.
These images may depict different characters or scenes,
but they all share the same intentional visual style.

Your task:
Extract a reusable art style definition that I can save
and later apply to generate new webtoon scenes.

Important requirements:
- Do NOT describe what is happening in the images.
- Do NOT mention specific characters, objects, or locations.
- Describe HOW the images are drawn, not WHAT they depict.
- Balance structure and flexibility:
  - Use controlled categories where possible
  - Use short descriptive phrases where nuance is important
- The style should be adjustable later at the scene or panel level.

Return the result using the EXACT JSON schema below.
```

---

## OUTPUT JSON SCHEMA

### (Hybrid: structured knobs + descriptive tags)

```json
{
  "style_id": "string",
  "style_name": "string",
  "medium": "digital_webtoon|manhwa|illustration|other",

  "line_art": {
    "line_weight": "very_thin|thin|medium|thick|variable",
    "line_quality": "clean|soft|sketchy|expressive",
    "line_variation": "minimal|moderate|high",
    "edge_feel": "sharp|soft|mixed",
    "outline_emphasis": "low|medium|high",
    "notes": ["string"]
  },

  "color_palette": {
    "palette_character": "pastel|muted|vibrant|natural|desaturated",
    "dominant_hues": ["string"],
    "secondary_hues": ["string"],
    "saturation_bias": "low|medium|high",
    "contrast_bias": "low|medium|high",
    "temperature_bias": "warm|cool|neutral|mixed",
    "notes": ["string"]
  },

  "lighting": {
    "lighting_style": "soft_diffused|cinematic|dramatic|minimal|flat",
    "light_source_feel": "natural|artificial|mixed",
    "shadow_presence": "low|medium|high",
    "highlight_behavior": "subtle|soft_glow|sharp|painterly",
    "mood_keywords": ["string"]
  },

  "rendering": {
    "shading_style": "flat|minimal|soft_gradient|cell_shaded|painterly",
    "detail_density": "low|medium|high",
    "texture_usage": "none|subtle|moderate",
    "surface_finish": "matte|soft_glow|glossy|mixed",
    "notes": ["string"]
  },

  "anatomy_and_expression": {
    "proportion_style": "realistic|slightly_idealized|stylized",
    "facial_expression_range": "subtle|moderate|expressive",
    "eye_emphasis": "low|medium|high",
    "body_silhouette_tendency": ["string"]
  },

  "background_and_space": {
    "background_complexity": "minimal|moderate|detailed",
    "background_focus": "soft|balanced|sharp",
    "use_of_negative_space": "low|medium|high",
    "environment_stylization": "realistic|softened|stylized"
  },

  "panel_and_composition_style": {
    "framing_bias": "cinematic|balanced|character_focused|environment_focused",
    "shot_variety": "low|medium|high",
    "use_of_asymmetry": "low|medium|high",
    "dominant_panel_usage": "rare|occasional|frequent",
    "composition_notes": ["string"]
  },

  "overall_vibe": ["string"],

  "style_constraints": [
    "string"
  ]
}
```

---

## Why this prompt works (and fits your concern)

### 1. Enums are **biases**, not absolutes

* “shadow_presence: medium” doesn’t lock you
* It gives your compiler a **direction**
* You can override per scene/panel later

### 2. Notes + keywords capture nuance

* You don’t lose subtlety
* But you don’t hard-code prose into every scene prompt

### 3. Perfect for your pipeline

This output:

* becomes a **style artifact**
* is stored once
* is merged later with:

  * genre defaults
  * scene overrides
  * panel overrides

---

## How you’ll actually use this in practice

1. Pick a webtoon you like
2. Download ~5–15 representative images
3. Send images + this prompt to the LLM
4. Save the JSON output as:

   * `image_style_v1`
5. Your scene prompt compiler:

   * converts enums → short language
   * injects only relevant parts per panel

---

## One important operational tip

When selecting images:

* Avoid UI-heavy panels (speech bubbles, text)
* Prefer:

  * character-only
  * environment-only
  * emotional close-ups
  * wide establishing shots

This helps the model extract *style*, not layout noise.

---

If you want next, I can:

* design the **style override merge rules** (story → scene → panel)
* or write the **style-to-prompt compiler** that converts this JSON into clean, minimal prompt lines
