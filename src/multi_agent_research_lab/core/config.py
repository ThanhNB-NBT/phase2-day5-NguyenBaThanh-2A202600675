"""Application configuration.

Keep config small and explicit. Do not read environment variables directly in agents.
"""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings loaded from environment variables or `.env`."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = Field(default="local", validation_alias="APP_ENV")
    log_level: str = Field(default="INFO", validation_alias="LOG_LEVEL")

    openai_api_key: str | None = Field(default=None, validation_alias="OPENAI_API_KEY")
    nvidia_api_key: str | None = Field(default=None, validation_alias="NVIDIA_API_KEY")
    use_mock_llm: bool = Field(default=False, validation_alias="USE_MOCK_LLM")
    openai_base_url: str = Field(
        default="https://integrate.api.nvidia.com/v1",
        validation_alias="OPENAI_BASE_URL",
    )
    openai_model: str = Field(default="meta/llama-3.1-8b-instruct", validation_alias="OPENAI_MODEL")

    langsmith_api_key: str | None = Field(default=None, validation_alias="LANGSMITH_API_KEY")
    langsmith_project: str = Field(default="multi-agent-research-lab", validation_alias="LANGSMITH_PROJECT")

    tavily_api_key: str | None = Field(default=None, validation_alias="TAVILY_API_KEY")

    max_iterations: int = Field(default=6, ge=1, le=20, validation_alias="MAX_ITERATIONS")
    timeout_seconds: int = Field(default=60, ge=5, le=600, validation_alias="TIMEOUT_SECONDS")
    llm_requests_per_minute: int = Field(default=39, ge=1, le=60, validation_alias="LLM_REQUESTS_PER_MINUTE")
    llm_input_cost_per_1m_tokens: float = Field(default=0.15, ge=0, validation_alias="LLM_INPUT_COST_PER_1M_TOKENS")
    llm_output_cost_per_1m_tokens: float = Field(default=0.15, ge=0, validation_alias="LLM_OUTPUT_COST_PER_1M_TOKENS")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached settings instance."""

    return Settings()
