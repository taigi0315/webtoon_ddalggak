import asyncio
from dataclasses import dataclass, field
from datetime import datetime
import threading
import uuid
from typing import Any, Callable


JobHandler = Callable[["JobRecord"], dict | None]


@dataclass
class JobRecord:
    job_id: uuid.UUID
    job_type: str
    status: str
    created_at: datetime
    updated_at: datetime
    payload: dict[str, Any] = field(default_factory=dict)
    request_id: str | None = None
    result: dict | None = None
    error: str | None = None
    progress: dict | None = None
    cancel_requested: bool = False
    handler: JobHandler | None = None


_jobs: dict[uuid.UUID, JobRecord] = {}
_jobs_lock = threading.Lock()
_queue: asyncio.Queue[uuid.UUID] | None = None
_worker_task: asyncio.Task | None = None
_loop: asyncio.AbstractEventLoop | None = None


def _utcnow() -> datetime:
    return datetime.utcnow()


def enqueue_job(
    job_type: str,
    payload: dict[str, Any],
    handler: JobHandler,
    *,
    request_id: str | None = None,
) -> JobRecord:
    if _queue is None or _loop is None:
        raise RuntimeError("job queue is not running")

    job_id = uuid.uuid4()
    now = _utcnow()
    job = JobRecord(
        job_id=job_id,
        job_type=job_type,
        status="queued",
        created_at=now,
        updated_at=now,
        payload=payload,
        request_id=request_id,
        handler=handler,
    )
    with _jobs_lock:
        _jobs[job_id] = job

    asyncio.run_coroutine_threadsafe(_queue.put(job_id), _loop)
    return job


def get_job(job_id: uuid.UUID) -> JobRecord | None:
    with _jobs_lock:
        return _jobs.get(job_id)


def list_jobs() -> list[JobRecord]:
    with _jobs_lock:
        return list(_jobs.values())


def update_job_progress(job_id: uuid.UUID, progress: dict) -> None:
    with _jobs_lock:
        job = _jobs.get(job_id)
        if job is None:
            return
        job.progress = progress
        job.updated_at = _utcnow()


def cancel_job(job_id: uuid.UUID) -> JobRecord | None:
    with _jobs_lock:
        job = _jobs.get(job_id)
        if job is None:
            return None
        if job.status in {"succeeded", "failed", "cancelled"}:
            return job
        job.cancel_requested = True
        if job.status == "queued":
            job.status = "cancelled"
            job.updated_at = _utcnow()
        return job


async def _worker_loop() -> None:
    assert _queue is not None
    while True:
        job_id = await _queue.get()
        job = get_job(job_id)
        if job is None:
            _queue.task_done()
            continue
        if job.status == "cancelled":
            _queue.task_done()
            continue
        if job.cancel_requested:
            with _jobs_lock:
                job.status = "cancelled"
                job.updated_at = _utcnow()
            _queue.task_done()
            continue

        with _jobs_lock:
            job.status = "running"
            job.updated_at = _utcnow()

        try:
            if job.handler is None:
                raise RuntimeError("job handler missing")
            result = await asyncio.to_thread(job.handler, job)
        except Exception as exc:  # noqa: BLE001
            with _jobs_lock:
                job.status = "failed"
                job.error = str(exc)
                job.updated_at = _utcnow()
        else:
            with _jobs_lock:
                job.status = "succeeded"
                job.result = result
                job.updated_at = _utcnow()
        finally:
            _queue.task_done()


async def start_worker() -> None:
    global _queue, _worker_task, _loop
    if _worker_task is not None:
        return
    _loop = asyncio.get_running_loop()
    _queue = asyncio.Queue()
    _worker_task = asyncio.create_task(_worker_loop())


async def stop_worker() -> None:
    global _worker_task, _queue, _loop
    if _worker_task is None:
        return
    _worker_task.cancel()
    try:
        await _worker_task
    except asyncio.CancelledError:
        pass
    _worker_task = None
    _queue = None
    _loop = None
