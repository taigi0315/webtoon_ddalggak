import uuid

from fastapi import APIRouter, HTTPException

from app.api.deps import DbSessionDep
from app.api.v1.schemas import StoryCreate, StoryRead
from app.db.models import Project, Story


router = APIRouter(tags=["stories"])


@router.post("/projects/{project_id}/stories", response_model=StoryRead)
def create_story(project_id: uuid.UUID, payload: StoryCreate, db=DbSessionDep):
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="project not found")

    story = Story(project_id=project_id, title=payload.title)
    db.add(story)
    db.commit()
    db.refresh(story)
    return story


@router.get("/stories/{story_id}", response_model=StoryRead)
def get_story(story_id: uuid.UUID, db=DbSessionDep):
    story = db.get(Story, story_id)
    if story is None:
        raise HTTPException(status_code=404, detail="story not found")
    return story
