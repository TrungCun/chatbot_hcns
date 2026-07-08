from typing import Any, Dict, List, Optional
from langchain_core.tools import tool
from bot_app.prompt.loader import load_tool_description
from bot_app.tools.embed import EmbedTools
from bot_app.tools.qdrant import QdrantTools
from bot_app.config import settings

from bot_app.log import get_logger
logger = get_logger(__name__)

_description = load_tool_description("tools/retrieve_from_vector_database")

@tool("retrieve_from_vector_database", description=_description)
async def retrieve_from_vector_database(
    prompt: str,
    limit: int = 20,
) -> List[Dict[str, Any]]:
    """
    Truy xuất tài liệu từ Qdrant sử dụng Hybrid Search (Dense + Sparse) + RRF.
    Dành cho Agent gọi khi cần tìm kiếm thông tin tri thức về HCNS.
    """
    logger.info(f"[retrieve_from_vector_database] Tool called | Query: {prompt[:50]}...")

    try:
        # 1. Nhúng Query (Hybrid) - Sử dụng model đã loaded trong Application
        query_dense, query_indices, query_values = EmbedTools.hybrid_embed_query(
            text=prompt
        )

        # 2. Truy xuất từ Qdrant (Sử dụng Hybrid RRF trực tiếp từ Qdrant)
        collection_name = settings.qdrant_collection
        scored_points = QdrantTools.retrieve(
            collection_name=collection_name,
            query=query_dense,
            query_indices=query_indices,
            query_values=query_values,
            limit=limit,
        )

        # 3. Format kết quả trả về cho Agent
        results = []
        for point in scored_points:
            payload = point.payload or {}
            results.append({
                "content": payload.get("page_content", ""),
                "metadata": payload.get("metadata", {}),
                "score": point.score
            })
        
        # Log chi tiết các chunk để kiểm tra
        for i, res in enumerate(results):
            logger.info("==============================================================")
            logger.info(f"[retrieve_from_vector_database] Chunk {i+1} | Score: {res['score']:.4f} | Source: {res['metadata'].get('source')} | Content: {res['content']}")

        logger.info(f"[retrieve_from_vector_database] Returned {len(results)} relevant documents.")
        return results

    except Exception as e:
        logger.error(f"[retrieve_from_vector_database] Error: {e}", exc_info=True)
        return [{"error": "Hệ thống tri thức đang gặp sự cố, không thể tra cứu thông tin lúc này."}]
