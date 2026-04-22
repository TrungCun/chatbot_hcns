from fastapi import APIRouter, HTTPException

from app.log import get_logger
from app.schema.redis_schema import JobCreate, JobListResponse, JobResponse, JobUpdate
from app.services.job_services import JobService

logger = get_logger(__name__)

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


@router.post("", response_model=JobResponse, status_code=201)
async def create_job(body: JobCreate) -> JobResponse:
    return await JobService.create(body)


@router.get("", response_model=JobListResponse)
async def list_jobs() -> JobListResponse:
    return await JobService.list_all()


@router.get("/{job_id}", response_model=JobResponse)
async def get_job(job_id: str) -> JobResponse:
    job = await JobService.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Không tìm thấy vị trí id={job_id}")
    return job


@router.put("/{job_id}", response_model=JobResponse)
async def update_job(job_id: str, body: JobUpdate) -> JobResponse:
    updated = await JobService.update(job_id, body)
    if updated is None:
        raise HTTPException(status_code=404, detail=f"Không tìm thấy vị trí id={job_id}")
    return updated


@router.delete("/{job_id}", status_code=204)
async def delete_job(job_id: str) -> None:
    ok = await JobService.delete(job_id)
    if not ok:
        raise HTTPException(status_code=404, detail=f"Không tìm thấy vị trí id={job_id}")
