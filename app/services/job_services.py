import uuid
from datetime import datetime, timezone
from typing import Optional
from fastapi import Depends
from redis.asyncio import Redis

from app.schema.redis_schema import JobCreate, JobListResponse, JobResponse, JobUpdate
from app.tools.redis import get_redis

from app.log import get_logger
logger = get_logger(__name__)

_JOBS_HASH_KEY = "jobs"

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()

class JobService:
    def __init__(self, redis_client: Redis):
        self.redis = redis_client

    async def create(self, body: JobCreate) -> JobResponse:
        now = _now()
        job = JobResponse(
            id=str(uuid.uuid4()),
            **body.model_dump(),
            status="open",
            created_at=now,
            updated_at=now,
        )
        await self.redis.hset(_JOBS_HASH_KEY, job.id, job.model_dump_json())

        logger.info(f"[JobService.create] id={job.id} title='{job.title}'")
        return job

    async def list_all(self) -> JobListResponse:
        raws = await self.redis.hvals(_JOBS_HASH_KEY)

        if not raws:
            return JobListResponse(total=0, items=[])

        items = []
        for r in raws:
            try:
                job_obj = JobResponse.model_validate_json(r)
                items.append(job_obj)
            except Exception as e:
                logger.error(f"[JobService.list_all] Failed to parse job record: {e}. Raw data: {r}")
                continue
        items.sort(key=lambda x: x.created_at, reverse=True)

        return JobListResponse(total=len(items), items=items)

    async def get(self, job_id: str) -> Optional[JobResponse]:
        raw = await self.redis.hget(_JOBS_HASH_KEY, job_id)
        if not raw:
            return None
        try:
            return JobResponse.model_validate_json(raw)
        except Exception as e:
            logger.error(f"[JobService.get] Failed to parse job record for id={job_id}: {e}. Raw data: {raw}")
            return None

    async def update(self, job_id: str, body: JobUpdate) -> Optional[JobResponse]:
        raw = await self.redis.hget(_JOBS_HASH_KEY, job_id)
        if not raw:
            return None

        try:
            job = JobResponse.model_validate_json(raw)
        except Exception as e:
            logger.error(f"[JobService.update] Failed to parse existing job record for id={job_id}: {e}. Raw data: {raw}")
            return None
        patch = body.model_dump(exclude_unset=True)

        if not patch:
            return job

        updated = job.model_copy(update={**patch, "updated_at": _now()})

        await self.redis.hset(_JOBS_HASH_KEY, job_id, updated.model_dump_json())

        logger.info(f"[JobService.update] id={job_id} fields={list(patch.keys())}")
        return updated

    async def delete(self, job_id: str) -> bool:
        deleted = await self.redis.hdel(_JOBS_HASH_KEY, job_id)

        if deleted == 0:
            return False

        logger.info(f"[JobService.delete] id={job_id}")
        return True

def get_job_service(redis_client: Redis = Depends(get_redis)) -> JobService:
    return JobService(redis_client)