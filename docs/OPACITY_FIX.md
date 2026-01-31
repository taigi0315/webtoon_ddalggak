# Opacity Fix - Technical Details

## Problem

Opacity was applied in the frontend UI but not in the output video.

## Root Cause

When using `PIL.ImageDraw.Draw()` directly on an image, RGBA colors with alpha channel don't get properly composited. The alpha value in the color tuple (r, g, b, a) is ignored when drawing directly.

## Solution

Use **alpha compositing** by:

1. Drawing each bubble on a separate transparent RGBA layer
2. Using `Image.alpha_composite()` to properly blend layers

## Implementation

### Before (Incorrect):

```python
def compose_scene_image(image_path, dialogues, output_path):
    img = Image.open(image_path).convert("RGBA")
    draw = ImageDraw.Draw(img)  # ❌ Alpha values ignored

    for bubble in dialogues:
        render_dialogue_bubble(draw, bubble, ...)  # Opacity not applied

    img.save(output_path, "PNG")
```

### After (Correct):

```python
def compose_scene_image(image_path, dialogues, output_path):
    img = Image.open(image_path).convert("RGBA")
    composite = img.copy()

    for bubble in dialogues:
        # Create separate layer for each bubble
        bubble_layer = Image.new("RGBA", img.size, (255, 255, 255, 0))
        bubble_draw = ImageDraw.Draw(bubble_layer)

        # Draw bubble with RGBA colors
        render_dialogue_bubble(bubble_draw, bubble, ...)

        # ✅ Properly composite with alpha blending
        composite = Image.alpha_composite(composite, bubble_layer)

    final = composite.convert("RGB")
    final.save(output_path, "PNG")
```

## Key Changes

1. **Separate layers**: Each bubble gets its own transparent RGBA layer
2. **Alpha compositing**: `Image.alpha_composite()` properly blends RGBA layers
3. **Correct opacity**: The `opacity` value from config now works correctly

## Testing

Run the test script:

```bash
python test_bubble_opacity.py
```

This generates test images with all four bubble types. Open `/tmp/bubble_opacity_test/test_output.png` to verify:

- Chat bubble background is semi-transparent (you can see the blue background through it)
- Thought bubble has light blue semi-transparent background
- Narration has darker semi-transparent black background
- SFX has no background (fully transparent)

## Performance Impact

**Minimal.** Creating additional RGBA layers has negligible overhead:

- Each layer is just a memory buffer
- Alpha compositing is a fast operation in PIL
- Only affects video generation, not real-time rendering

## Related Files

- `app/services/video.py`: `compose_scene_image()` function
- `app/config/chat_bubble_config.json`: Opacity settings
- `test_bubble_opacity.py`: Test script

## References

- [PIL Alpha Compositing](https://pillow.readthedocs.io/en/stable/reference/Image.html#PIL.Image.alpha_composite)
- [ImageDraw limitations with alpha](https://github.com/python-pillow/Pillow/issues/4744)
