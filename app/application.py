from pathlib import Path
from typing import Any, Dict

from app.log import get_logger

logger = get_logger(__name__)

WEIGHTS_DIR = Path(__file__).parent.parent / "weights"

class Application:
    def __init__(self):
        self.models: Dict[str, Any] = {}
        self.llm: Dict[str, Any] = {}

    def load_models(self) -> None:
        import torch
        from sentence_transformers import SentenceTransformer
        from FlagEmbedding import BGEM3FlagModel

        device = "cuda" if torch.cuda.is_available() else "cpu"
        logger.info(f"Loading embedding models on device={device}...")

        dense_model = SentenceTransformer(
            str(WEIGHTS_DIR / "embeddinggemma-300m"),
            device=device,
        )
        self.models["dense_embedder"] = dense_model
        logger.info("Loaded dense model: weights/embeddinggemma-300m")

        sparse_model = BGEM3FlagModel(
            "BAAI/bge-m3",
            use_fp16=True,
            device=device,
        )
        self.models["sparse_embedder"] = sparse_model
        logger.info("Loaded sparse model: BAAI/bge-m3")

        logger.info(f"All embedding models loaded | device={device}")


    def get_model(self, name_model: str) -> Any:
        return self.models[name_model]

    def cleanup_model(self) -> None:
        self.models.clear()
        logger.info("Embedding models cleared")

# application = Application()