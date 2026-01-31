# Chat Bubble Configuration Guide

## Overview

The chat bubble system uses `app/config/chat_bubble_config.json` to control visual styling, fonts, and animation behavior for dialogue bubbles in webtoon videos.

## Configuration Structure

### 1. Dialogue Types

Four dialogue types are supported, each with customizable styling:

#### Chat (Speech)

```json
"chat": {
  "type": "speech",
  "background_color": "#FFFFFF",
  "border_color": "#000000",
  "border_width": 2,
  "opacity": 0.4,  // 40% transparency
  "font_name": "dialogue",
  "bubble_shape": "ellipse"
}
```

#### Thought

```json
"thought": {
  "background_color": "#F0F8FF",  // Light blue
  "border_color": "#4682B4",
  "opacity": 0.4,
  "bubble_shape": "cloud"
}
```

#### Narration

```json
"narration": {
  "background_color": "#000000",  // Black background
  "text_color": "#FFFFFF",  // White text
  "opacity": 0.6,  // More opaque for readability
  "bubble_shape": "rectangle"
}
```

#### SFX (Sound Effects)

```json
"sfx": {
  "background_color": null,  // No background
  "text_color": "#FF0000",  // Red text
  "opacity": 1.0,
  "bubble_shape": "none",
  "text_stroke": true,
  "stroke_color": "#000000",
  "stroke_width": 2
}
```

### 2. Fonts

Each dialogue type can use a different font:

```json
"fonts": {
  "dialogue": {
    "path": "app/assets/fonts/cs-raving-drawn-font/CsravingdrawnRegularDemo-DYjD1.otf",
    "size": 16,
    "scale": 1.8
  },
  "sfx": {
    "path": "app/assets/fonts/cs-raving-drawn-font/CsravingdrawnRegularDemo-DYjD1.otf",
    "size": 24,
    "scale": 2.5,
    "bold": true
  }
}
```

### 3. Animation Settings

Controls sequential bubble appearance and timing:

```json
"animation": {
  "min_stay_time": 2.0,           // Minimum time a bubble stays visible (seconds)
  "time_per_character": 0.05,     // Additional time per character (seconds)
  "transition_duration": 0.3,     // Fade-in duration (seconds)
  "sequential": true              // Enable/disable sequential animation
}
```

## Tuning Guide

### Adjusting Opacity

To make bubbles more/less transparent:

```json
"opacity": 0.4  // Range: 0.0 (fully transparent) to 1.0 (fully opaque)
```

**Recommended values:**

- Chat/Thought: 0.3 - 0.5
- Narration: 0.6 - 0.8 (needs higher opacity for black background)
- SFX: 1.0 (no transparency)

### Adjusting Stay Time

The formula for bubble stay time is:

```
stay_time = min_stay_time + (text_length * time_per_character)
```

**Examples:**

- Short text (10 chars): 2.0 + (10 × 0.05) = 2.5 seconds
- Long text (50 chars): 2.0 + (50 × 0.05) = 4.5 seconds

**Tuning:**

- Increase `min_stay_time` for slower pacing
- Increase `time_per_character` to give more reading time
- Decrease both for faster-paced scenes

### Disable Sequential Animation

To show all bubbles at once (like original behavior):

```json
"animation": {
  "sequential": false
}
```

### Custom Colors

Colors use hex format. Examples:

```json
"background_color": "#FFFFFF",  // White
"background_color": "#F0F8FF",  // Alice Blue
"background_color": "#000000",  // Black
"background_color": null,       // No background
```

## Testing Changes

After modifying the config:

1. **Restart the backend** (config is loaded on startup)
2. **Create a test scene** with different dialogue types
3. **Generate video** to see the results
4. **Iterate** based on visual feedback

## Common Adjustments

### Make bubbles more visible:

- Increase `opacity` to 0.5-0.7
- Add stronger `border_color` contrast
- Increase `border_width` to 3

### Speed up animation:

- Decrease `min_stay_time` to 1.5
- Decrease `time_per_character` to 0.03
- Decrease `transition_duration` to 0.2

### Slow down animation:

- Increase `min_stay_time` to 3.0
- Increase `time_per_character` to 0.08
- Increase `transition_duration` to 0.5

## Advanced: Adding New Bubble Types

To add a new dialogue type:

1. Add configuration in `chat_bubble_config.json`:

```json
"whisper": {
  "type": "whisper",
  "background_color": "#E6E6FA",
  "border_color": "#9370DB",
  "opacity": 0.3,
  "font_name": "dialogue",
  "bubble_shape": "ellipse"
}
```

2. No code changes needed - the system reads from config automatically

3. Use in frontend by setting `bubble_type: "whisper"`

## Troubleshooting

**Bubbles not showing:**

- Check font path is correct
- Ensure opacity > 0
- Verify background_color is not null (unless intended)

**Text not readable:**

- Increase opacity
- Adjust text_color for contrast
- Increase font size/scale

**Animation too fast/slow:**

- Adjust min_stay_time and time_per_character
- Check if sequential mode is enabled

## File Location

Config file: `/Users/changikchoi/Documents/Github/ssuljaengi_v4/app/config/chat_bubble_config.json`

Video service: `/Users/changikchoi/Documents/Github/ssuljaengi_v4/app/services/video.py`
