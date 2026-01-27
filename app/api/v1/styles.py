from fastapi import APIRouter

from app.api.v1.schemas import StyleItemRead
from app.config.loaders import load_image_styles_v1, load_story_styles_v1


router = APIRouter(tags=["styles"])


@router.get("/styles/story", response_model=list[StyleItemRead])
def list_story_styles():
    library = load_story_styles_v1()
    return [StyleItemRead.model_validate(item) for item in library.styles]


@router.get("/styles/image", response_model=list[StyleItemRead])
def list_image_styles():
    library = load_image_styles_v1()
    return [StyleItemRead.model_validate(item) for item in library.styles]
