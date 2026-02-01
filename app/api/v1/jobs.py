import uuid

from fastapi import APIRouter, HTTPException, Response

from app.api.v1.schemas import JobStatusRead
from app.services import job_queue


router = APIRouter(tags=["jobs"])


def _job_or_404(job_id: uuid.UUID):
    job = job_queue.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job not found")
    return job


@router.get("/jobs/{job_id}", response_model=JobStatusRead)
def get_job(job_id: uuid.UUID):
    job = _job_or_404(job_id)
    return JobStatusRead(
        job_id=job.job_id,
        job_type=job.job_type,
        status=job.status,
        created_at=job.created_at.isoformat(),
        updated_at=job.updated_at.isoformat(),
        progress=job.progress,
        result=job.result,
        error=job.error,
    )


@router.post("/jobs/{job_id}/cancel", response_model=JobStatusRead)
def cancel_job(job_id: uuid.UUID, response: Response):
    job = job_queue.cancel_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job not found")
    if job.status == "cancelled":
        response.status_code = 202
    return JobStatusRead(
        job_id=job.job_id,
        job_type=job.job_type,
        status=job.status,
        created_at=job.created_at.isoformat(),
        updated_at=job.updated_at.isoformat(),
        progress=job.progress,
        result=job.result,
        error=job.error,
    )
