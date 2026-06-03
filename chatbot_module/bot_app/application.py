import os
import torch
from typing import Any, Optional

from sentence_transformers import SentenceTransformer, CrossEncoder
from langchain_qdrant import FastEmbedSparse

from bot_app.config import settings

from bot_app.log import get_logger
logger = get_logger(__name__)

class Application:
    _instance: Optional['Application'] = None
    _initialized: bool = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Application, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if not self._initialized:
            self.models: dict[str, Any] = {}
            self._initialized = True
            logger.info("[APPLICATION] Application Singleton initialized.")


    def load_models(self) -> None:
        """
        Khởi tạo và load các model cần thiết vào memory với cơ chế Error Handling.
        """
        device = "cuda" if torch.cuda.is_available() else "cpu"
        logger.info(f"[APPLICATION] Loading models on: {device} (Physical GPU: {os.environ.get('CUDA_VISIBLE_DEVICES')})")
        
        try:
            model_path = settings.embedding_model_path
            if not os.path.exists(model_path):
                logger.error(f"[APPLICATION] Model path not found: {model_path}")
                raise FileNotFoundError(f"Missing weights at {model_path}")

            logger.info(f"[APPLICATION] Loading Dense Embedder from {model_path}...")
            self.models["dense_embedder"] = SentenceTransformer(
                model_path, 
                device=device,
                trust_remote_code=True
            )

            logger.info(f"[APPLICATION] Initializing Sparse Embedder ({settings.sparse_model_name})...")
            self.models["sparse_embedder"] = FastEmbedSparse(model_name=settings.sparse_model_name)

            rerank_path = settings.reranker_model_path
            if not os.path.exists(rerank_path):
                logger.error(f"[APPLICATION] Reranker model path not found: {rerank_path}")
                raise FileNotFoundError(f"Missing weights at {rerank_path}")
            logger.info(f"[APPLICATION] Loading Reranker from {rerank_path}...")
            self.models["reranker"] = CrossEncoder(
                rerank_path,
                device=device,
                trust_remote_code=True
            )

            logger.info("[APPLICATION] All units standing by.")

        except Exception as e:
            logger.critical(f"[APPLICATION] FAILED TO START APPLICATION: {e}", exc_info=True)
            raise

    def get_model(self, name: str) -> Optional[Any]:
        model = self.models.get(name)
        if not model:
            logger.warning(f"[APPLICATION] Model '{name}' requested but not loaded!")
        return model

    def cleanup_models(self) -> None:
        self.models.clear()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            torch.cuda.ipc_collect()
        logger.info("[APPLICATION] Resource cleanup completed.")

application = Application()
