from langchain_core.tools import tool


from app.services.job_services import JobService

from app.log import get_logger
logger = get_logger(__name__)


@tool
async def list_all_jobs() -> dict:
    """Lấy danh sách tất cả vị trí tuyển dụng hiện có.
    Dùng tool này khi người dùng hỏi về các vị trí tuyển dụng, công việc đang mở, hoặc cơ hội nghề nghiệp.
    """
    logger.info("[list_all_jobs] fetching all jobs from service")

    result = await JobService.list_all()
    logger.info(f"[list_all_jobs] returned {result.total} jobs")

    return result.model_dump(mode="json")
