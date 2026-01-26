from fastapi import APIRouter

from app.api.v1 import artifacts, characters, gemini, generation, projects, review, scenes, stories


api_router = APIRouter(prefix="/v1")

api_router.include_router(projects.router)
api_router.include_router(stories.router)
api_router.include_router(scenes.router)
api_router.include_router(characters.router)
api_router.include_router(artifacts.router)
api_router.include_router(gemini.router)
api_router.include_router(generation.router)
api_router.include_router(review.router)
