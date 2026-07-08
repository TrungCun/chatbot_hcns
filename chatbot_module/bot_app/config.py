from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

_APP_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _APP_DIR.parent

from pydantic import Field

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(_REPO_ROOT / ".env", _APP_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        env_prefix=""
    )

    # --- LLM Configurations ---
    llm_base_url: str = Field(...)
    llm_model: str = Field(...)
    llm_temperature: float = 0.0
    llm_max_tokens: int = 4096

    # --- Qdrant Configurations ---
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: str = "dummy"
    qdrant_collection: str = "hcns_knowledge_base"

    # --- Redis Configurations ---
    redis_host: str = "localhost"
    redis_port: int = 6380

    # --- MySQL Configurations ---
    db_host: str = Field(..., alias="DB_HOST")
    db_port: int = Field(3306, alias="DB_PORT")
    db_user: str = Field(..., alias="DB_USER")
    db_password: str = Field(..., alias="DB_PASSWORD")
    db_name: str = Field(..., alias="DB_NAME")

    @property
    def mysql_url(self) -> str:
        return f"mysql+pymysql://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"

    @property
    def redis_url(self) -> str:
        return f"redis://{self.redis_host}:{self.redis_port}/0"

    # --- Embedding Configuration ---
    embedding_model_path: str = str(_REPO_ROOT / "weights/embeddinggemma-300m")
    reranker_model_path: str = str(_REPO_ROOT / "weights/bge-reranker-v2-m3")
    sparse_model_name: str = "Qdrant/bm25"
    gpu_device: str = Field("1", alias="GPU_DEVICE")

settings = Settings()
