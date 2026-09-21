from pydantic_settings import BaseSettings, SettingsConfigDict


class VlmSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="VLM_",
        extra="ignore",
    )

    api_key: str = ""
    url: str = ""
    quality: float = 60.0
