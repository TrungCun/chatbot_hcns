import time
from typing import Any, Dict, List, Optional
from qdrant_client import QdrantClient, models
from qdrant_client.models import QueryResponse
from app.config import settings
from app.log import get_logger

logger = get_logger(__name__)

class QdrantTools:
    _client: Optional[QdrantClient] = None

    @classmethod
    def get_client(cls) -> QdrantClient:
        if cls._client is None:
            cls._client = QdrantClient(
                url=settings.qdrant_url,
                api_key=settings.qdrant_api_key
            )
        return cls._client

    @staticmethod
    def retrieve(
        collection_name: str,
        query: List[float],
        query_indices: List[int],
        query_values: List[float],
        limit: int = 10,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Any]:
        """
        Thực hiện hybrid search: 1 dense search + 1 sparse search kết hợp RRF trên server Qdrant.
        """
        client = QdrantTools.get_client()
        start = time.perf_counter()
        
        # Xử lý filters nếu có (hiện tại chưa dùng)
        qdrant_filter = None

        try:
            # Chuyển đổi query sang list thuần để đảm bảo không có kiểu dữ liệu lạ
            dense_query = list(query)
            
            # Sử dụng query_points để thực hiện Hybrid Search (Dense + Sparse) 
            # kết hợp RRF trực tiếp trên server Qdrant v1.10+.
            prefetch_limit = limit * 3
            response = client.query_points(
                collection_name=collection_name,
                prefetch=[
                    models.Prefetch(
                        query=dense_query,
                        using="dense-embedding",
                        limit=prefetch_limit,
                    ),
                    models.Prefetch(
                        query=models.SparseVector(
                            indices=query_indices,
                            values=query_values
                        ),
                        using="sparse-embedding",
                        limit=prefetch_limit,
                    ),
                ],
                query=models.FusionQuery(
                    fusion=models.Fusion.RRF
                ),
                limit=limit
            )

            logger.info(f"Qdrant Hybrid Retrieval (RRF): {(time.perf_counter() - start) * 1000:.2f} ms")
            return response.points

        except Exception as e:
            logger.error(f"Qdrant retrieval failed: {e}", exc_info=True)
            raise
