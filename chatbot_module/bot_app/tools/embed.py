import time
from typing import List, Tuple

from bot_app.log import get_logger

logger = get_logger(__name__)


class EmbedTools:
    @staticmethod
    def compute_dense_vector(text: str) -> List[float]:
        """
        Encode 1 query text → dense vector dùng Gemma-300m (FP16).
        Phục vụ Semantic Search.
        """
        start = time.perf_counter()
        try:
            from bot_app.application import application

            model = application.get_model("dense_embedder")
            if not model:
                raise RuntimeError("Dense embedder model is not loaded in Application instance.")

            vector = model.encode(text, normalize_embeddings=True).tolist()

            logger.info(
                f"Dense embedding: {(time.perf_counter() - start) * 1000:.2f} ms "
                f"| dim={len(vector)}"
            )
            return vector
        except Exception as e:
            logger.error(f"compute_dense_vector failed: {e}", exc_info=True)
            raise

    @staticmethod
    def compute_sparse_vector(text: str) -> Tuple[List[int], List[float]]:
        """
        Encode 1 query text → sparse vector (indices, values) dùng BM25 (FastEmbed).
        Phục vụ Keyword Search.
        """
        start = time.perf_counter()
        try:
            from bot_app.application import application

            model = application.get_model("sparse_embedder")
            if not model:
                raise RuntimeError("Sparse embedder model is not loaded in Application instance.")

            # Sử dụng API của FastEmbedSparse để tạo sparse vector cho query
            # model.embed_query trả về object SparseVector có thuộc tính 'indices' và 'values' (đã là list hoặc ndarray)
            sparse_result = model.embed_query(text)
            
            indices = list(sparse_result.indices)
            values = list(sparse_result.values)

            logger.info(
                f"Sparse embedding (BM25): {(time.perf_counter() - start) * 1000:.2f} ms "
                f"| nonzero={len(indices)}"
            )
            return indices, values
        except Exception as e:
            logger.error(f"compute_sparse_vector failed: {e}", exc_info=True)
            # Fallback: Trả về vector rỗng để không làm crash toàn bộ flow RAG
            return [], []

    @staticmethod
    def hybrid_embed_query(
        text: str,
    ) -> Tuple[List[float], List[int], List[float]]:
        """
        Tổng hợp Dense + Sparse cho 1 query của người dùng.
        Sẵn sàng cho Qdrant Hybrid Search.
        """
        start = time.perf_counter()
        try:
            dense_vector = EmbedTools.compute_dense_vector(text)
            sparse_indices, sparse_values = EmbedTools.compute_sparse_vector(text)

            logger.info(
                f"Hybrid query total: {(time.perf_counter() - start) * 1000:.2f} ms "
                f"| dense_dim={len(dense_vector)} | sparse_nnz={len(sparse_indices)}"
            )
            return dense_vector, sparse_indices, sparse_values
        except Exception as e:
            logger.error(f"hybrid_embed_query failed: {e}", exc_info=True)
            raise

    @staticmethod
    def get_embedding_dimension() -> int:
        """Trả về số chiều dense vector (Thường là 768 cho Gemma-300m)."""
        from bot_app.application import application

        model = application.get_model("dense_embedder")
        if hasattr(model, "get_sentence_embedding_dimension"):
            return model.get_sentence_embedding_dimension()
        return 768 # Fallback for Gemma-300m
