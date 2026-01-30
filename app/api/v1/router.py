from fastapi import APIRouter

from app.api.v1 import (
    artifacts,
    character_variants,
    characters,
    config,
    dialogue,
    environments,
    episode_planning,
    episodes,
    exports,
    gemini,
    generation,
    internal_generation,
    jobs,
    layers,
    projects,
    review,
    scenes,
    stories,
    style_presets,
    styles,
)


api_router = APIRouter(prefix="/v1")

api_router.include_router(projects.router)
api_router.include_router(stories.router)
api_router.include_router(scenes.router)
api_router.include_router(characters.router)
api_router.include_router(character_variants.router)
api_router.include_router(artifacts.router)
api_router.include_router(gemini.router)
api_router.include_router(generation.router)
api_router.include_router(internal_generation.router)
api_router.include_router(jobs.router)
api_router.include_router(review.router)
api_router.include_router(styles.router)
api_router.include_router(dialogue.router)
api_router.include_router(environments.router)
api_router.include_router(exports.router)
api_router.include_router(episodes.router)
api_router.include_router(episode_planning.router)
api_router.include_router(layers.router)
api_router.include_router(config.router)
api_router.include_router(style_presets.router)
