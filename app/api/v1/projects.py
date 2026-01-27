import uuid

from fastapi import APIRouter, HTTPException, Response
from sqlalchemy import select

from app.api.deps import DbSessionDep
from app.api.v1.schemas import ProjectCreate, ProjectRead
from app.db.models import Project


router = APIRouter(tags=["projects"])


@router.post("/projects", response_model=ProjectRead)
def create_project(payload: ProjectCreate, db=DbSessionDep):
    project = Project(name=payload.name)
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


@router.get("/projects", response_model=list[ProjectRead])
def list_projects(db=DbSessionDep):
    return list(db.execute(select(Project)).scalars().all())


@router.delete("/projects/{project_id}", status_code=204)
def delete_project(project_id: uuid.UUID, db=DbSessionDep):
    project = get_project_or_404(db, project_id)
    db.delete(project)
    db.commit()
    return Response(status_code=204)


def get_project_or_404(db, project_id: uuid.UUID) -> Project:
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="project not found")
    return project
