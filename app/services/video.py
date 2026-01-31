"""Video composition service for webtoon exports.

Combines rendered scene images with dialogue bubbles to create a vertical scroll video.
"""
from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
import tempfile
import uuid
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger(__name__)

# Load chat bubble config
CONFIG_PATH = Path(__file__).parent.parent / "config" / "chat_bubble_config.json"
try:
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        CHAT_BUBBLE_CONFIG = json.load(f)
except Exception as e:
    logger.warning("Failed to load chat_bubble_config.json: %s. Using defaults.", e)
    CHAT_BUBBLE_CONFIG = {
        "dialogue": {"chat": {"opacity": 0.4, "font_name": "dialogue"}},
        "fonts": {"dialogue": {"path": "/System/Library/Fonts/Helvetica.ttc", "size": 16}},
        "animation": {"min_stay_time": 2.0, "time_per_character": 0.05}
    }

VIDEO_DIALOGUE_CONFIG = {
    "font_path": "/System/Library/Fonts/Helvetica.ttc",
    "font_size": 16,
    "font_scale": 1.8,
    "padding": 10,
    "line_height": 20,
}


@dataclass
class DialogueBubbleData:
    """Dialogue bubble for video composition."""
    text: str
    speaker: str
    x: float  # Normalized 0-1
    y: float  # Normalized 0-1
    width: float  # Normalized 0-1
    height: float  # Normalized 0-1
    bubble_type: str = "chat"  # chat, thought, narration, sfx


@dataclass
class SceneFrameData:
    """Scene data for video composition."""
    image_path: str
    dialogues: list[DialogueBubbleData]
    duration_seconds: float = 3.0


def calculate_text_duration(text: str, base_duration: float = 2.0, chars_per_second: float = 15.0) -> float:
    """Calculate display duration based on text length using config."""
    animation_config = CHAT_BUBBLE_CONFIG.get("animation", {})
    min_time = animation_config.get("min_stay_time", base_duration)
    time_per_char = animation_config.get("time_per_character", 1.0 / chars_per_second)
    return min_time + len(text) * time_per_char


def render_dialogue_bubble(
    draw: ImageDraw.ImageDraw,
    bubble: DialogueBubbleData,
    image_width: int,
    image_height: int,
    font: ImageFont.FreeTypeFont | None = None,
) -> None:
    """Render a dialogue bubble with type-specific styling."""
    # Get config for bubble type
    bubble_type = bubble.bubble_type or "chat"
    type_config = CHAT_BUBBLE_CONFIG.get("dialogue", {}).get(bubble_type, {})
    
    # Calculate pixel positions
    x = int(bubble.x * image_width)
    y = int(bubble.y * image_height)
    w = int(bubble.width * image_width)
    h = int(bubble.height * image_height)

    # Get styling from config
    bg_color = type_config.get("background_color", "#FFFFFF")
    border_color = type_config.get("border_color", "#000000")
    border_width = type_config.get("border_width", 2)
    opacity = type_config.get("opacity", 0.4)
    text_color = type_config.get("text_color", "#000000")
    bubble_shape = type_config.get("bubble_shape", "ellipse")
    
    # Apply opacity to colors
    if bg_color and bg_color != "null":
        bg_rgba = hex_to_rgba(bg_color, opacity)
    else:
        bg_rgba = None
    
    border_rgba = hex_to_rgba(border_color, 1.0) if border_color else None
    text_rgba = hex_to_rgba(text_color, 1.0)

    # Draw bubble background based on shape
    padding = VIDEO_DIALOGUE_CONFIG["padding"]
    bubble_rect = [x, y, x + w, y + h]
    
    if bubble_shape == "rectangle":
        if bg_rgba:
            draw.rectangle(bubble_rect, fill=bg_rgba, outline=border_rgba, width=border_width)
    elif bubble_shape == "cloud":
        # Simple cloud approximation with multiple circles
        if bg_rgba:
            cloud_radius = min(w, h) // 6
            for offset_x, offset_y in [(0, 0), (w//3, 0), (2*w//3, 0), (w//6, h//4), (5*w//6, h//4)]:
                draw.ellipse(
                    [x + offset_x - cloud_radius, y + offset_y - cloud_radius,
                     x + offset_x + cloud_radius, y + offset_y + cloud_radius],
                    fill=bg_rgba, outline=border_rgba
                )
    elif bubble_shape != "none":
        # Default ellipse/rounded rectangle for chat and thought
        if bg_rgba:
            draw.rounded_rectangle(bubble_rect, radius=15, fill=bg_rgba, outline=border_rgba, width=border_width)

    # Load font
    if font is None:
        font_name = type_config.get("font_name", "dialogue")
        font_config = CHAT_BUBBLE_CONFIG.get("fonts", {}).get(font_name, {})
        font_path = font_config.get("path", VIDEO_DIALOGUE_CONFIG["font_path"])
        font_size = int(font_config.get("size", 16) * font_config.get("scale", 1.8))
        
        try:
            font = ImageFont.truetype(font_path, font_size)
        except Exception as e:
            logger.warning("Failed to load font %s: %s", font_path, e)
            try:
                font = ImageFont.truetype(VIDEO_DIALOGUE_CONFIG["font_path"], 
                                         int(VIDEO_DIALOGUE_CONFIG["font_size"] * VIDEO_DIALOGUE_CONFIG["font_scale"]))
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

    # Center text horizontally and vertically
    line_height = int(VIDEO_DIALOGUE_CONFIG["line_height"] * VIDEO_DIALOGUE_CONFIG["font_scale"])
    total_text_height = line_height * len(lines)
    text_block_width = max(
        (draw.textbbox((0, 0), line, font=font)[2] for line in lines), default=0
    )
    text_x = x + max(padding, (w - text_block_width) // 2)
    text_y = y + max(padding, (h - total_text_height) // 2)

    # Draw text with optional stroke for SFX
    if type_config.get("text_stroke"):
        stroke_color = hex_to_rgba(type_config.get("stroke_color", "#000000"), 1.0)
        stroke_width = type_config.get("stroke_width", 2)
        for i, line in enumerate(lines):
            draw.text((text_x, text_y + i * line_height), line, fill=text_rgba, font=font,
                     stroke_width=stroke_width, stroke_fill=stroke_color)
    else:
        for i, line in enumerate(lines):
            draw.text((text_x, text_y + i * line_height), line, fill=text_rgba, font=font)


def hex_to_rgba(hex_color: str, opacity: float = 1.0) -> tuple[int, int, int, int]:
    """Convert hex color to RGBA tuple with opacity."""
    hex_color = hex_color.lstrip("#")
    if len(hex_color) == 3:
        hex_color = "".join([c*2 for c in hex_color])
    r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
    a = int(opacity * 255)
    return (r, g, b, a)


def compose_scene_image(
    image_path: str,
    dialogues: list[DialogueBubbleData],
    output_path: str,
) -> str:
    """Compose a scene image with dialogue bubbles overlaid with proper opacity support."""
    # Load base image
    img = Image.open(image_path)
    if img.mode != "RGBA":
        img = img.convert("RGBA")
    
    # Create a composite image starting with the base
    composite = img.copy()
    
    # Render each dialogue bubble on a separate layer with proper opacity
    for bubble in dialogues:
        # Create a transparent layer for this bubble
        bubble_layer = Image.new("RGBA", img.size, (255, 255, 255, 0))
        bubble_draw = ImageDraw.Draw(bubble_layer)
        
        # Render the bubble on its own layer
        render_dialogue_bubble(bubble_draw, bubble, img.width, img.height)
        
        # Composite this bubble layer onto the result
        composite = Image.alpha_composite(composite, bubble_layer)
    
    # Convert to RGB for saving (PNG supports RGBA but this ensures compatibility)
    final = composite.convert("RGB")
    final.save(output_path, "PNG")
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
    if shutil.which("ffmpeg") is None:
        logger.error("ffmpeg not installed - video export not available")
        raise RuntimeError("Video export requires ffmpeg. Install ffmpeg and ensure it is on PATH.")

    if not scenes:
        raise ValueError("No scenes provided for video generation")

    temp_dir = tempfile.mkdtemp()
    concat_path = os.path.join(temp_dir, "concat.txt")

    try:
        concat_lines: list[str] = []
        for i, scene in enumerate(scenes):
            # Check if image exists
            if not os.path.exists(scene.image_path):
                logger.warning("Scene image not found: %s", scene.image_path)
                continue


            # Get animation config
            animation_config = CHAT_BUBBLE_CONFIG.get("animation", {})
            sequential = animation_config.get("sequential", True)
            transition_duration = animation_config.get("transition_duration", 0.3)

            # Generate sequential frames if dialogues exist and sequential mode is enabled
            if scene.dialogues and sequential:
                # Sort dialogues by position (top to bottom, left to right) for natural reading order
                sorted_dialogues = sorted(scene.dialogues, key=lambda d: (d.y, d.x))
                
                # Frame 0: Just the image (no dialogue)
                base_duration = scene.duration_seconds
                abs_path = os.path.abspath(scene.image_path)
                concat_lines.append(f"file '{abs_path}'")
                concat_lines.append(f"duration {base_duration:.3f}")
                
                # Frames 1-N: Progressively add each dialogue bubble
                for idx, dialogue in enumerate(sorted_dialogues):
                    # Create image with bubbles up to this point
                    bubbles_to_show = sorted_dialogues[:idx + 1]
                    composed_path = os.path.join(temp_dir, f"scene_{i}_bubble_{idx}.png")
                    compose_scene_image(scene.image_path, bubbles_to_show, composed_path)
                    
                    # Calculate stay time for this bubble
                    stay_time = calculate_text_duration(dialogue.text)
                    
                    # Add transition + stay time
                    # Transition is handled by showing the image briefly
                    abs_composed = os.path.abspath(composed_path)
                    concat_lines.append(f"file '{abs_composed}'")
                    concat_lines.append(f"duration {transition_duration + stay_time:.3f}")
            elif scene.dialogues:
                # Non-sequential mode: show all bubbles at once
                composed_path = os.path.join(temp_dir, f"composed_{i}.png")
                compose_scene_image(scene.image_path, scene.dialogues, composed_path)
                
                # Calculate total duration
                duration = scene.duration_seconds
                for dialogue in scene.dialogues:
                    duration += calculate_text_duration(dialogue.text)
                
                abs_path = os.path.abspath(composed_path)
                concat_lines.append(f"file '{abs_path}'")
                concat_lines.append(f"duration {duration:.3f}")
            else:
                # No dialogues: just show the image
                abs_path = os.path.abspath(scene.image_path)
                concat_lines.append(f"file '{abs_path}'")
                concat_lines.append(f"duration {scene.duration_seconds:.3f}")


        if not concat_lines:
            raise ValueError("No valid scenes could be processed")

        # Repeat last file so the final duration is honored by concat demuxer
        last_file = concat_lines[-2].replace("file ", "")
        concat_lines.append(f"file {last_file}")

        with open(concat_path, "w", encoding="utf-8") as handle:
            handle.write("\n".join(concat_lines))

        target_height = int(target_width * 16 / 9)
        scale_pad = (
            f"scale={target_width}:-2:force_original_aspect_ratio=decrease,"
            f"pad={target_width}:{target_height}:(ow-iw)/2:(oh-ih)/2"
        )

        cmd = [
            "ffmpeg",
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            concat_path,
            "-vf",
            scale_pad,
            "-r",
            str(fps),
            "-pix_fmt",
            "yuv420p",
            "-c:v",
            "libx264",
            "-movflags",
            "+faststart",
            output_path,
        ]
        logger.info("ffmpeg_start output_path=%s frames=%s", output_path, len(concat_lines) // 2)
        try:
            subprocess.run(
                cmd,
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                timeout=300,
            )
            logger.info("ffmpeg_done output_path=%s", output_path)
        except subprocess.TimeoutExpired as exc:
            logger.error("ffmpeg timed out: %s", exc)
            raise RuntimeError("Video export timed out. Try again with fewer scenes.") from exc
        except subprocess.CalledProcessError as exc:
            stderr = exc.stderr.decode("utf-8", errors="ignore") if exc.stderr else "ffmpeg failed"
            logger.error("ffmpeg failed: %s", stderr)
            raise RuntimeError(f"Video export failed: {stderr[:500]}") from exc

        return output_path

    finally:
        # Cleanup temp files
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
        if not os.path.isabs(image_path):
            image_path = os.path.abspath(image_path)

        # Extract dialogue from layers or dialogue export
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
                        bubble_type=obj.get("type", "chat"),
                    ))

        if not dialogues:
            for obj in scene_info.get("dialogue_bubbles", []) or []:
                geometry = obj.get("geometry", {})
                dialogues.append(DialogueBubbleData(
                    text=obj.get("text", ""),
                    speaker=obj.get("speaker", ""),
                    x=geometry.get("x", 0.1),
                    y=geometry.get("y", 0.1),
                    width=geometry.get("w", 0.3),
                    height=geometry.get("h", 0.15),
                    bubble_type=obj.get("bubble_type", "chat"),
                ))

        frames.append(SceneFrameData(
            image_path=image_path,
            dialogues=dialogues,
            duration_seconds=3.0,  # Base duration
        ))

    logger.info("video_build_frames scenes=%s frames=%s", len(scenes_data), len(frames))

    if not frames:
        raise ValueError("No valid scenes could be processed")

    # Generate output filename
    video_filename = f"webtoon_{uuid.uuid4().hex[:8]}.mp4"
    output_path = os.path.join(output_dir, video_filename)

    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)

    return generate_webtoon_video(frames, output_path)
