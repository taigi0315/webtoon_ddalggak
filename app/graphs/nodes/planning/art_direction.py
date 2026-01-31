"""Art Director node for generating lighting, color temperature, and atmosphere.

The Art Director translates emotional intent into visual mood that complements
the user-selected image style without overriding it.
"""

from __future__ import annotations

import uuid
from sqlalchemy.orm import Session

from app.db.models import Scene, Artifact
from app.services.artifacts import ArtifactService
from app.core.image_styles import get_style_semantic_hint
from ..utils import logger, GeminiClient, _maybe_json_from_gemini
from ..constants import ARTIFACT_ART_DIRECTION


def run_art_director(
    db: Session,
    scene_id: uuid.UUID,
    image_style_id: str,
    gemini: GeminiClient | None = None,
) -> Artifact:
    """Generate art direction (lighting, mood, atmosphere) for a scene.
    
    The Art Director translates Studio Director's emotional intent into
    lighting, color temperature, and atmospheric keywords that complement
    the user-selected image style.
    
    Args:
        db: Database session
        scene_id: Scene UUID
        image_style_id: User-selected image style (e.g., "STARK_BLACK_WHITE_NOIR")
        gemini: Gemini client for LLM calls
        
    Returns:
        Artifact with type ARTIFACT_ART_DIRECTION containing:
        {
            "lighting": str,
            "color_temperature": str,
            "atmosphere_keywords": list[str],
            "compatible_with_style": bool,
        }
    """
    # Load scene
    scene = db.query(Scene).filter(Scene.scene_id == scene_id).first()
    if not scene:
        raise ValueError(f"Scene {scene_id} not found")
    
    # Check for existing artifact (resumability)
    svc = ArtifactService(db)
    existing = svc.get_latest_artifact(scene_id, ARTIFACT_ART_DIRECTION)
    if existing and scene.planning_locked:
        logger.info(f"Reusing existing art direction for scene {scene_id} (planning locked)")
        return existing
    
    # Get image style description
    image_style_description = get_style_semantic_hint(image_style_id)
    
    # Load scene intent (if available)
    scene_intent_artifact = svc.get_latest_artifact(scene_id, "scene_intent")
    scene_intent = ""
    if scene_intent_artifact and scene_intent_artifact.payload:
        intent_data = scene_intent_artifact.payload
        if isinstance(intent_data, dict):
            scene_intent = intent_data.get("intent", "") or intent_data.get("narrative_intent", "")
    
    # Generate art direction
    if gemini is None:
        # Fallback: basic art direction
        logger.warning(f"No Gemini client provided, using fallback art direction for scene {scene_id}")
        art_direction = _fallback_art_direction(image_style_id)
    else:
        prompt = _build_art_direction_prompt(
            image_style_id=image_style_id,
            image_style_description=image_style_description,
            scene_source_text=scene.source_text or "",
            scene_intent=scene_intent,
        )
        
        result = _maybe_json_from_gemini(gemini, prompt)
        
        if result and isinstance(result, dict):
            art_direction = {
                "lighting": result.get("lighting", ""),
                "color_temperature": result.get("color_temperature", ""),
                "atmosphere_keywords": result.get("atmosphere_keywords", []),
                "reasoning": result.get("reasoning", ""),
            }
        else:
            logger.warning(f"Failed to parse art direction from LLM, using fallback for scene {scene_id}")
            art_direction = _fallback_art_direction(image_style_id)
    
    # Validate and correct art direction
    art_direction = _validate_art_direction(art_direction, image_style_id)
    
    # Create artifact
    payload = {
        "lighting": art_direction["lighting"],
        "color_temperature": art_direction["color_temperature"],
        "atmosphere_keywords": art_direction["atmosphere_keywords"],
        "compatible_with_style": art_direction.get("compatible_with_style", True),
        "image_style_id": image_style_id,
    }
    
    return svc.create_artifact(scene_id, ARTIFACT_ART_DIRECTION, payload)


def _build_art_direction_prompt(
    image_style_id: str,
    image_style_description: str,
    scene_source_text: str,
    scene_intent: str,
) -> str:
    """Build prompt for Art Director LLM call.
    
    Args:
        image_style_id: User-selected image style ID
        image_style_description: Semantic description of the style
        scene_source_text: Raw scene text
        scene_intent: Emotional intent from Studio Director
        
    Returns:
        Compiled prompt string
    """
    from app.prompts.loader import render_prompt
    
    return render_prompt(
        "prompt_art_direction",
        image_style_id=image_style_id,
        image_style_description=image_style_description,
        scene_source_text=scene_source_text,
        scene_intent=scene_intent,
    )


def _fallback_art_direction(image_style_id: str) -> dict:
    """Generate fallback art direction when LLM is unavailable.
    
    Args:
        image_style_id: User-selected image style ID
        
    Returns:
        Basic art direction dict
    """
    # Check if style is monochrome
    is_monochrome = _is_monochrome_style(image_style_id)
    
    return {
        "lighting": "balanced natural lighting",
        "color_temperature": "N/A (monochrome)" if is_monochrome else "neutral",
        "atmosphere_keywords": ["neutral", "balanced"],
        "compatible_with_style": True,
    }


def _validate_art_direction(art_direction: dict, image_style_id: str) -> dict:
    """Validate and correct art direction output.
    
    Enforces monochrome constraints and removes color keywords for
    monochrome styles.
    
    Args:
        art_direction: Art direction dict from LLM
        image_style_id: User-selected image style ID
        
    Returns:
        Validated and corrected art direction dict
    """
    is_monochrome = _is_monochrome_style(image_style_id)
    
    if is_monochrome:
        # Force N/A for color temperature
        original_color_temp = art_direction.get("color_temperature", "")
        # Only correct if there's a value that doesn't start with N/A
        if original_color_temp and not original_color_temp.upper().startswith("N/A"):
            logger.warning(
                f"Correcting color temperature for monochrome style {image_style_id}: "
                f"'{original_color_temp}' → 'N/A (monochrome)'"
            )
            art_direction["color_temperature"] = "N/A (monochrome)"
        elif not original_color_temp:
            # Set default for empty/missing color temperature
            art_direction["color_temperature"] = "N/A (monochrome)"
        
        # Remove color keywords from atmosphere
        atmosphere = art_direction.get("atmosphere_keywords", [])
        if isinstance(atmosphere, list):
            color_keywords = [
                "warm", "cool", "golden", "blue", "red", "green", "yellow",
                "orange", "purple", "pink", "pastel", "vibrant", "colorful",
            ]
            original_atmosphere = atmosphere.copy()
            atmosphere = [
                kw for kw in atmosphere
                if not any(color in kw.lower() for color in color_keywords)
            ]
            if len(atmosphere) < len(original_atmosphere):
                removed = set(original_atmosphere) - set(atmosphere)
                logger.warning(
                    f"Removed color keywords from atmosphere for monochrome style {image_style_id}: "
                    f"{removed}"
                )
            art_direction["atmosphere_keywords"] = atmosphere
    
    art_direction["compatible_with_style"] = True
    return art_direction


def _is_monochrome_style(image_style_id: str) -> bool:
    """Check if image style is monochrome.
    
    Args:
        image_style_id: Image style ID
        
    Returns:
        True if style is monochrome (black & white)
    """
    monochrome_styles = [
        "STARK_BLACK_WHITE_NOIR",
        "BLACK_WHITE_NOIR",
        "MONOCHROME",
        "NOIR",
    ]
    
    return any(mono in image_style_id.upper() for mono in monochrome_styles)
