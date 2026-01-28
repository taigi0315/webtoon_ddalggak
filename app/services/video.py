"""Video composition service for webtoon exports.

Combines rendered scene images with dialogue bubbles to create a vertical scroll video.
"""
from __future__ import annotations

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
    padding = VIDEO_DIALOGUE_CONFIG["padding"]
    bubble_rect = [x, y, x + w, y + h]
    draw.rounded_rectangle(bubble_rect, radius=15, fill="white", outline="black", width=2)

    if font is None:
        try:
            font = ImageFont.truetype(
                VIDEO_DIALOGUE_CONFIG["font_path"],
                int(VIDEO_DIALOGUE_CONFIG["font_size"] * VIDEO_DIALOGUE_CONFIG["font_scale"]),
            )
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
            abs_path = os.path.abspath(img_path)
            concat_lines.append(f"file '{abs_path}'")
            concat_lines.append(f"duration {duration:.3f}")

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
