from fastapi import APIRouter

from app.api.v1 import (
    artifacts,
    characters,
    dialogue,
    environments,
    episode_planning,
    episodes,
    exports,
    gemini,
    generation,
    layers,
    projects,
    review,
    scenes,
    stories,
    styles,
)


api_router = APIRouter(prefix="/v1")

api_router.include_router(projects.router)
api_router.include_router(stories.router)
api_router.include_router(scenes.router)
api_router.include_router(characters.router)
api_router.include_router(artifacts.router)
api_router.include_router(gemini.router)
api_router.include_router(generation.router)
api_router.include_router(review.router)
api_router.include_router(styles.router)
api_router.include_router(dialogue.router)
api_router.include_router(environments.router)
api_router.include_router(exports.router)
api_router.include_router(episodes.router)
api_router.include_router(episode_planning.router)
api_router.include_router(layers.router)
