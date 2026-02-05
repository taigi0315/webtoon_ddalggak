# Webtoon Style Extraction Prompt

Analyze the provided webtoon images and extract a detailed style guide that can be used to generate new images matching this artistic style.

## Analysis Framework

### 1. Shot Types & Framing
- **Establishing shots**: How wide shots set scenes (backgrounds, environment detail)
- **Medium shots**: Character framing for dialogue and interaction
- **Close-ups**: Emotional emphasis, detail level on faces
- **Extreme close-ups**: Intensity moments (eyes, hands, objects)
- **Action shots**: Dynamic movement, perspective distortion
- Panel shape/aspect ratio preferences (vertical scroll format)

### 2. Visual Beats (Narrative Rhythm)
- **DETAIL beats**: Small, intimate moments (objects, expressions, textures)
- **ACTION beats**: Movement, gestures, physical dynamics
- **REACTION beats**: Emotional responses, facial expressions
- How these beats alternate to create pacing

### 3. Line Work
- Line weight variation (thick/thin, consistent/variable)
- Line quality (clean/sketchy, smooth/textured, confident/delicate)
- Outline treatment (bold contours, soft edges, selective outlines)
- Detail density (highly rendered vs simplified areas)
- Line style for different elements (characters vs backgrounds vs effects)

### 4. Color Language
- **Dominant palette**: Primary colors and their emotional associations
- **Color temperature**: Warm/cool bias and shifts
- **Saturation strategy**: Vibrant, muted, desaturated, or mixed approach
- **Color coding**: How colors signal mood, time, or character states
- **Contrast levels**: High contrast vs subtle gradations
- Background color treatment vs character colors

### 5. Lighting & Atmosphere
- **Light direction**: Top-down, dramatic side, ambient, backlighting
- **Mood lighting**: How light creates emotional tone
- **Shadow rendering**: Hard-edge, gradient, colored shadows, shadow shapes
- **Highlight style**: Sharp specular, soft glow, rim lighting
- **Atmospheric effects**: Fog, haze, light rays, darkness gradients
- **Time of day indicators**: Color temperature and light quality

### 6. Depth & Spatial Design
- **Foreground/middleground/background** layering clarity
- **Depth cues**: Size scaling, atmospheric perspective, overlap
- **Focus control**: Sharp vs blurred areas, depth of field simulation
- **Spatial compression**: Flat graphic vs deep realistic space

### 7. Character Rendering Style
- **Proportions**: Realistic, stylized, chibi, variable by emotion
- **Facial features**: Eye complexity, nose/mouth simplification level
- **Expression range**: Subtle to exaggerated spectrum
- **Anatomy approach**: Realistic structure vs graphic simplification
- **Clothing/texture detail**: Fabric rendering, pattern treatment

### 8. Background Treatment
- **Detail philosophy**: Photorealistic, stylized, minimal, abstract
- **Texture vs flat**: Surface quality rendering
- **Perspective accuracy**: Technical vs expressive perspective
- **Environment storytelling**: How much background tells the story

### 9. Visual Effects & Techniques
- **Motion indicators**: Speed lines, blur, multiples, impact frames
- **Emotional effects**: Sparkles, flowers, dark auras, symbolic imagery
- **Screentone/patterns**: Dot patterns, gradient screens, textures
- **Panel transitions**: Fade, blur, seamless scroll connections
- **Text integration**: Speech bubble style, SFX treatment

### 10. Emotional Visual Language
- **Intimacy markers**: Soft focus, warm colors, close framing
- **Tension indicators**: Harsh shadows, cool colors, tight crops
- **Joy/lightness**: Bright palettes, soft edges, open compositions
- **Drama/intensity**: High contrast, dynamic angles, bold lines
- How visual style shifts with emotional beats

### 11. Artistic Identity
- **Overall aesthetic**: Korean manhwa, Japanese manga, Western, hybrid
- **Digital rendering**: Brush quality, blending technique, texture overlays
- **Stylistic consistency**: Uniform vs variable style across panels
- **Distinctive signatures**: Unique visual quirks or trademark techniques

## Output Format

Provide a **Webtoon Style Prompt** structured as:
```
=== WEBTOON VISUAL STYLE GUIDE ===

CORE AESTHETIC: [fundamental style identity]

SHOT COMPOSITION:
- Establishing: [wide shot characteristics]
- Medium: [dialogue/interaction framing]
- Close-up: [emotional beat treatment]
- Action: [dynamic movement style]

VISUAL BEATS RHYTHM:
- Detail beats: [intimate moment rendering]
- Action beats: [movement and gesture style]
- Reaction beats: [emotional response treatment]

LINE ART:
[line weight, quality, detail density, stylistic approach]

COLOR PALETTE:
[dominant colors, temperature, saturation, emotional coding]

LIGHTING & MOOD:
[light direction, shadow style, atmospheric effects, emotional tone]

DEPTH & SPACE:
[layering approach, focus control, perspective treatment]

CHARACTER STYLE:
[proportions, facial features, expression range, anatomy approach]

BACKGROUNDS:
[detail level, texture approach, environmental storytelling]

EFFECTS & TECHNIQUES:
[motion, emotion indicators, screentone, transitions]

EMOTIONAL LANGUAGE:
[how visuals shift with narrative beats]

---

IMAGE GENERATION PROMPT TEMPLATE:
"[Core aesthetic], [shot type], [visual beat type], [line art style], [color approach], [lighting mood], [depth treatment], [character style], [background approach], [relevant effects], [emotional tone]"

EXAMPLE:
"Korean webtoon style, medium shot, reaction beat, clean confident linework with variable weight, warm saturated palette with soft shadows, gentle top lighting creating intimate mood, moderate depth with soft background blur, semi-realistic proportions with expressive eyes, simplified background suggesting cafe interior, soft focus effect, tender emotional tone"
```

## Usage

Combine this style guide with scene descriptions:

**[EXTRACTED STYLE] + [Scene Description]**

Example:
"[Your style guide] + Young woman with long black hair, sitting alone at a cafe table, worried expression while looking at her phone screen, afternoon window light from the left"