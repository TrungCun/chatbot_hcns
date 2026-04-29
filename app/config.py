from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # --- LLM Configurations ---
    llm_base_url: str
    llm_model: str
    llm_temperature: float = 0.0
    llm_max_tokens: int = 2048
    llm_support_vision: bool = True

    # --- Qdrant Configurations ---
    qdrant_url: str
    qdrant_api_key: str
    qdrant_collection: str

    # --- Redis Configurations ---
    redis_host: str = "localhost"
    redis_port: int = 6380

    @property
    def redis_url(self) -> str:
        return f"redis://{self.redis_host}:{self.redis_port}/0"

    # --- Embedding Configuration ---
    embedding_model_name: str = "sentence-transformers/all-MiniLM-L6-v2"

    # Cấu hình file .env
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()