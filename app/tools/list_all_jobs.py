from langchain_core.tools import tool
from app.prompt.loader import load_tool_description

from app.services.job_services import JobService

from app.log import get_logger
logger = get_logger(__name__)

_description = load_tool_description("tools/list_all_jobs")

@tool("list_all_jobs", description=_description)
async def list_all_jobs() -> dict:
    logger.info("[list_all_jobs] fetching all jobs from service")
    try:
        result = await JobService.list_all()

        if result.total == 0:
            return "Hiện tại không có vị trí tuyển dụng nào đang mở."

        logger.info(f"[list_all_jobs] returned {result.total} jobs")

        return result.model_dump(mode="json")
    except Exception as e:
        logger.error(f"[list_all_jobs] Error: {e}", exc_info=True)
        return "Hệ thống đang bận, không thể lấy danh sách công việc lúc này. Xin vui lòng thử lại sau."