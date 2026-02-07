"""
Webtoon Style Definitions
Extracted from example webtoon analysis
"""

# Base style prompt that should be included in all generations
BASE_STYLE = "Korean webtoon style, clean confident linework with variable weight, semi-realistic proportions with large expressive eyes and detailed hair"

# Shot type variations
SHOT_TYPES = {
    "establishing": "wide establishing shot, deep layered depth with atmospheric perspective, detailed but stylized background",
    "medium": "medium shot, moderate depth with soft background blur, simplified background",
    "closeup": "close-up shot, shallow depth of field, minimal background detail",
    "extreme_closeup": "extreme close-up, very shallow depth, abstract or gradient background",
    "action": "dynamic action shot, exaggerated perspective depth, simplified background with motion effects"
}

# Visual beat types (narrative rhythm)
VISUAL_BEATS = {
    "detail": "detail beat, high detail on subject, textural rendering, intimate framing",
    "action": "action beat, dynamic composition, bold effects, energetic pacing",
    "reaction": "reaction beat, emotional emphasis, expressive features, focused composition"
}

# Color approaches
COLOR_MOODS = {
    "warm_intimate": "warm saturated palette with soft shadows, golden lighting",
    "cool_tense": "cool-toned palette with high contrast, blue-purple tones",
    "neutral_calm": "warm neutral palette with soft gradients, balanced temperature",
    "vibrant_energetic": "saturated vibrant palette, bold color contrasts",
    "desaturated_melancholy": "desaturated muted palette, low saturation, cool bias"
}

# Lighting setups
LIGHTING_MOODS = {
    "intimate": "gentle window lighting creating intimate mood, soft shadows",
    "dramatic": "dramatic side lighting with harsh shadows, high contrast",
    "natural": "natural ambient lighting, soft fill light, balanced exposure",
    "golden_hour": "warm golden hour lighting, long soft shadows, warm glow",
    "night": "cool blue night lighting, selective highlights, deep shadows",
    "backlit": "strong backlighting creating silhouette, rim lighting on edges"
}

# Background detail levels
BACKGROUND_STYLES = {
    "detailed": "detailed but stylized architectural background, clear environmental context",
    "simplified": "simplified background suggesting location, atmospheric treatment",
    "minimal": "minimal background with gradient fill, focus on characters",
    "blurred": "soft blurred background, depth of field effect, environmental suggestion",
    "abstract": "abstract gradient background, pure mood and color"
}

# Visual effects
EFFECTS = {
    "soft_focus": "soft focus effect, gentle blur",
    "motion": "motion blur and speed lines, dynamic movement",
    "sparkle": "sparkle and light particle effects, romantic atmosphere",
    "glow": "subtle glow effects, atmospheric lighting",
    "impact": "impact frames with bold effects, action emphasis",
    "none": ""
}

# Emotional tones
EMOTIONAL_TONES = {
    "tender": "tender emotional tone, warm and intimate",
    "tense": "tense dramatic tone, high emotional stakes",
    "energetic": "energetic intense tone, dynamic and bold",
    "calm": "calm contemplative tone, peaceful atmosphere",
    "melancholic": "melancholic reflective tone, subdued mood",
    "joyful": "joyful lighthearted tone, bright and positive"
}


def build_style_prompt(
    shot_type: str = "medium",
    visual_beat: str = "reaction",
    color_mood: str = "warm_intimate",
    lighting: str = "intimate",
    background: str = "simplified",
    effects: str = "soft_focus",
    emotional_tone: str = "tender"
) -> str:
    """
    Build a complete style prompt from components.
    
    Args:
        shot_type: Type of shot framing (establishing, medium, closeup, extreme_closeup, action)
        visual_beat: Narrative rhythm type (detail, action, reaction)
        color_mood: Color palette approach (warm_intimate, cool_tense, neutral_calm, vibrant_energetic, desaturated_melancholy)
        lighting: Lighting setup (intimate, dramatic, natural, golden_hour, night, backlit)
        background: Background detail level (detailed, simplified, minimal, blurred, abstract)
        effects: Visual effects (soft_focus, motion, sparkle, glow, impact, none)
        emotional_tone: Overall emotional tone (tender, tense, energetic, calm, melancholic, joyful)
    
    Returns:
        Complete style prompt string
    """
    components = [
        BASE_STYLE,
        SHOT_TYPES.get(shot_type, SHOT_TYPES["medium"]),
        VISUAL_BEATS.get(visual_beat, VISUAL_BEATS["reaction"]),
        COLOR_MOODS.get(color_mood, COLOR_MOODS["warm_intimate"]),
        LIGHTING_MOODS.get(lighting, LIGHTING_MOODS["intimate"]),
        BACKGROUND_STYLES.get(background, BACKGROUND_STYLES["simplified"]),
        EFFECTS.get(effects, ""),
        EMOTIONAL_TONES.get(emotional_tone, EMOTIONAL_TONES["tender"])
    ]
    
    # Filter out empty strings and join
    return ", ".join(filter(None, components))


def build_scene_prompt(
    scene_description: str,
    shot_type: str = "medium",
    visual_beat: str = "reaction",
    color_mood: str = "warm_intimate",
    lighting: str = "intimate",
    background: str = "simplified",
    effects: str = "soft_focus",
    emotional_tone: str = "tender"
) -> str:
    """
    Build a complete prompt combining style and scene description.
    
    Args:
        scene_description: Specific scene content (characters, actions, setting details)
        shot_type: Type of shot framing
        visual_beat: Narrative rhythm type
        color_mood: Color palette approach
        lighting: Lighting setup
        background: Background detail level
        effects: Visual effects
        emotional_tone: Overall emotional tone
    
    Returns:
        Complete prompt: [style] + [scene description]
    """
    style = build_style_prompt(
        shot_type=shot_type,
        visual_beat=visual_beat,
        color_mood=color_mood,
        lighting=lighting,
        background=background,
        effects=effects,
        emotional_tone=emotional_tone
    )
    
    return f"{style} + {scene_description}"


# Preset style combinations for common scene types
STYLE_PRESETS = {
    "romantic_dialogue": {
        "shot_type": "medium",
        "visual_beat": "reaction",
        "color_mood": "warm_intimate",
        "lighting": "golden_hour",
        "background": "blurred",
        "effects": "soft_focus",
        "emotional_tone": "tender"
    },
    "tense_confrontation": {
        "shot_type": "closeup",
        "visual_beat": "reaction",
        "color_mood": "cool_tense",
        "lighting": "dramatic",
        "background": "minimal",
        "effects": "none",
        "emotional_tone": "tense"
    },
    "action_sequence": {
        "shot_type": "action",
        "visual_beat": "action",
        "color_mood": "vibrant_energetic",
        "lighting": "dramatic",
        "background": "simplified",
        "effects": "motion",
        "emotional_tone": "energetic"
    },
    "quiet_moment": {
        "shot_type": "medium",
        "visual_beat": "detail",
        "color_mood": "neutral_calm",
        "lighting": "natural",
        "background": "detailed",
        "effects": "soft_focus",
        "emotional_tone": "calm"
    },
    "emotional_peak": {
        "shot_type": "closeup",
        "visual_beat": "reaction",
        "color_mood": "vibrant_energetic",
        "lighting": "dramatic",
        "background": "abstract",
        "effects": "glow",
        "emotional_tone": "tense"
    },
    "establishing_scene": {
        "shot_type": "establishing",
        "visual_beat": "detail",
        "color_mood": "neutral_calm",
        "lighting": "natural",
        "background": "detailed",
        "effects": "none",
        "emotional_tone": "calm"
    }
}


def build_preset_prompt(preset_name: str, scene_description: str) -> str:
    """
    Build a prompt using a preset style combination.
    
    Args:
        preset_name: Name of the preset (romantic_dialogue, tense_confrontation, etc.)
        scene_description: Specific scene content
    
    Returns:
        Complete prompt with preset style
    """
    preset = STYLE_PRESETS.get(preset_name)
    if not preset:
        raise ValueError(f"Unknown preset: {preset_name}. Available: {list(STYLE_PRESETS.keys())}")
    
    return build_scene_prompt(scene_description, **preset)


# Example usage
if __name__ == "__main__":
    # Example 1: Custom style combination
    custom_prompt = build_scene_prompt(
        scene_description="young woman with long black hair in casual sweater, worried expression while looking at phone, cafe setting",
        shot_type="medium",
        visual_beat="reaction",
        color_mood="warm_intimate",
        lighting="intimate",
        background="blurred",
        effects="soft_focus",
        emotional_tone="tender"
    )
    print("Custom prompt:")
    print(custom_prompt)
    print()
    
    # Example 2: Using preset
    preset_prompt = build_preset_prompt(
        "romantic_dialogue",
        "two characters sitting across from each other at cafe table, gentle smiles, afternoon light"
    )
    print("Preset prompt (romantic_dialogue):")
    print(preset_prompt)
    print()
    
    # Example 3: Action scene
    action_prompt = build_preset_prompt(
        "action_sequence",
        "character running through crowded street, dynamic movement, determined expression"
    )
    print("Preset prompt (action_sequence):")
    print(action_prompt)
