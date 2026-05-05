import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "LLM-ERP"
    debug: bool = True

    # Database
    database_url: str = "postgresql+asyncpg://erp_user:erp_pass_dev@localhost:5432/llm_erp"

    # LLM
    anthropic_api_key: str = ""

    # Server
    host: str = "0.0.0.0"
    port: int = 8000

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
