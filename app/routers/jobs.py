from typing import Annotated
from fastapi import APIRouter, Form, HTTPException, status, Depends, Body

from app.schema.redis_schema import JobCreate, JobListResponse, JobResponse, JobUpdate
from app.services.job_services import JobService, get_job_service

from app.log import get_logger
logger = get_logger(__name__)

router = APIRouter(prefix="/api/jobs", tags=["Jobs"])

@router.post("", response_model=JobResponse, status_code=status.HTTP_201_CREATED)
async def create_job(
    body: Annotated[JobCreate, Form()],
    # body: Annotated[JobCreate, Body()],
    service: JobService = Depends(get_job_service)
    ) -> JobResponse:
    return await service.create(body)


@router.get("", response_model=JobListResponse, status_code=status.HTTP_200_OK)
async def list_jobs(
    service: JobService = Depends(get_job_service)
    ) -> JobListResponse:
    return await service.list_all()


@router.get(
        "/{job_id}",
        response_model=JobResponse,
        status_code=status.HTTP_200_OK,
        responses={
            status.HTTP_404_NOT_FOUND: {"description": "Không tìm thấy Job với ID tương ứng"}
            })
async def get_job(
    job_id: str,
    service: JobService = Depends(get_job_service)
    ) -> JobResponse:
    job = await service.get(job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Không tìm thấy vị trí id={job_id}")
    return job


@router.patch(
        "/{job_id}",
        response_model=JobResponse,
        status_code=status.HTTP_200_OK,
        responses={
            status.HTTP_404_NOT_FOUND: {"description": "Không tìm thấy Job để cập nhật"}
            })
async def update_job(
    job_id: str,
    body: Annotated[JobUpdate, Form()],
    # body: Annotated[JobUpdate, Body()],
    service: JobService = Depends(get_job_service)
    ) -> JobResponse:
    updated = await service.update(job_id, body)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Không tìm thấy vị trí id={job_id} để cập nhật"
        )
    return updated


@router.delete(
        "/{job_id}",
        status_code=status.HTTP_204_NO_CONTENT,
        responses={
            status.HTTP_404_NOT_FOUND: {"description": "Không tìm thấy Job để xóa"}
            })
async def delete_job(
    job_id: str,
    service: JobService = Depends(get_job_service)
    ) -> None:
    ok = await service.delete(job_id)
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Không tìm thấy vị trí id={job_id} để xóa"
            )