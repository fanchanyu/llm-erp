import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "LLM-ERP"
    debug: bool = True

    # Database
    database_url: str = "postgresql+asyncpg://erp_user:erp_pass_dev@localhost:5432/llm_erp"

    # LLM Provider — 支援多家 LLM，使用者自己選
    # provider: anthropic, openai, deepseek, openrouter, ollama
    llm_provider: str = "anthropic"
    llm_model: str = ""

    # API Keys (只填你用的那家就好)
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    deepseek_api_key: str = ""
    openrouter_api_key: str = ""

    # Ollama (本地 LLM，不需要 API Key)
    ollama_base_url: str = "http://localhost:11434"

    # Server
    host: str = "0.0.0.0"
    port: int = 8000

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    @property
    def active_api_key(self) -> str:
        """回傳當前啟用 provider 的 API Key"""
        return getattr(self, f"{self.llm_provider}_api_key", "") or ""

    @property
    def active_model(self) -> str:
        """回傳當前啟用 provider 的預設 model"""
        if self.llm_model:
            return self.llm_model
        defaults = {
            "anthropic": "claude-sonnet-4-20250514",
            "openai": "gpt-4o",
            "deepseek": "deepseek-chat",
            "openrouter": "anthropic/claude-sonnet-4",
            "ollama": "qwen2.5:7b",
        }
        return defaults.get(self.llm_provider, "gpt-4o")


settings = Settings()
