from typing import Any, Dict, List

from app.log import get_logger
from app.tools.embed import EmbedTools
from app.tools.helper import HelperTools
from app.tools.qdrant import QdrantTools

logger = get_logger(__name__)


async def upsert(collection_name: str, data: List[Dict[str, Any]]) -> None:
    """
    Nhận list documents (chunks từ PDF), embed và lưu vào Qdrant.

    Mỗi document phải có field 'content' là nội dung chunk cần embed.
    Các field còn lại sẽ được lưu vào payload.
    """
    try:
        if not data:
            logger.info("No data to upsert.")
            return

        # Flatten fields (list → string, None → "")
        docs_data = [
            {k: HelperTools.flatten_field(v) for k, v in doc.items()}
            for doc in data
        ]

        logger.info(f"Upserting {len(docs_data)} documents into '{collection_name}'...")

        # Lấy nội dung chunk để embed (field 'content')
        texts = [str(doc.get("content", "")).strip() for doc in docs_data]

        empty_texts = [i for i, t in enumerate(texts) if not t]
        if empty_texts:
            logger.warning(f"{len(empty_texts)} documents có content rỗng tại index: {empty_texts}")

        # Batch embed dense + sparse cùng lúc (tối ưu GPU)
        logger.info("Generating embeddings...")
        dense_vectors, sparse_vectors = EmbedTools.hybrid_embed_batch(
            texts, batch_size=32
        )
        logger.info(f"Embeddings generated: {len(dense_vectors)} dense, {len(sparse_vectors)} sparse")

        # Lưu vào Qdrant
        QdrantTools.add_vectors(
            collection_name=collection_name,
            dense_vectors=dense_vectors,
            sparse_vectors=sparse_vectors,
            docs_data=docs_data,
        )

        logger.info(f"Upsert completed: {len(docs_data)} documents → '{collection_name}'")

    except Exception as e:
        logger.error(f"Upsert failed: {e}", exc_info=True)
        raise
