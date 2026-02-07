# Analyzed Webtoon Styles

Based on analysis of 15 example webtoon screenshots, we've extracted 6 new image style profiles that capture the core aesthetic of modern Korean webtoons.

## Style Overview

All analyzed styles share these core characteristics:
- **Clean confident linework** with variable weight
- **Semi-realistic proportions** with large expressive eyes
- **Polished digital painting** with soft brushwork
- **Modern clean aesthetic** with smooth gradient shading
- **Warm neutral color bias** for everyday scenes
- **Natural cinematic lighting** approach

## Available Styles

### 1. ANALYZED_WEBTOON_BASE
**Core versatile style for general storytelling**

- **Aesthetic**: Modern Korean Webtoon with Clean Digital Rendering
- **Best For**: Versatile modern storytelling, balanced emotional range, everyday life to drama
- **Key Elements**:
  - Clean variable linework
  - Warm neutral palette (beiges, browns, creams)
  - Natural ambient lighting with soft directional light
  - Soft depth of field with clear foreground/background separation

**Use When**: You need a balanced, professional webtoon style that works for most scenes

---

### 2. ANALYZED_ROMANTIC_WEBTOON
**Warm romantic scenes with golden hour lighting**

- **Aesthetic**: Romantic Korean Webtoon with Golden Hour Warmth and Soft Focus
- **Best For**: Romance, tender moments, emotional intimacy, heartwarming scenes
- **Key Elements**:
  - Golden hour lighting with warm glow
  - Soft sparkles and light particles
  - Warm saturated palette
  - Intimate framing with soft background blur

**Use When**: Romantic dialogue, confession scenes, tender emotional moments

---

### 3. ANALYZED_TENSE_WEBTOON
**High-contrast dramatic scenes with cool tones**

- **Aesthetic**: Tense Dramatic Korean Webtoon with Cool Tones and High Contrast
- **Best For**: Tension, confrontation, dramatic peaks, intense emotions, suspense
- **Key Elements**:
  - Harsh shadows with dramatic side lighting
  - Cool blue-purple tones
  - High contrast with sharp focus
  - Tight cropping on faces

**Use When**: Confrontations, suspenseful moments, emotional peaks, tense dialogue

---

### 4. ANALYZED_ACTION_WEBTOON
**Dynamic movement with speed lines and vibrant energy**

- **Aesthetic**: Dynamic Action Korean Webtoon with Bold Movement and Vibrant Energy
- **Best For**: Action sequences, high energy, dynamic movement, intense activity
- **Key Elements**:
  - Speed lines and motion blur
  - Vibrant saturated colors
  - Dynamic angles and exaggerated perspective
  - Bold directional lines

**Use When**: Fight scenes, chase sequences, sports action, dynamic movement

---

### 5. ANALYZED_QUIET_WEBTOON
**Contemplative moments with soft atmosphere**

- **Aesthetic**: Quiet Contemplative Korean Webtoon with Soft Atmosphere and Natural Light
- **Best For**: Quiet moments, contemplation, peaceful scenes, introspective storytelling
- **Key Elements**:
  - Atmospheric haze and soft natural light
  - Warm neutrals with low saturation
  - Environmental detail and storytelling
  - Gentle depth separation

**Use When**: Reflective moments, establishing shots, peaceful daily life, introspection

---

### 6. ANALYZED_DRAMATIC_WEBTOON
**Emotional climax with cinematic lighting**

- **Aesthetic**: High Drama Korean Webtoon with Cinematic Lighting and Emotional Intensity
- **Best For**: Dramatic peaks, emotional climax, intense feelings, pivotal story moments
- **Key Elements**:
  - Dramatic cinematic lighting
  - High saturation for emotional peaks
  - Expressive linework
  - Emotional atmospheric effects

**Use When**: Story climax, emotional revelations, pivotal decisions, intense reactions

---

## Usage in Code

```python
from app.core.image_styles import IMAGE_STYLE_PROFILES, get_style_semantic_hint

# Get style prompt
romantic_style = IMAGE_STYLE_PROFILES["ANALYZED_ROMANTIC_WEBTOON"]["prompt"]

# Get semantic description for LLM
style_hint = get_style_semantic_hint("ANALYZED_ROMANTIC_WEBTOON")
print(style_hint)
# Output:
# AESTHETIC: Romantic Korean Webtoon with Golden Hour Warmth and Soft Focus
# ELEMENTS: Golden hour lighting, Soft sparkles, Warm saturated palette, Intimate framing
# BEST FOR: Romance, tender moments, emotional intimacy, heartwarming scenes
```

## Style Selection Guide

### By Scene Type

| Scene Type | Recommended Style |
|------------|------------------|
| Romantic dialogue | ANALYZED_ROMANTIC_WEBTOON |
| Confrontation | ANALYZED_TENSE_WEBTOON |
| Action sequence | ANALYZED_ACTION_WEBTOON |
| Quiet reflection | ANALYZED_QUIET_WEBTOON |
| Emotional climax | ANALYZED_DRAMATIC_WEBTOON |
| General scenes | ANALYZED_WEBTOON_BASE |

### By Emotional Tone

| Emotion | Recommended Style |
|---------|------------------|
| Tender, warm | ANALYZED_ROMANTIC_WEBTOON |
| Tense, anxious | ANALYZED_TENSE_WEBTOON |
| Energetic, dynamic | ANALYZED_ACTION_WEBTOON |
| Calm, peaceful | ANALYZED_QUIET_WEBTOON |
| Intense, dramatic | ANALYZED_DRAMATIC_WEBTOON |
| Neutral, balanced | ANALYZED_WEBTOON_BASE |

### By Lighting Mood

| Lighting | Recommended Style |
|----------|------------------|
| Golden hour, warm | ANALYZED_ROMANTIC_WEBTOON |
| Cool, harsh shadows | ANALYZED_TENSE_WEBTOON |
| Dynamic, directional | ANALYZED_ACTION_WEBTOON |
| Soft, natural ambient | ANALYZED_QUIET_WEBTOON |
| Cinematic, dramatic | ANALYZED_DRAMATIC_WEBTOON |
| Balanced, natural | ANALYZED_WEBTOON_BASE |

## Comparison with Existing Styles

### vs SOFT_ROMANTIC_WEBTOON
- **SOFT_ROMANTIC_WEBTOON**: More pastel, ethereal, dreamy with heavy bokeh
- **ANALYZED_ROMANTIC_WEBTOON**: More grounded, golden hour warmth, realistic romance

### vs CLEAN_MODERN_WEBTOON
- **CLEAN_MODERN_WEBTOON**: More neutral, studio lighting, commercial polish
- **ANALYZED_WEBTOON_BASE**: Warmer bias, more cinematic, natural lighting

### vs OPERATION_TRUE_LOVE
- **OPERATION_TRUE_LOVE**: Muted tones, minimalist lines, film-inspired grading
- **ANALYZED_DRAMATIC_WEBTOON**: Higher saturation, bolder lines, more expressive

## Technical Details

All analyzed styles follow this structure:

```
[MEDIUM: Korean Webtoon - Style Variant]
Base aesthetic description

[VISUAL BEAT: Beat Type]
Narrative rhythm and pacing

[LINEWORK: Line Style]
Line weight and quality description

[ILLUMINATOR: Lighting Setup]
Light direction, shadows, atmosphere

[COLORIST: Color Palette]
Color choices, temperature, saturation

[EFFECTS: Visual Effects]
Motion, atmosphere, emotional effects

[FINISHER: Final Polish]
Quality markers and finishing touches
```

This structure ensures consistency while allowing for emotional and narrative variation.

## Source

These styles were extracted from 15 webtoon screenshots using the `webtoon_style_analysis` skill. The analysis identified:
- Shot composition patterns
- Visual beat rhythms
- Line art characteristics
- Color language
- Lighting approaches
- Character rendering style
- Background treatment
- Visual effects usage
- Emotional visual language

For detailed analysis, see: `app/assets/example_webtoon/STYLE_GUIDE.md`
