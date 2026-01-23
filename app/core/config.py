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

    # WhatsApp Cloud API (pilot-safe)
    whatsapp_enabled: bool = Field(default=False, alias="WHATSAPP_ENABLED")
    whatsapp_access_token: str = Field(
        default="", alias="WHATSAPP_ACCESS_TOKEN")
    whatsapp_phone_number_id: str = Field(
        default="", alias="WHATSAPP_PHONE_NUMBER_ID")
    whatsapp_waba_id: str = Field(default="", alias="WHATSAPP_WABA_ID")
    whatsapp_api_version: str = Field(
        default="v20.0", alias="WHATSAPP_API_VERSION")
    whatsapp_base_url: str = Field(
        default="https://graph.facebook.com", alias="WHATSAPP_BASE_URL")
    whatsapp_timeout_seconds: int = Field(
        default=10, alias="WHATSAPP_TIMEOUT_SECONDS")


# Pydantic v2 settings configuration
model_config = SettingsConfigDict(
    env_file=".env",
    env_file_encoding="utf-8",
    populate_by_name=True,  # allows access via field names while supporting aliases
)


settings = Settings()
