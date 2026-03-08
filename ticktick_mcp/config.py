from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    TICKTICK_CLIENT_ID: str
    TICKTICK_CLIENT_SECRET: str
    TICKTICK_REDIRECT_URI: str

    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8')


@lru_cache()
def get_settings():
    return Settings()
