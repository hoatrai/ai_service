"""
Cấu hình tập trung cho AI Service.
Đọc từ biến môi trường (.env) — xem .env.example để biết danh sách đầy đủ.
"""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # LLM
    openai_api_key: str = ""
    openai_model_name: str = "gpt-4o-mini"

    # WordPress (custom-api-core)
    wordpress_base_url: str = "https://spiritwebs.okinawanew.com"
    wordpress_jwt_endpoint: str = "/wp-json/jwt-auth/v1/token"

    # Phoenix
    phoenix_base_url: str = "https://socket.okinawanew.com"

    # Service
    ai_service_port: int = 8088
    ai_service_internal_key: str = "change-me-please"
    log_level: str = "INFO"


@lru_cache
def get_settings() -> Settings:
    return Settings()
