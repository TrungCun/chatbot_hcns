from datetime import datetime, timezone
from typing import Optional, List, Any
import json

from app.schema.summary_schema import CVTemplate
from app.tools.redis import client as redis
from app.log import get_logger

logger = get_logger(__name__)

_CANDIDATES_HASH_KEY = "candidates"

def _now() -> datetime:
    return datetime.now(timezone.utc)

class CandidateService:
    """
    Service quản lý thông tin ứng viên và hồ sơ (CV) đã trích xuất.
    Tái sử dụng pattern xử lý Redis Hash từ JobService.
    """

    @staticmethod
    async def save_profile(
        session_id: str,
        template: CVTemplate,
        summary: str,
        metadata: Optional[dict] = None
    ) -> bool:
        """
        Lưu hoặc cập nhật hồ sơ ứng viên vào Redis.
        """
        try:
            now = _now()

            # Chuẩn bị dữ liệu lưu trữ
            # Chúng ta gom template, summary và thông tin bổ sung vào một object duy nhất
            profile_data = {
                "session_id": session_id,
                "template": template.model_dump(),
                "summary": summary,
                "metadata": metadata or {},
                "updated_at": now.isoformat()
            }

            # Kiểm tra xem đã có bản ghi cũ chưa để giữ lại created_at nếu cần
            # (Ở đây tạm thời tối giản hóa theo hướng Upsert)
            await redis.hset(_CANDIDATES_HASH_KEY, session_id, json.dumps(profile_data, ensure_ascii=False))

            logger.info(f"[CandidateService.save_profile] session_id={session_id} saved successfully.")
            return True
        except Exception as e:
            logger.error(f"[CandidateService.save_profile] Error saving profile for {session_id}: {e}")
            return False

    @staticmethod
    async def get_profile(session_id: str) -> Optional[dict]:
        """
        Lấy thông tin hồ sơ ứng viên theo session_id.
        """
        raw = await redis.hget(_CANDIDATES_HASH_KEY, session_id)
        if not raw:
            return None

        return json.loads(raw)

    @staticmethod
    async def list_all_profiles() -> List[dict]:
        """
        Liệt kê danh sách tất cả ứng viên đã lưu.
        """
        raws = await redis.hvals(_CANDIDATES_HASH_KEY)
        if not raws:
            return []

        profiles = [json.loads(r) for r in raws]
        # Sắp xếp theo thời gian cập nhật mới nhất
        profiles.sort(key=lambda x: x.get("updated_at", ""), reverse=True)

        return profiles

    @staticmethod
    async def delete_profile(session_id: str) -> bool:
        """
        Xóa hồ sơ ứng viên.
        """
        deleted = await redis.hdel(_CANDIDATES_HASH_KEY, session_id)
        if deleted > 0:
            logger.info(f"[CandidateService.delete_profile] deleted session_id={session_id}")
            return True
        return False
