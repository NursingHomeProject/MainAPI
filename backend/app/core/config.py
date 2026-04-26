from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = Field(default="Casa Assistencial API", alias="APP_NAME")
    app_env: str = Field(default="development", alias="APP_ENV")
    app_debug: bool = Field(default=True, alias="APP_DEBUG")
    app_host: str = Field(default="0.0.0.0", alias="APP_HOST")
    app_port: int = Field(default=8000, alias="APP_PORT")
    app_timezone: str = Field(default="America/Sao_Paulo", alias="APP_TIMEZONE")
    dose_administration_tolerance_minutes: int = Field(
        default=30,
        alias="DOSE_ADMINISTRATION_TOLERANCE_MINUTES",
    )
    database_url: str = Field(
        default="postgresql+psycopg://postgres:postgres@localhost:5432/casa_assistencial",
        alias="DATABASE_URL",
    )
    jwt_secret_key: str = Field(
        default="change-this-secret-in-production",
        alias="JWT_SECRET_KEY",
    )
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    access_token_expire_minutes: int = Field(
        default=60,
        alias="ACCESS_TOKEN_EXPIRE_MINUTES",
    )
    seed_admin_on_startup: bool = Field(default=True, alias="SEED_ADMIN_ON_STARTUP")
    admin_full_name: str = Field(default="Administrador", alias="ADMIN_FULL_NAME")
    admin_email: str = Field(default="admin@casa.local", alias="ADMIN_EMAIL")
    admin_password: str = Field(default="admin123456", alias="ADMIN_PASSWORD")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
