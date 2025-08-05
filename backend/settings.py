from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    jwt_secret: str = Field("CHANGE_ME", validation_alias="JWT_SECRET")
    jwt_algorithm: str = Field("HS256", validation_alias="JWT_ALGORITHM")
    access_ttl_minutes: int = Field(15, validation_alias="ACCESS_TTL_MINUTES")
    refresh_ttl_days: int = Field(30, validation_alias="REFRESH_TTL_DAYS")

    auth_backend: str = Field("db", validation_alias="AUTH_BACKEND")  # db | keycloak

    postgres_host: str = Field("localhost", validation_alias="POSTGRES_HOST")
    postgres_port: str = Field("5432", validation_alias="POSTGRES_PORT")
    postgres_user: str = Field("postgres", validation_alias="POSTGRES_USER")
    postgres_password: str = Field("postgres", validation_alias="POSTGRES_PASSWORD")
    postgres_db: str = Field("integration_server", validation_alias="POSTGRES_DB")

    model_config = SettingsConfigDict(env_file=".env")


def get_settings() -> Settings:  # Singleton-ish helper
    from functools import lru_cache

    @lru_cache()
    def _get() -> Settings:
        return Settings()

    return _get() 