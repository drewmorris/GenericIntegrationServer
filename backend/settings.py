from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    jwt_secret: str = 'changeme'
    jwt_algorithm: str = 'HS256'
    access_ttl_minutes: int = 15
    refresh_ttl_days: int = 30
    auth_backend: str = 'db'

    postgres_host: str = 'localhost'
    postgres_port: int = 5432
    postgres_user: str = 'user'
    postgres_password: str = 'password'
    postgres_db: str = 'integration'

    model_config = SettingsConfigDict(env_file=".env")


def get_settings() -> Settings:  # Singleton-ish helper
    from functools import lru_cache

    @lru_cache()
    def _get() -> Settings:
        return Settings()

    return _get() 