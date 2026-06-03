from langchain_core.tools import tool
from sqlalchemy import text
from bot_app.prompt.loader import load_tool_description
from bot_app.tools.mysql import get_mysql_engine

from bot_app.log import get_logger
logger = get_logger(__name__)

_description = load_tool_description("tools/check_jobs")

@tool("check_jobs", description=_description)
async def check_jobs(query: str) -> dict:
    """Thực thi câu lệnh SQL được tạo ra để truy vấn thông tin tuyển dụng từ MySQL."""
    logger.info(f"[check_jobs] executing query: {query}")
    try:
        engine = get_mysql_engine()
        with engine.connect() as conn:
            rows = conn.execute(text(query)).mappings().fetchall()

        if not rows:
            return "Không tìm thấy kết quả phù hợp với truy vấn."

        result = [dict(row) for row in rows]
        logger.info(f"[check_jobs] returned {len(result)} rows")
        return result
    except Exception as e:
        logger.error(f"[check_jobs] Error: {e}", exc_info=True)
        return f"Lỗi khi thực thi truy vấn: {str(e)}"
