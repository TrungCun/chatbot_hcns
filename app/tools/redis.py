from redis.asyncio import Redis, ConnectionPool
from app.config import settings

from app.log import get_logger
logger = get_logger(__name__)

redis_client: Redis | None = None

async def init_redis():
    global redis_client
    try:
        pool = ConnectionPool.from_url(
            settings.redis_url,
            decode_responses=True,
            max_connections=20,
            socket_timeout=5.0
        )

        redis_client = Redis(connection_pool=pool)

        await redis_client.ping()
        logger.info(f"Kết nối Redis thành công tại {settings.redis_url}")

    except Exception as e:
        logger.error(f"Khởi tạo Redis thất bại: {e}")
        raise e

async def close_redis():
    global redis_client
    if redis_client:
        await redis_client.close()
        logger.info("Đã đóng kết nối Redis an toàn.")

def get_redis() -> Redis:
    if redis_client is None:
        raise RuntimeError("Redis chưa được khởi tạo! Hãy chắc chắn init_redis() đã chạy trong lifespan.")
    return redis_client

