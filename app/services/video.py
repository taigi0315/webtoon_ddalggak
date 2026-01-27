"""Video composition service for webtoon exports.

Combines rendered scene images with dialogue bubbles to create a vertical scroll video.
"""
from __future__ import annotations

import logging
import os
import tempfile
import uuid
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger(__name__)


@dataclass
class DialogueBubbleData:
    """Dialogue bubble for video composition."""
    text: str
    speaker: str
    x: float  # Normalized 0-1
    y: float  # Normalized 0-1
    width: float  # Normalized 0-1
    height: float  # Normalized 0-1


@dataclass
class SceneFrameData:
    """Scene data for video composition."""
    image_path: str
    dialogues: list[DialogueBubbleData]
    duration_seconds: float = 3.0


def calculate_text_duration(text: str, base_duration: float = 2.0, chars_per_second: float = 15.0) -> float:
    """Calculate display duration based on text length."""
    reading_time = len(text) / chars_per_second
    return max(base_duration, reading_time)


def render_dialogue_bubble(
    draw: ImageDraw.ImageDraw,
    bubble: DialogueBubbleData,
    image_width: int,
    image_height: int,
    font: ImageFont.FreeTypeFont | None = None,
) -> None:
    """Render a dialogue bubble onto an image."""
    # Calculate pixel positions
    x = int(bubble.x * image_width)
    y = int(bubble.y * image_height)
    w = int(bubble.width * image_width)
    h = int(bubble.height * image_height)

    # Draw bubble background (rounded rectangle)
    padding = 10
    bubble_rect = [x, y, x + w, y + h]
    draw.rounded_rectangle(bubble_rect, radius=15, fill="white", outline="black", width=2)

    # Draw text
    text_x = x + padding
    text_y = y + padding

    if font is None:
        try:
            font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 16)
        except Exception:
            font = ImageFont.load_default()

    # Word wrap text
    max_width = w - 2 * padding
    words = bubble.text.split()
    lines = []
    current_line = []

    for word in words:
        test_line = " ".join(current_line + [word])
        bbox = draw.textbbox((0, 0), test_line, font=font)
        if bbox[2] - bbox[0] <= max_width:
            current_line.append(word)
        else:
            if current_line:
                lines.append(" ".join(current_line))
            current_line = [word]

    if current_line:
        lines.append(" ".join(current_line))

    # Draw each line
    line_height = 20
    for i, line in enumerate(lines):
        draw.text((text_x, text_y + i * line_height), line, fill="black", font=font)


def compose_scene_image(
    image_path: str,
    dialogues: list[DialogueBubbleData],
    output_path: str,
) -> str:
    """Compose a scene image with dialogue bubbles overlaid."""
    # Load image
    img = Image.open(image_path)
    if img.mode != "RGBA":
        img = img.convert("RGBA")

    # Create drawing context
    draw = ImageDraw.Draw(img)

    # Render each dialogue bubble
    for bubble in dialogues:
        render_dialogue_bubble(draw, bubble, img.width, img.height)

    # Save composed image
    img.save(output_path, "PNG")
    return output_path


def generate_webtoon_video(
    scenes: list[SceneFrameData],
    output_path: str,
    fps: int = 30,
    scroll_speed: float = 100.0,  # pixels per second
    target_width: int = 720,
) -> str:
    """Generate a vertical scroll video from scene images.

    Args:
        scenes: List of scene frame data with images and dialogues
        output_path: Path to save the output video
        fps: Frames per second
        scroll_speed: Vertical scroll speed in pixels per second
        target_width: Target video width (height calculated to maintain aspect ratio)

    Returns:
        Path to the generated video file
    """
    try:
        from moviepy.editor import ImageClip, concatenate_videoclips, CompositeVideoClip
    except ImportError:
        logger.error("moviepy not installed - video export not available")
        raise RuntimeError("Video export requires moviepy. Install with: pip install moviepy")

    if not scenes:
        raise ValueError("No scenes provided for video generation")

    clips = []
    temp_dir = tempfile.mkdtemp()

    try:
        for i, scene in enumerate(scenes):
            # Check if image exists
            if not os.path.exists(scene.image_path):
                logger.warning("Scene image not found: %s", scene.image_path)
                continue

            # Compose image with dialogues
            if scene.dialogues:
                composed_path = os.path.join(temp_dir, f"composed_{i}.png")
                compose_scene_image(scene.image_path, scene.dialogues, composed_path)
                img_path = composed_path
            else:
                img_path = scene.image_path

            # Calculate duration - base duration plus time for dialogue reading
            duration = scene.duration_seconds
            for dialogue in scene.dialogues:
                duration += calculate_text_duration(dialogue.text)

            # Create image clip
            clip = ImageClip(img_path, duration=duration)

            # Resize to target width while maintaining aspect ratio
            if clip.w != target_width:
                clip = clip.resize(width=target_width)

            clips.append(clip)

        if not clips:
            raise ValueError("No valid scenes could be processed")

        # Concatenate all clips
        final_clip = concatenate_videoclips(clips, method="compose")

        # Write video file
        final_clip.write_videofile(
            output_path,
            fps=fps,
            codec="libx264",
            audio=False,
            logger=None,  # Suppress moviepy output
        )

        # Cleanup
        final_clip.close()
        for clip in clips:
            clip.close()

        return output_path

    finally:
        # Cleanup temp files
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)


def generate_video_from_export_data(
    export_metadata: dict,
    media_root: str,
    output_dir: str,
) -> str:
    """Generate video from export job metadata.

    Args:
        export_metadata: Export job metadata containing scene info
        media_root: Root directory for media files
        output_dir: Directory to save output video

    Returns:
        Path to the generated video file
    """
    scenes_data = export_metadata.get("scenes", [])
    if not scenes_data:
        raise ValueError("No scenes in export metadata")

    frames: list[SceneFrameData] = []

    for scene_info in scenes_data:
        image_url = scene_info.get("image_url")
        if not image_url:
            continue

        # Convert URL to file path
        if image_url.startswith("/media/"):
            image_path = os.path.join(media_root, image_url[7:])  # Remove /media/ prefix
        elif image_url.startswith("media/"):
            image_path = os.path.join(media_root, image_url[6:])
        else:
            image_path = image_url

        # Extract dialogue from layers
        dialogues: list[DialogueBubbleData] = []
        layers = scene_info.get("layers", [])
        for layer in layers:
            if layer.get("layer_type") == "dialogue":
                for obj in layer.get("objects", []):
                    geometry = obj.get("geometry", {})
                    dialogues.append(DialogueBubbleData(
                        text=obj.get("text", ""),
                        speaker=obj.get("speaker", ""),
                        x=geometry.get("x", 0.1),
                        y=geometry.get("y", 0.1),
                        width=geometry.get("w", 0.3),
                        height=geometry.get("h", 0.15),
                    ))

        frames.append(SceneFrameData(
            image_path=image_path,
            dialogues=dialogues,
            duration_seconds=3.0,  # Base duration
        ))

    # Generate output filename
    video_filename = f"webtoon_{uuid.uuid4().hex[:8]}.mp4"
    output_path = os.path.join(output_dir, video_filename)

    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)

    return generate_webtoon_video(frames, output_path)
