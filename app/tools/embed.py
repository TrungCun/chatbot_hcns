import time
from typing import List, Tuple

from app.log import get_logger

logger = get_logger(__name__)


class EmbedTools:
    @staticmethod
    def compute_dense_vector(text: str) -> List[float]:
        """Encode 1 text → dense vector dùng Vietnamese_Embedding_v2."""
        start = time.perf_counter()
        try:
            from app.application import application

            model = application.get_model("dense_embedder")
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
    def compute_dense_vectors(texts: List[str], batch_size: int = 32) -> List[List[float]]:
        """Batch encode nhiều texts → list dense vectors."""
        start = time.perf_counter()
        try:
            from app.application import application

            model = application.get_model("dense_embedder")
            vectors = model.encode(
                texts,
                batch_size=batch_size,
                normalize_embeddings=True,
                show_progress_bar=len(texts) > 50,
            ).tolist()

            logger.info(
                f"Dense batch encode: {len(texts)} texts | "
                f"{(time.perf_counter() - start) * 1000:.2f} ms"
            )
            return vectors
        except Exception as e:
            logger.error(f"compute_dense_vectors failed: {e}", exc_info=True)
            raise

    @staticmethod
    def compute_sparse_vector(text: str) -> Tuple[List[int], List[float]]:
        """Encode 1 text → sparse vector (indices, values) dùng BGE-M3."""
        start = time.perf_counter()
        try:
            from app.application import application

            model = application.get_model("sparse_embedder")
            output = model.encode(
                [text],
                return_dense=False,
                return_sparse=True,
                return_colbert_vecs=False,
            )

            lexical_weights = output["lexical_weights"][0]
            indices = [int(k) for k in lexical_weights.keys()]
            values = [float(v) for v in lexical_weights.values()]

            logger.info(
                f"Sparse embedding: {(time.perf_counter() - start) * 1000:.2f} ms "
                f"| nonzero={len(indices)}"
            )
            return indices, values
        except Exception as e:
            logger.error(f"compute_sparse_vector failed: {e}", exc_info=True)
            raise

    @staticmethod
    def compute_sparse_vectors(
        texts: List[str], batch_size: int = 32
    ) -> List[Tuple[List[int], List[float]]]:
        """Batch encode nhiều texts → list sparse vectors."""
        start = time.perf_counter()
        try:
            from app.application import application

            model = application.get_model("sparse_embedder")
            output = model.encode(
                texts,
                batch_size=batch_size,
                return_dense=False,
                return_sparse=True,
                return_colbert_vecs=False,
            )

            results = []
            for lexical_weights in output["lexical_weights"]:
                indices = [int(k) for k in lexical_weights.keys()]
                values = [float(v) for v in lexical_weights.values()]
                results.append((indices, values))

            logger.info(
                f"Sparse batch encode: {len(texts)} texts | "
                f"{(time.perf_counter() - start) * 1000:.2f} ms"
            )
            return results
        except Exception as e:
            logger.error(f"compute_sparse_vectors failed: {e}", exc_info=True)
            raise

    @staticmethod
    def hybrid_embed_query(
        text: str,
    ) -> Tuple[List[float], List[int], List[float]]:
        """
        Encode 1 query → (dense_vector, sparse_indices, sparse_values).
        Dùng khi retrieval (không phải ingestion).
        """
        start = time.perf_counter()
        try:
            dense_vector = EmbedTools.compute_dense_vector(text)
            sparse_indices, sparse_values = EmbedTools.compute_sparse_vector(text)

            logger.info(
                f"Hybrid query embed: {(time.perf_counter() - start) * 1000:.2f} ms "
                f"| dense_dim={len(dense_vector)} | sparse_nnz={len(sparse_indices)}"
            )
            return dense_vector, sparse_indices, sparse_values
        except Exception as e:
            logger.error(f"hybrid_embed_query failed: {e}", exc_info=True)
            raise

    @staticmethod
    def hybrid_embed_batch(
        texts: List[str], batch_size: int = 32
    ) -> Tuple[List[List[float]], List[Tuple[List[int], List[float]]]]:
        """
        Batch encode nhiều texts → (dense_vectors, sparse_vectors).
        Dùng khi ingestion pipeline.
        """
        start = time.perf_counter()
        try:
            dense_vectors = EmbedTools.compute_dense_vectors(texts, batch_size)
            sparse_vectors = EmbedTools.compute_sparse_vectors(texts, batch_size)

            logger.info(
                f"Hybrid batch embed: {len(texts)} texts | "
                f"{(time.perf_counter() - start) * 1000:.2f} ms"
            )
            return dense_vectors, sparse_vectors
        except Exception as e:
            logger.error(f"hybrid_embed_batch failed: {e}", exc_info=True)
            raise

    @staticmethod
    def get_embedding_dimension() -> int:
        """Trả về số chiều dense vector (1024 cho Vietnamese_Embedding_v2)."""
        from app.application import application

        model = application.get_model("dense_embedder")
        return model.get_sentence_embedding_dimension()
