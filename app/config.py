from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

_APP_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _APP_DIR.parent

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(_REPO_ROOT / ".env", _APP_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        env_prefix=""
    )

    # --- LLM Configurations ---
    llm_base_url: str = "http://10.0.99.116:8070/v1"
    llm_model: str
    llm_temperature: float = 0.0
    llm_max_tokens: int = 4096

    # --- Qdrant Configurations ---
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: str = "dummy"
    qdrant_collection: str = "hcns_knowledge_base"

    # --- Redis Configurations ---
    redis_host: str = "localhost"
    redis_port: int = 6380

    @property
    def redis_url(self) -> str:
        return f"redis://{self.redis_host}:{self.redis_port}/0"

    # --- Embedding Configuration ---
    embedding_model_path: str = "weights/embeddinggemma-300m"
    sparse_model_name: str = "Qdrant/bm25"
    gpu_device: str = "1"

settings = Settings()