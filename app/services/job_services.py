import uuid
from datetime import datetime, timezone
from typing import Optional

from app.schema.redis_schema import JobCreate, JobListResponse, JobResponse, JobUpdate
from app.tools.redis import client as redis

from app.log import get_logger
logger = get_logger(__name__)

_JOBS_HASH_KEY = "jobs"

def _now() -> datetime:
    return datetime.now(timezone.utc)

class JobService:
    
    @staticmethod
    async def create(body: JobCreate) -> JobResponse:
        now = _now()
        job = JobResponse(
            id=str(uuid.uuid4()),
            title=body.title,
            department=body.department,
            description=body.description,
            requirements=body.requirements,
            salary_range=body.salary_range,
            location=body.location,
            slots=body.slots,
            status="open",
            created_at=now,
            updated_at=now,
        )
        await redis.hset(_JOBS_HASH_KEY, job.id, job.model_dump_json())

        logger.info(f"[JobService.create] id={job.id} title='{job.title}'")
        return job

    @staticmethod
    async def list_all() -> JobListResponse:
        raws = await redis.hvals(_JOBS_HASH_KEY)

        if not raws:
            return JobListResponse(total=0, items=[])

        items = [JobResponse.model_validate_json(r) for r in raws]
        items.sort(key=lambda x: x.created_at, reverse=True)

        return JobListResponse(total=len(items), items=items)

    @staticmethod
    async def get(job_id: str) -> Optional[JobResponse]:
        raw = await redis.hget(_JOBS_HASH_KEY, job_id)
        return JobResponse.model_validate_json(raw) if raw else None

    @staticmethod
    async def update(job_id: str, body: JobUpdate) -> Optional[JobResponse]:
        raw = await redis.hget(_JOBS_HASH_KEY, job_id)
        if not raw:
            return None

        job = JobResponse.model_validate_json(raw)
        patch = body.model_dump(exclude_none=True)
        updated = job.model_copy(update={**patch, "updated_at": _now()})

        await redis.hset(_JOBS_HASH_KEY, job_id, updated.model_dump_json())

        logger.info(f"[JobService.update] id={job_id} fields={list(patch.keys())}")
        return updated

    @staticmethod
    async def delete(job_id: str) -> bool:
        deleted = await redis.hdel(_JOBS_HASH_KEY, job_id)

        if deleted == 0:
            return False

        logger.info(f"[JobService.delete] id={job_id}")
        return True