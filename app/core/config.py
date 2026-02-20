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
    db_host: str = Field(default="127.0.0.1", alias="DB_HOST")
    db_port: int = Field(default=5432, alias="DB_PORT")
    db_name: str = Field(default="vidyatrack", alias="DB_NAME")
    db_user: str = Field(default="vidyatrack", alias="DB_USER")
    db_password: str = Field(default="change_me", alias="DB_PASSWORD")
    # Auth / Security
    jwt_secret: str = Field(default="change_me", alias="JWT_SECRET")
    jwt_ttl_minutes: int = Field(default=30, alias="JWT_TTL_MINUTES")
    otp_pepper: str = Field(default="change_me", alias="OTP_PEPPER")
    otp_ttl_minutes: int = Field(default=5, alias="OTP_TTL_MINUTES")
    # CMS (Strapi)
    strapi_base_url: str = Field(default="http://localhost:1337/api", alias="STRAPI_BASE_URL")
    strapi_api_token: str = Field(default="", alias="STRAPI_API_TOKEN")
    strapi_timeout_seconds: int = Field(default=10, alias="STRAPI_TIMEOUT_SECONDS")


    # Pydantic v2 settings configuration
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        populate_by_name=True,  # allows access via field names while supporting aliases
    )


settings = Settings()
