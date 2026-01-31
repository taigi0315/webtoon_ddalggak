"""Test opacity in video generation.

This script tests that opacity is properly applied to dialogue bubbles
in the generated video output.
"""
from pathlib import Path
from PIL import Image, ImageDraw
from app.services.video import DialogueBubbleData, compose_scene_image

# Create a test scene image
test_dir = Path("/tmp/bubble_opacity_test")
test_dir.mkdir(exist_ok=True)

# Create a simple test image (solid color background)
test_img = Image.new("RGB", (720, 1280), (100, 150, 200))  # Blue background
test_img_path = test_dir / "test_scene.png"
test_img.save(test_img_path)

# Create test bubbles with different types
test_bubbles = [
    DialogueBubbleData(
        text="This is a chat bubble with 40% opacity",
        speaker="Character A",
        x=0.5,
        y=0.2,
        width=0.6,
        height=0.15,
        bubble_type="chat"
    ),
    DialogueBubbleData(
        text="This is a thought bubble",
        speaker="Character A",
        x=0.5,
        y=0.4,
        width=0.5,
        height=0.12,
        bubble_type="thought"
    ),
    DialogueBubbleData(
        text="Narration with 60% opacity",
        speaker="Narrator",
        x=0.5,
        y=0.6,
        width=0.7,
        height=0.1,
        bubble_type="narration"
    ),
    DialogueBubbleData(
        text="BOOM!",
        speaker="",
        x=0.5,
        y=0.8,
        width=0.3,
        height=0.1,
        bubble_type="sfx"
    ),
]

# Generate composed image
output_path = test_dir / "test_output.png"
compose_scene_image(str(test_img_path), test_bubbles, str(output_path))

print(f"✅ Test image generated: {output_path}")
print(f"Open the image to verify opacity is applied correctly")
print(f"\nExpected results:")
print(f"  - Chat bubble: White background with 40% opacity (should see blue through it)")
print(f"  - Thought bubble: Light blue background with 40% opacity")
print(f"  - Narration: Black background with 60% opacity, white text")
print(f"  - SFX: No background, red text with black stroke")
