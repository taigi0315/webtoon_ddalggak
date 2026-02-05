# WebtoonForge: AI-Powered Webtoon Generation System

## Architecture Overview

WebtoonForge transforms story seeds into complete vertical webtoons with draggable dialogue bubbles and MP4 video output. The system leverages LangGraph for multi-agent orchestration and React with Fabric.js for the interactive editor.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              WEBTOONFORGE                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────┐    ┌─────────────────────────────────────────────────┐    │
│  │   FRONTEND  │◄───►│                   BACKEND                       │    │
│  │   (React)   │    │              (FastAPI + LangGraph)               │    │
│  └─────────────┘    └─────────────────────────────────────────────────┘    │
│        │                              │                                     │
│        ▼                              ▼                                     │
│  ┌─────────────┐    ┌─────────────────────────────────────────────────┐    │
│  │ Fabric.js   │    │           LANGGRAPH MULTI-AGENT SYSTEM          │    │
│  │ Canvas      │    │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌────────┐ │    │
│  │ Editor      │    │  │Story    │ │Character│ │Panel    │ │Image   │ │    │
│  │             │    │  │Architect│→│Designer │→│Composer │→│Generator│ │    │
│  └─────────────┘    │  └─────────┘ └─────────┘ └─────────┘ └────────┘ │    │
│        │            └─────────────────────────────────────────────────┘    │
│        ▼                              │                                     │
│  ┌─────────────┐                      ▼                                     │
│  │ Video       │    ┌─────────────────────────────────────────────────┐    │
│  │ Exporter    │    │           GEMINI 2.5 FLASH IMAGE MODEL          │    │
│  │ (FFmpeg)    │    │                (9:16 Vertical)                   │    │
│  └─────────────┘    └─────────────────────────────────────────────────┘    │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Part 1: Backend Architecture (LangGraph + FastAPI)

### 1.1 State Definition

```python
from typing import Annotated, TypedDict, Optional
from pydantic import BaseModel, Field
from langgraph.graph import MessagesState
from enum import Enum

class VisualBeatType(str, Enum):
    DETAIL = "detail"      # Object focus, environmental details
    ACTION = "action"      # Character movement, dynamic poses
    REACTION = "reaction"  # Emotional response, facial close-ups
    ESTABLISHING = "establishing"  # Wide shot, scene context
    HOOK = "hook"          # Full-width impact panel (thumbnail candidate)

class PanelWidth(str, Enum):
    FULL = "100%"     # Impact panels, reveals, hooks
    STANDARD = "80%"  # Normal narrative flow
    NARROW = "60%"    # Intimate close-ups, rapid dialogue

class Character(BaseModel):
    """Character definition for consistency tracking"""
    id: str = Field(description="Unique character identifier")
    name: str
    visual_description: str = Field(description="Detailed appearance: hair, eyes, clothing, distinguishing features")
    personality_traits: list[str]
    color_palette: list[str] = Field(description="Character's signature colors")
    reference_prompt: str = Field(description="Stable prompt fragment for image generation")

class Dialogue(BaseModel):
    """Single dialogue bubble"""
    id: str
    character_id: str
    text: str
    emotion: str = Field(description="angry, happy, sad, surprised, neutral, etc.")
    position: dict = Field(default={"x": 50, "y": 50}, description="Position percentage for drag/drop")
    duration_ms: int = Field(description="Display duration based on text length")

class Panel(BaseModel):
    """Single panel within a scene"""
    id: str
    panel_index: int  # 1-3 panels per scene
    visual_beat: VisualBeatType
    width: PanelWidth
    composition_prompt: str = Field(description="Detailed image generation prompt")
    camera_angle: str = Field(description="wide, medium, close-up, extreme-close-up, bird-eye, worm-eye")
    character_ids: list[str] = Field(description="Characters visible in panel")
    is_silent: bool = Field(default=False, description="No dialogue - pure visual storytelling")
    dialogues: list[Dialogue] = Field(default_factory=list)
    image_url: Optional[str] = None
    vertical_spacing_px: int = Field(default=100, description="Gutter space after panel")

class Scene(BaseModel):
    """Scene containing up to 3 panels"""
    id: str
    scene_index: int
    narrative_beat: str = Field(description="Initial, Rising, Peak, Falling, Release")
    panels: list[Panel] = Field(max_length=3)
    is_hook_scene: bool = Field(default=False, description="Contains the hooking/thumbnail panel")

class WebtoonState(TypedDict):
    """Main state for LangGraph orchestration"""
    # Input
    story_seed: str
    target_scene_count: int
    
    # Story Analysis
    story_summary: str
    narrative_arcs: list[dict]  # [{arc: str, beats: list}]
    themes: list[str]
    mood: str
    
    # Character System
    characters: Annotated[list[Character], "extracted characters"]
    character_bank: dict  # {char_id: reference_prompt}
    
    # Scene Structure
    scenes: Annotated[list[Scene], "generated scenes"]
    hook_scene_index: int
    
    # Generation Progress
    current_step: str
    generated_images: dict  # {panel_id: image_url}
    errors: list[str]
    
    # Output
    webtoon_json: Optional[dict]
```

### 1.2 LangGraph Multi-Agent System

```python
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import tool
import google.generativeai as genai
import asyncio

# Initialize LLMs
claude = ChatAnthropic(model="claude-sonnet-4-5", temperature=0.7)
checkpointer = MemorySaver()

# ═══════════════════════════════════════════════════════════════════════════
# AGENT 1: STORY ARCHITECT
# ═══════════════════════════════════════════════════════════════════════════

STORY_ARCHITECT_PROMPT = ChatPromptTemplate.from_template("""
You are a Story Architect specializing in vertical webtoon narrative design.

Analyze this story seed and create a structured narrative plan:

<story_seed>
{story_seed}
</story_seed>

Target scenes: {target_scene_count}

## Your Tasks:

1. **Summarize** the core story (2-3 sentences)
2. **Identify Themes** (visual metaphors we can use)
3. **Map Narrative Arcs** using the structure:
   - Initial (establishing)
   - Rising (building tension)  
   - Peak (climax/reveal)
   - Falling (consequences)
   - Release (resolution/cliffhanger)

4. **Designate the HOOK Scene** - One scene must be the "thumb stop" moment:
   - Most visually striking
   - Works as a thumbnail
   - Full-width impact panel
   - Usually a Peak or dramatic Reveal moment

5. **Scene Breakdown** - Distribute {target_scene_count} scenes across arcs:
   - Each scene = 1-3 panels
   - Balance: 30% establishing, 50% action/dialogue, 20% reaction/silence
   - Apply the "One Action per Panel" rule

## Visual Storytelling Heuristics (from webtoon theory):
- Prioritize "show don't tell" - if art can show it, text shouldn't say it
- Silent panels for emotional weight
- Vary panel widths: Full(100%) for impact, Standard(80%) for flow, Narrow(60%) for intimacy
- Gutter spacing = dramatic weight (more space = longer pause)

Output as structured JSON.
""")

async def story_architect_node(state: WebtoonState) -> WebtoonState:
    """Analyzes story seed and creates narrative structure"""
    
    response = await claude.ainvoke(
        STORY_ARCHITECT_PROMPT.format(
            story_seed=state["story_seed"],
            target_scene_count=state["target_scene_count"]
        )
    )
    
    # Parse structured output
    story_plan = parse_story_json(response.content)
    
    return {
        "story_summary": story_plan["summary"],
        "narrative_arcs": story_plan["arcs"],
        "themes": story_plan["themes"],
        "mood": story_plan["mood"],
        "hook_scene_index": story_plan["hook_scene_index"],
        "current_step": "story_analyzed"
    }


# ═══════════════════════════════════════════════════════════════════════════
# AGENT 2: CHARACTER DESIGNER
# ═══════════════════════════════════════════════════════════════════════════

CHARACTER_DESIGNER_PROMPT = ChatPromptTemplate.from_template("""
You are a Character Designer creating consistent visual identities for webtoon characters.

Story Context:
{story_summary}

Themes: {themes}
Mood: {mood}

## Your Tasks:

1. **Extract Characters** from the story
2. **Design Visual Identity** for each:
   - Distinctive silhouette
   - Color palette (3-5 signature colors)
   - Clothing style that's easy to reproduce
   - Face shape and key features
   - Hair style and color
   
3. **Create Reference Prompts** - Stable text for Gemini image generation:
   - Must be consistent across all panels
   - Include: age, gender, body type, hair, eyes, skin tone, outfit
   - Avoid vague terms - be specific
   - Example: "young woman, early 20s, long straight black hair with bangs, 
     almond-shaped brown eyes, fair skin, wearing oversized cream knit sweater 
     and dark blue jeans, slender build"

4. **Assign Visual Metaphors** based on personality:
   - Color associations (red=passion, blue=calm, etc.)
   - Environmental elements that represent them
   
## Character Consistency Rules:
- Same outfit throughout (unless story requires change)
- Distinctive features that survive different angles
- Color palette must be reproducible in any scene

Output as structured JSON with Character objects.
""")

async def character_designer_node(state: WebtoonState) -> WebtoonState:
    """Creates consistent character designs and reference prompts"""
    
    response = await claude.ainvoke(
        CHARACTER_DESIGNER_PROMPT.format(
            story_summary=state["story_summary"],
            themes=state["themes"],
            mood=state["mood"]
        )
    )
    
    characters = parse_characters_json(response.content)
    character_bank = {c.id: c.reference_prompt for c in characters}
    
    return {
        "characters": characters,
        "character_bank": character_bank,
        "current_step": "characters_designed"
    }


# ═══════════════════════════════════════════════════════════════════════════
# AGENT 3: PANEL COMPOSER
# ═══════════════════════════════════════════════════════════════════════════

PANEL_COMPOSER_PROMPT = ChatPromptTemplate.from_template("""
You are a Panel Composer translating narrative into visual webtoon panels.

Story Summary: {story_summary}
Narrative Arcs: {narrative_arcs}
Characters: {characters}
Hook Scene Index: {hook_scene_index}

## Your Tasks:

For each scene, compose 1-3 panels following webtoon visual grammar:

### Panel Composition Rules:

1. **Visual Beat Types** (assign one per panel):
   - DETAIL: Object focus, environmental storytelling
   - ACTION: Character movement, dynamic poses
   - REACTION: Emotional response, facial expressions
   - ESTABLISHING: Wide shot, scene context
   - HOOK: Full-width dramatic reveal (thumbnail-worthy)

2. **Panel Width Strategy**:
   - 100% (FULL): Climactic reveals, hook moments, emotional peaks
   - 80% (STANDARD): Normal narrative flow, dialogue exchanges
   - 60% (NARROW): Intimate close-ups, rapid sequences, speed

3. **Camera Angles**:
   - wide: Establishing shots, group scenes
   - medium: Standard conversations
   - close-up: Emotional moments, character focus
   - extreme-close-up: Eyes, hands, small details
   - bird-eye: Overhead for isolation/vulnerability
   - worm-eye: Low angle for power/intimidation

4. **Silence Strategy** (mark is_silent=true):
   - Use for: Tension building, emotional weight, "beat" panels
   - 3-5 silent panels per action sequence
   - Reaction shots often work better silent

5. **Dialogue Rules** (if not silent):
   - Max 15 words per bubble
   - Max 2 bubbles per panel
   - Emotion tag for each line
   - Position hints for bubble placement

6. **Gutter Spacing** (vertical_spacing_px):
   - 50px: Rapid action, quick succession
   - 100px: Normal flow
   - 200px: Dramatic pause
   - 400px+: Major scene transition, "thumb stop"

### Scene {scene_index} Specification:
Arc Position: {arc_position}
Narrative Beat: {narrative_beat}
Characters Present: {scene_characters}

Generate panels with detailed composition prompts for Gemini 2.5 Flash.

Output as structured JSON with Scene and Panel objects.
""")

async def panel_composer_node(state: WebtoonState) -> WebtoonState:
    """Composes detailed panel specifications for each scene"""
    
    scenes = []
    
    for arc in state["narrative_arcs"]:
        for beat in arc["beats"]:
            scene_index = len(scenes)
            
            response = await claude.ainvoke(
                PANEL_COMPOSER_PROMPT.format(
                    story_summary=state["story_summary"],
                    narrative_arcs=state["narrative_arcs"],
                    characters=state["characters"],
                    hook_scene_index=state["hook_scene_index"],
                    scene_index=scene_index,
                    arc_position=arc["name"],
                    narrative_beat=beat["type"],
                    scene_characters=beat.get("characters", [])
                )
            )
            
            scene = parse_scene_json(response.content)
            scenes.append(scene)
    
    return {
        "scenes": scenes,
        "current_step": "panels_composed"
    }


# ═══════════════════════════════════════════════════════════════════════════
# AGENT 4: IMAGE GENERATOR (Gemini 2.5 Flash)
# ═══════════════════════════════════════════════════════════════════════════

async def generate_panel_image(
    panel: Panel, 
    character_bank: dict,
    style_prompt: str
) -> str:
    """Generate single panel image using Gemini 2.5 Flash"""
    
    # Build character descriptions
    char_descriptions = []
    for char_id in panel.character_ids:
        if char_id in character_bank:
            char_descriptions.append(character_bank[char_id])
    
    # Construct full prompt
    full_prompt = f"""
Create a vertical webtoon panel (9:16 aspect ratio).

Style: {style_prompt}

Scene Description:
{panel.composition_prompt}

Camera: {panel.camera_angle}
Visual Beat: {panel.visual_beat.value}

Characters in scene:
{chr(10).join(char_descriptions)}

Important:
- DO NOT include any text, dialogue bubbles, or speech in the image
- Clean visual storytelling only
- Consistent anime/webtoon art style
- High contrast, vibrant colors
- Clear character expressions and poses
"""
    
    # Call Gemini 2.5 Flash
    genai.configure(api_key=os.environ["GEMINI_API_KEY"])
    model = genai.GenerativeModel('gemini-2.5-flash-preview-05-20')
    
    response = await model.generate_content_async(
        full_prompt,
        generation_config={
            "response_mime_type": "image/png",
            # 9:16 vertical aspect ratio
        }
    )
    
    # Save and return URL
    image_path = f"/tmp/panels/{panel.id}.png"
    save_image(response.image, image_path)
    
    return upload_to_storage(image_path)


async def image_generator_node(state: WebtoonState) -> WebtoonState:
    """Generates images for all panels using Gemini 2.5 Flash"""
    
    generated_images = {}
    errors = []
    
    # Style prompt for consistency
    style_prompt = f"""
Webtoon art style, {state['mood']} atmosphere.
Clean line art with soft shading.
Expressive anime-style characters.
Color palette emphasizing: {', '.join(state['themes'])}.
"""
    
    # Generate all panels concurrently (with rate limiting)
    semaphore = asyncio.Semaphore(5)  # Max 5 concurrent requests
    
    async def generate_with_limit(panel):
        async with semaphore:
            try:
                url = await generate_panel_image(
                    panel, 
                    state["character_bank"],
                    style_prompt
                )
                return (panel.id, url)
            except Exception as e:
                errors.append(f"Panel {panel.id}: {str(e)}")
                return (panel.id, None)
    
    tasks = []
    for scene in state["scenes"]:
        for panel in scene.panels:
            tasks.append(generate_with_limit(panel))
    
    results = await asyncio.gather(*tasks)
    
    for panel_id, url in results:
        if url:
            generated_images[panel_id] = url
    
    # Update scenes with image URLs
    updated_scenes = []
    for scene in state["scenes"]:
        updated_panels = []
        for panel in scene.panels:
            panel.image_url = generated_images.get(panel.id)
            updated_panels.append(panel)
        scene.panels = updated_panels
        updated_scenes.append(scene)
    
    return {
        "scenes": updated_scenes,
        "generated_images": generated_images,
        "errors": state.get("errors", []) + errors,
        "current_step": "images_generated"
    }


# ═══════════════════════════════════════════════════════════════════════════
# AGENT 5: OUTPUT ASSEMBLER
# ═══════════════════════════════════════════════════════════════════════════

async def output_assembler_node(state: WebtoonState) -> WebtoonState:
    """Assembles final webtoon JSON for frontend"""
    
    # Find hook scene for thumbnail
    hook_panel = None
    for scene in state["scenes"]:
        if scene.is_hook_scene:
            for panel in scene.panels:
                if panel.visual_beat == VisualBeatType.HOOK:
                    hook_panel = panel
                    break
    
    webtoon_json = {
        "id": generate_uuid(),
        "title": extract_title(state["story_summary"]),
        "summary": state["story_summary"],
        "thumbnail_url": hook_panel.image_url if hook_panel else state["scenes"][0].panels[0].image_url,
        "characters": [c.dict() for c in state["characters"]],
        "scenes": [s.dict() for s in state["scenes"]],
        "metadata": {
            "total_scenes": len(state["scenes"]),
            "total_panels": sum(len(s.panels) for s in state["scenes"]),
            "themes": state["themes"],
            "mood": state["mood"]
        }
    }
    
    return {
        "webtoon_json": webtoon_json,
        "current_step": "complete"
    }


# ═══════════════════════════════════════════════════════════════════════════
# GRAPH CONSTRUCTION
# ═══════════════════════════════════════════════════════════════════════════

def build_webtoon_graph():
    """Construct the LangGraph workflow"""
    
    builder = StateGraph(WebtoonState)
    
    # Add nodes
    builder.add_node("story_architect", story_architect_node)
    builder.add_node("character_designer", character_designer_node)
    builder.add_node("panel_composer", panel_composer_node)
    builder.add_node("image_generator", image_generator_node)
    builder.add_node("output_assembler", output_assembler_node)
    
    # Linear flow with checkpoints
    builder.add_edge(START, "story_architect")
    builder.add_edge("story_architect", "character_designer")
    builder.add_edge("character_designer", "panel_composer")
    builder.add_edge("panel_composer", "image_generator")
    builder.add_edge("image_generator", "output_assembler")
    builder.add_edge("output_assembler", END)
    
    # Compile with checkpointing for recovery
    return builder.compile(checkpointer=checkpointer)


webtoon_graph = build_webtoon_graph()
```

### 1.3 FastAPI Server

```python
from fastapi import FastAPI, WebSocket, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import asyncio
import json

app = FastAPI(title="WebtoonForge API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class GenerateRequest(BaseModel):
    story_seed: str
    target_scene_count: int = 10

class WebtoonUpdateRequest(BaseModel):
    webtoon_id: str
    scenes: list[dict]  # Updated scene data with dialogue positions

# In-memory store (replace with Redis/DB in production)
generation_status = {}
webtoon_store = {}


@app.post("/api/generate")
async def generate_webtoon(request: GenerateRequest, background_tasks: BackgroundTasks):
    """Start webtoon generation pipeline"""
    
    job_id = generate_uuid()
    generation_status[job_id] = {"status": "started", "progress": 0}
    
    background_tasks.add_task(run_generation, job_id, request)
    
    return {"job_id": job_id, "status": "started"}


async def run_generation(job_id: str, request: GenerateRequest):
    """Background task for generation"""
    
    try:
        config = {"configurable": {"thread_id": job_id}}
        
        async for event in webtoon_graph.astream_events(
            {
                "story_seed": request.story_seed,
                "target_scene_count": request.target_scene_count
            },
            config=config,
            version="v2"
        ):
            # Update progress based on node execution
            if event["event"] == "on_chain_end":
                node_name = event.get("name", "")
                progress_map = {
                    "story_architect": 20,
                    "character_designer": 40,
                    "panel_composer": 60,
                    "image_generator": 90,
                    "output_assembler": 100
                }
                if node_name in progress_map:
                    generation_status[job_id]["progress"] = progress_map[node_name]
                    generation_status[job_id]["current_step"] = node_name
        
        # Get final state
        final_state = await webtoon_graph.aget_state(config)
        webtoon_store[job_id] = final_state.values["webtoon_json"]
        
        generation_status[job_id] = {
            "status": "complete",
            "progress": 100,
            "webtoon_id": job_id
        }
        
    except Exception as e:
        generation_status[job_id] = {
            "status": "error",
            "error": str(e)
        }


@app.get("/api/status/{job_id}")
async def get_status(job_id: str):
    """Get generation status"""
    if job_id not in generation_status:
        raise HTTPException(404, "Job not found")
    return generation_status[job_id]


@app.get("/api/webtoon/{webtoon_id}")
async def get_webtoon(webtoon_id: str):
    """Get generated webtoon data"""
    if webtoon_id not in webtoon_store:
        raise HTTPException(404, "Webtoon not found")
    return webtoon_store[webtoon_id]


@app.put("/api/webtoon/{webtoon_id}")
async def update_webtoon(webtoon_id: str, request: WebtoonUpdateRequest):
    """Update webtoon with edited dialogue positions"""
    if webtoon_id not in webtoon_store:
        raise HTTPException(404, "Webtoon not found")
    
    webtoon_store[webtoon_id]["scenes"] = request.scenes
    return {"status": "updated"}


@app.post("/api/export/{webtoon_id}")
async def export_video(webtoon_id: str, background_tasks: BackgroundTasks):
    """Export webtoon to MP4 video"""
    if webtoon_id not in webtoon_store:
        raise HTTPException(404, "Webtoon not found")
    
    export_id = generate_uuid()
    background_tasks.add_task(run_video_export, export_id, webtoon_store[webtoon_id])
    
    return {"export_id": export_id}


async def run_video_export(export_id: str, webtoon_data: dict):
    """Generate MP4 from webtoon data using FFmpeg"""
    
    # Video generation logic using FFmpeg
    # - Each scene image displayed for calculated duration
    # - Dialogues overlaid one at a time
    # - Smooth transitions between panels
    
    output_path = f"/tmp/exports/{export_id}.mp4"
    
    # FFmpeg command construction
    # ... (detailed implementation below)
```

### 1.4 Video Export Service

```python
import subprocess
import tempfile
from PIL import Image, ImageDraw, ImageFont
import os

class VideoExporter:
    """Exports webtoon to MP4 with dialogue overlays"""
    
    def __init__(self, webtoon_data: dict):
        self.webtoon = webtoon_data
        self.fps = 30
        self.base_panel_duration = 3.0  # seconds
        self.dialogue_char_rate = 0.05  # seconds per character
        
    def calculate_dialogue_duration(self, text: str) -> float:
        """Calculate display time based on text length"""
        base = 1.5  # minimum duration
        char_time = len(text) * self.dialogue_char_rate
        return max(base, char_time)
    
    async def create_panel_frame(
        self, 
        panel: dict, 
        dialogue: dict = None
    ) -> str:
        """Create frame with optional dialogue overlay"""
        
        # Load base panel image
        img = Image.open(panel["image_url"])
        
        if dialogue:
            draw = ImageDraw.Draw(img)
            
            # Speech bubble styling
            bubble_color = (255, 255, 255, 240)
            text_color = (30, 30, 30)
            
            # Position from dialogue data
            x = int(img.width * dialogue["position"]["x"] / 100)
            y = int(img.height * dialogue["position"]["y"] / 100)
            
            # Draw bubble and text
            # ... (bubble rendering logic)
            
        # Save frame
        frame_path = tempfile.mktemp(suffix=".png")
        img.save(frame_path)
        return frame_path
    
    async def export(self, output_path: str) -> str:
        """Generate MP4 video"""
        
        frames = []
        
        for scene in self.webtoon["scenes"]:
            for panel in scene["panels"]:
                if panel["is_silent"]:
                    # Silent panel - just show image
                    frame = await self.create_panel_frame(panel)
                    frames.append({
                        "path": frame,
                        "duration": self.base_panel_duration
                    })
                else:
                    # Panel with dialogues - show each one sequentially
                    for i, dialogue in enumerate(panel["dialogues"]):
                        frame = await self.create_panel_frame(panel, dialogue)
                        duration = self.calculate_dialogue_duration(dialogue["text"])
                        frames.append({
                            "path": frame,
                            "duration": duration
                        })
        
        # Generate FFmpeg concat file
        concat_path = tempfile.mktemp(suffix=".txt")
        with open(concat_path, "w") as f:
            for frame in frames:
                f.write(f"file '{frame['path']}'\n")
                f.write(f"duration {frame['duration']}\n")
        
        # Run FFmpeg
        cmd = [
            "ffmpeg", "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", concat_path,
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-r", str(self.fps),
            output_path
        ]
        
        subprocess.run(cmd, check=True)
        
        # Cleanup temp files
        for frame in frames:
            os.remove(frame["path"])
        os.remove(concat_path)
        
        return output_path
```

---

## Part 2: Frontend Architecture (React + Fabric.js)

### 2.1 Design Direction

**Aesthetic**: Neo-Editorial Webtoon Studio
- Dark theme with vibrant accent colors
- Manga-inspired panel layouts
- Fluid animations mimicking page turns
- Split-panel workflow: Preview | Editor

**Typography**:
- Display: "Bebas Neue" (bold, impactful headers)
- Body: "Noto Sans JP" (clean, readable, supports Korean/Japanese)
- UI: "JetBrains Mono" (technical elements)

**Color Palette**:
```css
:root {
  --bg-primary: #0d0d0f;
  --bg-secondary: #161618;
  --bg-elevated: #1e1e21;
  --accent-primary: #ff3366;
  --accent-secondary: #00d4ff;
  --accent-success: #00ff88;
  --text-primary: #ffffff;
  --text-secondary: #8b8b8d;
  --border-subtle: rgba(255, 255, 255, 0.08);
}
```

### 2.2 Component Architecture

```
src/
├── app/
│   ├── page.tsx              # Main entry
│   └── layout.tsx            # Root layout
├── components/
│   ├── studio/
│   │   ├── StudioLayout.tsx  # Split-panel layout
│   │   ├── StoryInput.tsx    # Story seed input
│   │   └── GenerationProgress.tsx
│   ├── preview/
│   │   ├── WebtoonPreview.tsx    # Vertical scroll preview
│   │   ├── SceneCard.tsx         # Individual scene
│   │   └── PanelView.tsx         # Panel with dialogues
│   ├── editor/
│   │   ├── DialogueEditor.tsx    # Fabric.js canvas
│   │   ├── BubbleControls.tsx    # Style/position controls
│   │   ├── CharacterPanel.tsx    # Character reference
│   │   └── TimelineEditor.tsx    # Dialogue timing
│   └── export/
│       └── VideoExporter.tsx     # Export controls
├── hooks/
│   ├── useWebtoonGeneration.ts
│   ├── useFabricCanvas.ts
│   └── useVideoExport.ts
├── stores/
│   └── webtoonStore.ts       # Zustand store
└── types/
    └── webtoon.ts            # TypeScript types
```

### 2.3 Main Components

#### StudioLayout.tsx
```tsx
'use client';

import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { StoryInput } from './StoryInput';
import { GenerationProgress } from './GenerationProgress';
import { WebtoonPreview } from '../preview/WebtoonPreview';
import { DialogueEditor } from '../editor/DialogueEditor';
import { useWebtoonStore } from '@/stores/webtoonStore';
import styles from './StudioLayout.module.css';

export function StudioLayout() {
  const { webtoon, isGenerating, selectedPanel } = useWebtoonStore();
  const [view, setView] = useState<'input' | 'preview' | 'editor'>('input');

  return (
    <div className={styles.studioContainer}>
      {/* Header */}
      <header className={styles.header}>
        <div className={styles.logo}>
          <span className={styles.logoAccent}>WEBTOON</span>FORGE
        </div>
        <nav className={styles.viewTabs}>
          {['input', 'preview', 'editor'].map((v) => (
            <button
              key={v}
              className={`${styles.tab} ${view === v ? styles.active : ''}`}
              onClick={() => setView(v as any)}
              disabled={v !== 'input' && !webtoon}
            >
              {v.toUpperCase()}
            </button>
          ))}
        </nav>
        <div className={styles.actions}>
          {webtoon && (
            <motion.button
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              className={styles.exportBtn}
            >
              Export MP4
            </motion.button>
          )}
        </div>
      </header>

      {/* Main Content */}
      <main className={styles.mainContent}>
        <AnimatePresence mode="wait">
          {view === 'input' && (
            <motion.div
              key="input"
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: 20 }}
              className={styles.inputView}
            >
              <StoryInput />
              {isGenerating && <GenerationProgress />}
            </motion.div>
          )}

          {view === 'preview' && webtoon && (
            <motion.div
              key="preview"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              className={styles.previewView}
            >
              <WebtoonPreview webtoon={webtoon} />
            </motion.div>
          )}

          {view === 'editor' && selectedPanel && (
            <motion.div
              key="editor"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className={styles.editorView}
            >
              <div className={styles.editorSplit}>
                <DialogueEditor panel={selectedPanel} />
                <div className={styles.editorSidebar}>
                  <CharacterPanel />
                  <TimelineEditor />
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </main>
    </div>
  );
}
```

#### DialogueEditor.tsx (Fabric.js Canvas)
```tsx
'use client';

import { useEffect, useRef, useState } from 'react';
import { fabric } from 'fabric';
import { motion } from 'framer-motion';
import { useWebtoonStore } from '@/stores/webtoonStore';
import { Panel, Dialogue } from '@/types/webtoon';
import styles from './DialogueEditor.module.css';

interface DialogueEditorProps {
  panel: Panel;
}

export function DialogueEditor({ panel }: DialogueEditorProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const fabricRef = useRef<fabric.Canvas | null>(null);
  const { updateDialoguePosition, characters } = useWebtoonStore();
  
  const [selectedBubble, setSelectedBubble] = useState<string | null>(null);
  const [bubbleStyle, setBubbleStyle] = useState<'normal' | 'shout' | 'whisper' | 'thought'>('normal');

  useEffect(() => {
    if (!canvasRef.current) return;

    // Initialize Fabric.js canvas
    const canvas = new fabric.Canvas(canvasRef.current, {
      width: 450,  // 9:16 ratio scaled
      height: 800,
      backgroundColor: 'transparent',
      selection: true,
    });

    fabricRef.current = canvas;

    // Load panel image as background
    fabric.Image.fromURL(panel.image_url, (img) => {
      canvas.setBackgroundImage(img, canvas.renderAll.bind(canvas), {
        scaleX: canvas.width! / img.width!,
        scaleY: canvas.height! / img.height!,
      });
    });

    // Add existing dialogues as draggable bubbles
    panel.dialogues.forEach((dialogue) => {
      const bubble = createSpeechBubble(dialogue, characters);
      canvas.add(bubble);
    });

    // Handle object movement
    canvas.on('object:modified', (e) => {
      const obj = e.target;
      if (obj && obj.data?.dialogueId) {
        const xPercent = (obj.left! / canvas.width!) * 100;
        const yPercent = (obj.top! / canvas.height!) * 100;
        
        updateDialoguePosition(panel.id, obj.data.dialogueId, {
          x: xPercent,
          y: yPercent,
        });
      }
    });

    canvas.on('selection:created', (e) => {
      if (e.selected?.[0]?.data?.dialogueId) {
        setSelectedBubble(e.selected[0].data.dialogueId);
      }
    });

    canvas.on('selection:cleared', () => {
      setSelectedBubble(null);
    });

    return () => {
      canvas.dispose();
    };
  }, [panel]);

  const createSpeechBubble = (dialogue: Dialogue, characters: Character[]) => {
    const char = characters.find(c => c.id === dialogue.character_id);
    const bubbleColor = getBubbleColor(bubbleStyle);
    
    // Create bubble shape based on style
    const bubbleWidth = Math.min(200, dialogue.text.length * 8 + 40);
    const bubbleHeight = Math.ceil(dialogue.text.length / 20) * 24 + 30;

    const group = new fabric.Group([], {
      left: (dialogue.position.x / 100) * 450,
      top: (dialogue.position.y / 100) * 800,
      hasControls: true,
      hasBorders: true,
      lockRotation: true,
      lockScalingX: true,
      lockScalingY: true,
      data: { dialogueId: dialogue.id },
    });

    // Bubble background
    let bubblePath;
    switch (bubbleStyle) {
      case 'shout':
        bubblePath = createJaggedBubble(bubbleWidth, bubbleHeight);
        break;
      case 'whisper':
        bubblePath = createDashedBubble(bubbleWidth, bubbleHeight);
        break;
      case 'thought':
        bubblePath = createCloudBubble(bubbleWidth, bubbleHeight);
        break;
      default:
        bubblePath = createRoundedBubble(bubbleWidth, bubbleHeight);
    }

    bubblePath.set({
      fill: bubbleColor.fill,
      stroke: bubbleColor.stroke,
      strokeWidth: 2,
    });
    group.addWithUpdate(bubblePath);

    // Dialogue text
    const text = new fabric.Textbox(dialogue.text, {
      width: bubbleWidth - 20,
      fontSize: 14,
      fontFamily: 'Noto Sans JP, sans-serif',
      fill: '#1a1a1a',
      textAlign: 'center',
      originX: 'center',
      originY: 'center',
    });
    group.addWithUpdate(text);

    // Character indicator
    if (char) {
      const indicator = new fabric.Circle({
        radius: 6,
        fill: char.color_palette[0],
        stroke: '#fff',
        strokeWidth: 1,
        left: -bubbleWidth / 2 - 5,
        top: -bubbleHeight / 2 - 5,
      });
      group.addWithUpdate(indicator);
    }

    return group;
  };

  const createRoundedBubble = (w: number, h: number) => {
    return new fabric.Rect({
      width: w,
      height: h,
      rx: 16,
      ry: 16,
      originX: 'center',
      originY: 'center',
    });
  };

  const createJaggedBubble = (w: number, h: number) => {
    // Create spiky/explosive bubble for shouts
    const points = [];
    const spikes = 12;
    for (let i = 0; i < spikes; i++) {
      const angle = (i / spikes) * Math.PI * 2;
      const r = i % 2 === 0 ? Math.max(w, h) / 2 : Math.max(w, h) / 2.5;
      points.push({
        x: Math.cos(angle) * r,
        y: Math.sin(angle) * r,
      });
    }
    return new fabric.Polygon(points, {
      originX: 'center',
      originY: 'center',
    });
  };

  const getBubbleColor = (style: string) => {
    switch (style) {
      case 'shout':
        return { fill: '#fff4f4', stroke: '#ff3366' };
      case 'whisper':
        return { fill: '#f0f0f0', stroke: '#888888' };
      case 'thought':
        return { fill: '#f4f8ff', stroke: '#4488ff' };
      default:
        return { fill: '#ffffff', stroke: '#333333' };
    }
  };

  return (
    <div className={styles.editorContainer}>
      <div className={styles.canvasWrapper}>
        <canvas ref={canvasRef} />
      </div>

      <div className={styles.controls}>
        <h3>Bubble Style</h3>
        <div className={styles.styleButtons}>
          {(['normal', 'shout', 'whisper', 'thought'] as const).map((style) => (
            <button
              key={style}
              className={`${styles.styleBtn} ${bubbleStyle === style ? styles.active : ''}`}
              onClick={() => setBubbleStyle(style)}
            >
              {style.charAt(0).toUpperCase() + style.slice(1)}
            </button>
          ))}
        </div>

        {selectedBubble && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className={styles.bubbleInfo}
          >
            <p>Drag bubble to reposition</p>
            <button className={styles.deleteBtn}>Delete Bubble</button>
          </motion.div>
        )}
      </div>
    </div>
  );
}
```

#### WebtoonPreview.tsx
```tsx
'use client';

import { useRef } from 'react';
import { motion, useScroll, useTransform } from 'framer-motion';
import { Webtoon, Scene, Panel } from '@/types/webtoon';
import { useWebtoonStore } from '@/stores/webtoonStore';
import styles from './WebtoonPreview.module.css';

interface WebtoonPreviewProps {
  webtoon: Webtoon;
}

export function WebtoonPreview({ webtoon }: WebtoonPreviewProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const { setSelectedPanel } = useWebtoonStore();
  const { scrollYProgress } = useScroll({ container: containerRef });

  return (
    <div className={styles.previewContainer}>
      {/* Progress indicator */}
      <motion.div
        className={styles.progressBar}
        style={{ scaleY: scrollYProgress }}
      />

      {/* Vertical scroll container */}
      <div ref={containerRef} className={styles.scrollContainer}>
        {/* Title card */}
        <motion.div
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          className={styles.titleCard}
        >
          <h1>{webtoon.title}</h1>
          <p>{webtoon.summary}</p>
        </motion.div>

        {/* Scenes */}
        {webtoon.scenes.map((scene, sceneIndex) => (
          <div
            key={scene.id}
            className={styles.scene}
            style={{
              marginTop: sceneIndex === 0 ? 0 : 40,
            }}
          >
            {scene.panels.map((panel, panelIndex) => (
              <PanelCard
                key={panel.id}
                panel={panel}
                isHook={scene.is_hook_scene && panel.visual_beat === 'hook'}
                onClick={() => setSelectedPanel(panel)}
              />
            ))}
            
            {/* Scene gutter */}
            <div
              className={styles.sceneGutter}
              style={{ height: getGutterHeight(scene) }}
            />
          </div>
        ))}

        {/* End card */}
        <div className={styles.endCard}>
          <span>END</span>
        </div>
      </div>

      {/* Scene navigator */}
      <div className={styles.sceneNav}>
        {webtoon.scenes.map((scene, i) => (
          <button
            key={scene.id}
            className={`${styles.navDot} ${scene.is_hook_scene ? styles.hook : ''}`}
            onClick={() => scrollToScene(i)}
            title={`Scene ${i + 1}`}
          />
        ))}
      </div>
    </div>
  );
}

interface PanelCardProps {
  panel: Panel;
  isHook: boolean;
  onClick: () => void;
}

function PanelCard({ panel, isHook, onClick }: PanelCardProps) {
  const ref = useRef<HTMLDivElement>(null);
  
  return (
    <motion.div
      ref={ref}
      initial={{ opacity: 0, y: 50 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "-100px" }}
      transition={{ duration: 0.5 }}
      className={`${styles.panel} ${styles[panel.width.replace('%', '')]} ${isHook ? styles.hookPanel : ''}`}
      style={{
        marginBottom: panel.vertical_spacing_px,
      }}
      onClick={onClick}
    >
      <img
        src={panel.image_url}
        alt={`Panel ${panel.panel_index}`}
        className={styles.panelImage}
      />

      {/* Dialogue overlays */}
      {panel.dialogues.map((dialogue) => (
        <motion.div
          key={dialogue.id}
          initial={{ opacity: 0, scale: 0.8 }}
          whileInView={{ opacity: 1, scale: 1 }}
          viewport={{ once: true }}
          transition={{ delay: 0.3 }}
          className={styles.dialogueBubble}
          style={{
            left: `${dialogue.position.x}%`,
            top: `${dialogue.position.y}%`,
          }}
        >
          <span className={styles.bubbleText}>{dialogue.text}</span>
        </motion.div>
      ))}

      {/* Edit indicator */}
      <div className={styles.editOverlay}>
        <span>Click to Edit Dialogues</span>
      </div>

      {isHook && (
        <div className={styles.hookBadge}>
          📌 HOOK
        </div>
      )}
    </motion.div>
  );
}

function getGutterHeight(scene: Scene): number {
  // Calculate gutter based on narrative beat
  const beatGutters = {
    'Initial': 100,
    'Rising': 80,
    'Peak': 200,
    'Falling': 120,
    'Release': 160,
  };
  return beatGutters[scene.narrative_beat] || 100;
}
```

### 2.4 Zustand Store

```typescript
// stores/webtoonStore.ts
import { create } from 'zustand';
import { Webtoon, Panel, Scene, Dialogue, Character } from '@/types/webtoon';

interface WebtoonState {
  // Data
  webtoon: Webtoon | null;
  characters: Character[];
  
  // UI State
  isGenerating: boolean;
  generationProgress: number;
  currentStep: string;
  selectedPanel: Panel | null;
  
  // Actions
  setWebtoon: (webtoon: Webtoon) => void;
  setSelectedPanel: (panel: Panel | null) => void;
  updateDialoguePosition: (panelId: string, dialogueId: string, position: { x: number; y: number }) => void;
  updateDialogue: (panelId: string, dialogueId: string, updates: Partial<Dialogue>) => void;
  addDialogue: (panelId: string, dialogue: Dialogue) => void;
  removeDialogue: (panelId: string, dialogueId: string) => void;
  
  // Generation
  startGeneration: (storySeed: string, targetScenes: number) => Promise<void>;
  setGenerationProgress: (progress: number, step: string) => void;
  
  // Export
  exportVideo: () => Promise<string>;
}

export const useWebtoonStore = create<WebtoonState>((set, get) => ({
  webtoon: null,
  characters: [],
  isGenerating: false,
  generationProgress: 0,
  currentStep: '',
  selectedPanel: null,

  setWebtoon: (webtoon) => set({ 
    webtoon, 
    characters: webtoon.characters 
  }),

  setSelectedPanel: (panel) => set({ selectedPanel: panel }),

  updateDialoguePosition: (panelId, dialogueId, position) => {
    const { webtoon } = get();
    if (!webtoon) return;

    const updatedScenes = webtoon.scenes.map((scene) => ({
      ...scene,
      panels: scene.panels.map((panel) => {
        if (panel.id !== panelId) return panel;
        return {
          ...panel,
          dialogues: panel.dialogues.map((d) =>
            d.id === dialogueId ? { ...d, position } : d
          ),
        };
      }),
    }));

    set({ webtoon: { ...webtoon, scenes: updatedScenes } });
  },

  updateDialogue: (panelId, dialogueId, updates) => {
    const { webtoon } = get();
    if (!webtoon) return;

    const updatedScenes = webtoon.scenes.map((scene) => ({
      ...scene,
      panels: scene.panels.map((panel) => {
        if (panel.id !== panelId) return panel;
        return {
          ...panel,
          dialogues: panel.dialogues.map((d) =>
            d.id === dialogueId ? { ...d, ...updates } : d
          ),
        };
      }),
    }));

    set({ webtoon: { ...webtoon, scenes: updatedScenes } });
  },

  addDialogue: (panelId, dialogue) => {
    const { webtoon } = get();
    if (!webtoon) return;

    const updatedScenes = webtoon.scenes.map((scene) => ({
      ...scene,
      panels: scene.panels.map((panel) => {
        if (panel.id !== panelId) return panel;
        return {
          ...panel,
          dialogues: [...panel.dialogues, dialogue],
          is_silent: false,
        };
      }),
    }));

    set({ webtoon: { ...webtoon, scenes: updatedScenes } });
  },

  removeDialogue: (panelId, dialogueId) => {
    const { webtoon } = get();
    if (!webtoon) return;

    const updatedScenes = webtoon.scenes.map((scene) => ({
      ...scene,
      panels: scene.panels.map((panel) => {
        if (panel.id !== panelId) return panel;
        const newDialogues = panel.dialogues.filter((d) => d.id !== dialogueId);
        return {
          ...panel,
          dialogues: newDialogues,
          is_silent: newDialogues.length === 0,
        };
      }),
    }));

    set({ webtoon: { ...webtoon, scenes: updatedScenes } });
  },

  startGeneration: async (storySeed, targetScenes) => {
    set({ isGenerating: true, generationProgress: 0 });

    try {
      // Start generation
      const response = await fetch('/api/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ story_seed: storySeed, target_scene_count: targetScenes }),
      });

      const { job_id } = await response.json();

      // Poll for status
      const pollInterval = setInterval(async () => {
        const statusRes = await fetch(`/api/status/${job_id}`);
        const status = await statusRes.json();

        set({
          generationProgress: status.progress,
          currentStep: status.current_step,
        });

        if (status.status === 'complete') {
          clearInterval(pollInterval);
          
          // Fetch completed webtoon
          const webtoonRes = await fetch(`/api/webtoon/${job_id}`);
          const webtoon = await webtoonRes.json();
          
          set({
            webtoon,
            characters: webtoon.characters,
            isGenerating: false,
          });
        }

        if (status.status === 'error') {
          clearInterval(pollInterval);
          set({ isGenerating: false });
          throw new Error(status.error);
        }
      }, 2000);

    } catch (error) {
      set({ isGenerating: false });
      throw error;
    }
  },

  setGenerationProgress: (progress, step) => set({
    generationProgress: progress,
    currentStep: step,
  }),

  exportVideo: async () => {
    const { webtoon } = get();
    if (!webtoon) throw new Error('No webtoon to export');

    // Save current state
    await fetch(`/api/webtoon/${webtoon.id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ scenes: webtoon.scenes }),
    });

    // Start export
    const response = await fetch(`/api/export/${webtoon.id}`, {
      method: 'POST',
    });

    const { export_id } = await response.json();

    // Poll for completion and return download URL
    // ...
    
    return `/api/download/${export_id}`;
  },
}));
```

### 2.5 CSS Styles

```css
/* StudioLayout.module.css */
.studioContainer {
  min-height: 100vh;
  background: var(--bg-primary);
  color: var(--text-primary);
  display: flex;
  flex-direction: column;
}

.header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1rem 2rem;
  background: var(--bg-secondary);
  border-bottom: 1px solid var(--border-subtle);
}

.logo {
  font-family: 'Bebas Neue', sans-serif;
  font-size: 1.5rem;
  letter-spacing: 0.1em;
}

.logoAccent {
  color: var(--accent-primary);
}

.viewTabs {
  display: flex;
  gap: 0.5rem;
}

.tab {
  padding: 0.5rem 1.5rem;
  background: transparent;
  border: 1px solid var(--border-subtle);
  color: var(--text-secondary);
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.75rem;
  cursor: pointer;
  transition: all 0.2s;
}

.tab:hover:not(:disabled) {
  border-color: var(--accent-secondary);
  color: var(--accent-secondary);
}

.tab.active {
  background: var(--accent-primary);
  border-color: var(--accent-primary);
  color: white;
}

.tab:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}

.exportBtn {
  padding: 0.75rem 2rem;
  background: linear-gradient(135deg, var(--accent-primary), #ff6699);
  border: none;
  color: white;
  font-family: 'Bebas Neue', sans-serif;
  font-size: 1rem;
  letter-spacing: 0.1em;
  cursor: pointer;
  transition: transform 0.2s;
}

.mainContent {
  flex: 1;
  display: flex;
  justify-content: center;
  padding: 2rem;
  overflow: hidden;
}

/* WebtoonPreview.module.css */
.previewContainer {
  position: relative;
  width: 100%;
  max-width: 500px;
  height: 100%;
}

.progressBar {
  position: fixed;
  right: 1rem;
  top: 50%;
  transform: translateY(-50%);
  width: 4px;
  height: 200px;
  background: var(--border-subtle);
  border-radius: 2px;
  transform-origin: top;
}

.scrollContainer {
  height: 100%;
  overflow-y: auto;
  padding: 2rem;
  scrollbar-width: thin;
  scrollbar-color: var(--accent-secondary) var(--bg-secondary);
}

.titleCard {
  text-align: center;
  padding: 4rem 2rem;
  margin-bottom: 3rem;
}

.titleCard h1 {
  font-family: 'Bebas Neue', sans-serif;
  font-size: 3rem;
  letter-spacing: 0.15em;
  margin-bottom: 1rem;
  background: linear-gradient(135deg, var(--accent-primary), var(--accent-secondary));
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

.panel {
  position: relative;
  margin: 0 auto;
  border-radius: 4px;
  overflow: hidden;
  cursor: pointer;
  transition: transform 0.3s, box-shadow 0.3s;
}

.panel:hover {
  transform: scale(1.02);
  box-shadow: 0 20px 60px rgba(255, 51, 102, 0.2);
}

.panel.100 { width: 100%; }
.panel.80 { width: 80%; }
.panel.60 { width: 60%; }

.panelImage {
  width: 100%;
  display: block;
}

.hookPanel {
  box-shadow: 0 0 40px rgba(255, 51, 102, 0.4);
}

.hookBadge {
  position: absolute;
  top: 1rem;
  right: 1rem;
  padding: 0.25rem 0.75rem;
  background: var(--accent-primary);
  color: white;
  font-size: 0.75rem;
  font-weight: bold;
  border-radius: 4px;
}

.dialogueBubble {
  position: absolute;
  transform: translate(-50%, -50%);
  max-width: 60%;
  padding: 0.75rem 1rem;
  background: white;
  border-radius: 1rem;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.bubbleText {
  font-family: 'Noto Sans JP', sans-serif;
  font-size: 0.875rem;
  color: #1a1a1a;
}

.editOverlay {
  position: absolute;
  inset: 0;
  background: rgba(0, 0, 0, 0.7);
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 0;
  transition: opacity 0.3s;
}

.panel:hover .editOverlay {
  opacity: 1;
}

.editOverlay span {
  padding: 0.5rem 1rem;
  background: var(--accent-secondary);
  color: white;
  font-size: 0.875rem;
  border-radius: 4px;
}

.sceneNav {
  position: fixed;
  left: 1rem;
  top: 50%;
  transform: translateY(-50%);
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.navDot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: var(--border-subtle);
  border: none;
  cursor: pointer;
  transition: all 0.2s;
}

.navDot:hover {
  background: var(--accent-secondary);
  transform: scale(1.2);
}

.navDot.hook {
  background: var(--accent-primary);
}

.endCard {
  text-align: center;
  padding: 4rem;
  font-family: 'Bebas Neue', sans-serif;
  font-size: 2rem;
  color: var(--text-secondary);
}
```

---

## Part 3: Data Flow Summary

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                              GENERATION FLOW                                  │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  USER INPUT                                                                  │
│  ├── Story Seed (text)                                                       │
│  └── Target Scene Count (number)                                             │
│              │                                                               │
│              ▼                                                               │
│  ┌─────────────────┐                                                         │
│  │ Story Architect │ ──► Narrative arcs, themes, hook identification         │
│  └────────┬────────┘                                                         │
│           │                                                                  │
│           ▼                                                                  │
│  ┌──────────────────┐                                                        │
│  │ Character Designer│ ──► Character bank with stable prompts                │
│  └────────┬─────────┘                                                        │
│           │                                                                  │
│           ▼                                                                  │
│  ┌───────────────┐                                                           │
│  │ Panel Composer │ ──► Scene/Panel structure with composition prompts       │
│  └────────┬──────┘                                                           │
│           │                                                                  │
│           ▼                                                                  │
│  ┌─────────────────┐                                                         │
│  │ Image Generator │ ──► Gemini 2.5 Flash ──► 9:16 images (no text)         │
│  └────────┬────────┘                                                         │
│           │                                                                  │
│           ▼                                                                  │
│  ┌──────────────────┐                                                        │
│  │ Output Assembler │ ──► Complete Webtoon JSON                              │
│  └──────────────────┘                                                        │
│                                                                              │
├──────────────────────────────────────────────────────────────────────────────┤
│                              EDITING FLOW                                     │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  FRONTEND                                                                    │
│  ├── Preview: Vertical scroll with click-to-edit panels                      │
│  └── Editor: Fabric.js canvas for drag/drop dialogue bubbles                 │
│              │                                                               │
│              ▼                                                               │
│  ┌─────────────────┐                                                         │
│  │ Zustand Store   │ ──► Live position updates                               │
│  └────────┬────────┘                                                         │
│           │                                                                  │
│           ▼                                                                  │
│  ┌─────────────────┐                                                         │
│  │ API: PUT update │ ──► Persist dialogue positions                          │
│  └─────────────────┘                                                         │
│                                                                              │
├──────────────────────────────────────────────────────────────────────────────┤
│                              EXPORT FLOW                                      │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  EXPORT REQUEST                                                              │
│              │                                                               │
│              ▼                                                               │
│  ┌─────────────────┐                                                         │
│  │ Video Exporter  │                                                         │
│  │  ├── Load panels                                                          │
│  │  ├── Overlay dialogues (one at a time)                                    │
│  │  ├── Calculate durations from text length                                 │
│  │  └── FFmpeg render to MP4                                                 │
│  └────────┬────────┘                                                         │
│           │                                                                  │
│           ▼                                                                  │
│  OUTPUT: 9:16 MP4 video                                                      │
│  ├── Each scene displayed                                                    │
│  ├── Dialogues appear sequentially                                           │
│  └── Smooth transitions between panels                                       │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## Part 4: Key Implementation Details

### 4.1 Character Consistency Strategy

```python
# Character reference prompt structure for Gemini
CHARACTER_PROMPT_TEMPLATE = """
{name}:
- Age/Gender: {age_gender}
- Face: {face_description}
- Hair: {hair_description}  
- Build: {body_type}
- Outfit: {clothing_description}
- Distinctive features: {distinguishing_marks}
- Color signature: {color_palette}

IMPORTANT: Maintain exact appearance across all panels.
"""
```

### 4.2 Hook Scene Detection

```python
def identify_hook_scene(narrative_arcs: list) -> int:
    """Identify the best hook/thumbnail scene"""
    
    # Priority order for hook scenes:
    # 1. Dramatic reveal in Peak arc
    # 2. Emotional climax
    # 3. Action peak
    # 4. First establishing shot (fallback)
    
    hook_keywords = [
        "reveal", "discover", "shocking", "realize",
        "confront", "transform", "explosion", "clash"
    ]
    
    for arc in narrative_arcs:
        if arc["name"] == "Peak":
            for beat in arc["beats"]:
                if any(kw in beat["description"].lower() for kw in hook_keywords):
                    return beat["scene_index"]
    
    # Fallback to first peak scene
    for arc in narrative_arcs:
        if arc["name"] == "Peak":
            return arc["beats"][0]["scene_index"]
    
    return 0  # First scene as last resort
```

### 4.3 Dialogue Duration Calculator

```typescript
// Calculate display time based on reading speed
function calculateDialogueDuration(text: string): number {
  const WORDS_PER_MINUTE = 200;
  const MIN_DURATION = 1500; // 1.5 seconds minimum
  const MAX_DURATION = 6000; // 6 seconds maximum
  
  const wordCount = text.split(/\s+/).length;
  const readingTime = (wordCount / WORDS_PER_MINUTE) * 60 * 1000;
  
  return Math.max(MIN_DURATION, Math.min(MAX_DURATION, readingTime));
}
```

### 4.4 Vertical Spacing Rules

```python
# Gutter spacing based on narrative beat
SPACING_RULES = {
    "Initial": 100,      # Normal flow
    "Rising": 80,        # Faster pacing
    "Peak": 200,         # Dramatic pause before climax
    "Falling": 120,      # Slightly slower
    "Release": 160,      # Let moment breathe
    
    # Special cases
    "scene_transition": 400,  # Major scene change
    "cliffhanger": 300,       # Before end of chapter
    "action_sequence": 50,    # Rapid succession
}
```

---

## Part 5: Technology Stack Summary

| Layer | Technology | Purpose |
|-------|------------|---------|
| **Backend Framework** | FastAPI | Async API server |
| **Agent Orchestration** | LangGraph | Multi-agent workflow |
| **LLM (Planning)** | Claude Sonnet 4.5 | Story/character/panel planning |
| **LLM (Images)** | Gemini 2.5 Flash | 9:16 image generation |
| **State Management** | LangGraph MemorySaver | Checkpointing & recovery |
| **Frontend Framework** | Next.js 14 + React | SSR + SPA hybrid |
| **Canvas Editor** | Fabric.js | Drag/drop dialogue bubbles |
| **Animations** | Framer Motion | Smooth transitions |
| **State (Frontend)** | Zustand | Lightweight store |
| **Styling** | CSS Modules | Scoped styles |
| **Video Export** | FFmpeg | MP4 rendering |
| **Storage** | S3/GCS | Image & video storage |

---

This architecture provides a complete, production-ready system for transforming story seeds into interactive webtoons with draggable dialogues and MP4 export. 핵심은 LangGraph의 multi-agent 구조로 각 단계를 체계적으로 처리하고, Fabric.js로 사용자가 대화 버블을 자유롭게 편집할 수 있게 하는 것입니다.
