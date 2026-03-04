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
    database_url: str | None = Field(default=None, alias="DATABASE_URL")
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
    # provider -> use WhatsApp/Brevo
    # local_log_only -> skip providers and print OTP in backend logs
    otp_delivery_mode: str = Field(
        default="provider", alias="OTP_DELIVERY_MODE")
    otp_debug_log_plaintext: bool = Field(
        default=False, alias="OTP_DEBUG_LOG_PLAINTEXT")
    # WhatsApp Cloud API
    whatsapp_access_token: str = Field(
        default="", alias="WHATSAPP_ACCESS_TOKEN")
    whatsapp_phone_number_id: str = Field(
        default="", alias="WHATSAPP_PHONE_NUMBER_ID")
    whatsapp_api_version: str = Field(
        default="v22.0", alias="WHATSAPP_API_VERSION")
    whatsapp_otp_template_name: str = Field(
        default="", alias="WHATSAPP_OTP_TEMPLATE_NAME")
    whatsapp_otp_template_lang: str = Field(
        default="en_US", alias="WHATSAPP_OTP_TEMPLATE_LANG")
    whatsapp_waba_id: str = Field(default="", alias="WHATSAPP_WABA_ID")
    # CMS (Strapi)
    strapi_base_url: str = Field(
        default="http://localhost:1337/api", alias="STRAPI_BASE_URL")
    strapi_api_token: str = Field(default="", alias="STRAPI_API_TOKEN")
    strapi_timeout_seconds: int = Field(
        default=10, alias="STRAPI_TIMEOUT_SECONDS")
    # Brevo transactional email (fallback OTP delivery)
    brevo_api_key: str = Field(default="", alias="BREVO_API_KEY")
    brevo_api_base_url: str = Field(
        default="https://api.brevo.com/v3", alias="BREVO_API_BASE_URL")
    brevo_sender_email: str = Field(default="", alias="BREVO_SENDER_EMAIL")
    brevo_sender_name: str = Field(
        default="VidyaTrack", alias="BREVO_SENDER_NAME")
    brevo_otp_subject: str = Field(
        default="Your VidyaTrack OTP", alias="BREVO_OTP_SUBJECT")
    cors_allow_origins: str = Field(
        default=(
            "http://localhost:5173,"
            "http://127.0.0.1:5173,"
            "https://vidyatrack-dev.vercel.app"
        ),
        alias="CORS_ALLOW_ORIGINS",
    )

    # Pydantic v2 settings configuration
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        populate_by_name=True,  # allows access via field names while supporting aliases
    )


settings = Settings()
