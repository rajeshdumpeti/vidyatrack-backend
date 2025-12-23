from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Central application configuration.

    Loads values from environment variables (preferred) and optionally from a local `.env` file.
    This enables multi-environment deployments without environment-specific branches.
    """

    app_name: str = Field(default="vidyatrack-backend", alias="APP_NAME")
    environment: str = Field(default="dev", alias="ENVIRONMENT")
    debug: bool = Field(default=True, alias="DEBUG")

    # Pydantic v2 settings configuration
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        populate_by_name=True,  # allows access via field names while supporting aliases
    )


settings = Settings()
