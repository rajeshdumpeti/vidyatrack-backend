from functools import lru_cache
from typing import Any, Literal

from pydantic import AliasChoices, Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

AppEnvironment = Literal["dev", "stage", "prod", "test"]


class Settings(BaseSettings):
    """
    Central application configuration.

    The application code stays identical across dev, stage, and prod. Only
    `APP_ENV`/`ENVIRONMENT` and the matching environment variables change.
    """

    app_name: str = Field(default="vidyatrack-backend", alias="APP_NAME")
    environment: AppEnvironment = Field(
        default="dev",
        validation_alias=AliasChoices("APP_ENV", "ENVIRONMENT"),
    )
    debug: bool | None = Field(default=None, alias="DEBUG")

    # `DATABASE_URL` is an explicit override for one-off jobs and local tooling.
    # Normal multi-environment deploys use the env-specific URLs below.
    database_url: str | None = Field(default=None, alias="DATABASE_URL")
    database_url_dev: str | None = Field(
        default=None, alias="DATABASE_URL_DEV")
    database_url_stage: str | None = Field(
        default=None, alias="DATABASE_URL_STAGE")
    database_url_prod: str | None = Field(
        default=None, alias="DATABASE_URL_PROD")
    database_url_test: str | None = Field(
        default=None, alias="DATABASE_URL_TEST")

    # Local development fallback if DATABASE_URL* is intentionally omitted.
    db_host: str = Field(default="127.0.0.1", alias="DB_HOST")
    db_port: int = Field(default=5432, alias="DB_PORT")
    db_name: str = Field(default="vidyatrack", alias="DB_NAME")
    db_user: str = Field(default="vidyatrack", alias="DB_USER")
    db_password: str = Field(default="change_me", alias="DB_PASSWORD")

    # Shared SQLAlchemy pool overrides. If unset, environment-specific defaults apply.
    db_pool_size: int | None = Field(default=None, alias="DB_POOL_SIZE")
    db_max_overflow: int | None = Field(default=None, alias="DB_MAX_OVERFLOW")
    db_pool_timeout: int | None = Field(default=None, alias="DB_POOL_TIMEOUT")
    db_pool_recycle_seconds: int | None = Field(
        default=None,
        alias="DB_POOL_RECYCLE_SECONDS",
    )

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
        default=False,
        alias="OTP_DEBUG_LOG_PLAINTEXT",
    )

    # WhatsApp Cloud API (Meta) — commented out, replaced by Twilio
    # whatsapp_access_token: str = Field(default="", alias="WHATSAPP_ACCESS_TOKEN")
    # whatsapp_phone_number_id: str = Field(default="", alias="WHATSAPP_PHONE_NUMBER_ID")
    # whatsapp_api_version: str = Field(default="v22.0", alias="WHATSAPP_API_VERSION")
    # whatsapp_otp_template_name: str = Field(default="", alias="WHATSAPP_OTP_TEMPLATE_NAME")
    # whatsapp_otp_template_lang: str = Field(default="en_US", alias="WHATSAPP_OTP_TEMPLATE_LANG")
    # whatsapp_waba_id: str = Field(default="", alias="WHATSAPP_WABA_ID")

    # Twilio WhatsApp
    twilio_account_sid: str = Field(default="", alias="TWILIO_ACCOUNT_SID")
    twilio_auth_token: str = Field(default="", alias="TWILIO_AUTH_TOKEN")
    # Sandbox: whatsapp:+14155238886 — change to your approved number in prod
    twilio_whatsapp_from: str = Field(
        default="whatsapp:+14155238886",
        alias="TWILIO_WHATSAPP_FROM",
    )

    # CMS (Strapi)
    strapi_base_url: str = Field(
        default="http://localhost:1337/api",
        alias="STRAPI_BASE_URL",
    )
    strapi_api_token: str = Field(default="", alias="STRAPI_API_TOKEN")
    strapi_timeout_seconds: int = Field(
        default=10, alias="STRAPI_TIMEOUT_SECONDS")

    # Brevo transactional email (fallback OTP delivery)
    brevo_api_key: str = Field(default="", alias="BREVO_API_KEY")
    brevo_api_base_url: str = Field(
        default="https://api.brevo.com/v3",
        alias="BREVO_API_BASE_URL",
    )
    brevo_sender_email: str = Field(default="", alias="BREVO_SENDER_EMAIL")
    brevo_sender_name: str = Field(
        default="VidyaTrack", alias="BREVO_SENDER_NAME")
    brevo_otp_subject: str = Field(
        default="Your VidyaTrack OTP",
        alias="BREVO_OTP_SUBJECT",
    )

    # Super admin bootstrap (set once per environment, never changes after)
    super_admin_phone: str | None = Field(default=None, alias="SUPER_ADMIN_PHONE")
    super_admin_email: str | None = Field(default=None, alias="SUPER_ADMIN_EMAIL")

    cors_allow_origins: str = Field(
        default="",
        alias="CORS_ALLOW_ORIGINS",
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_ignore_empty=True,
        extra="ignore",
        populate_by_name=True,
    )

    @field_validator("environment", mode="before")
    @classmethod
    def normalize_environment(cls, value: Any) -> Any:
        if isinstance(value, str):
            return value.strip().lower()
        return value

    @field_validator("debug", mode="before")
    @classmethod
    def normalize_debug(cls, value: Any) -> Any:
        if value is None or isinstance(value, bool):
            return value
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"1", "true", "yes", "on", "debug", "development"}:
                return True
            if normalized in {"0", "false", "no", "off", "release", "production"}:
                return False
        return value

    @model_validator(mode="after")
    def apply_environment_defaults(self) -> "Settings":
        if self.debug is None:
            self.debug = self.environment in {"dev", "test"}

        if self.environment in {"stage", "prod"}:
            insecure_defaults: list[str] = []
            if self.jwt_secret == "change_me":
                insecure_defaults.append("JWT_SECRET")
            if self.otp_pepper == "change_me":
                insecure_defaults.append("OTP_PEPPER")
            if insecure_defaults:
                joined = ", ".join(insecure_defaults)
                raise ValueError(
                    f"{joined} must be set for APP_ENV={self.environment}.",
                )

        return self

    def _database_url_by_environment(self) -> dict[AppEnvironment, str | None]:
        return {
            "dev": self.database_url_dev,
            "stage": self.database_url_stage,
            "prod": self.database_url_prod,
            "test": self.database_url_test,
        }

    def _build_local_database_url(self) -> str:
        return (
            f"postgresql+psycopg://{self.db_user}:"
            f"{self.db_password}@{self.db_host}:"
            f"{self.db_port}/{self.db_name}"
        )

    @property
    def resolved_database_url(self) -> str:
        if self.database_url:
            return self.database_url

        environment_url = self._database_url_by_environment().get(self.environment)
        if environment_url:
            return environment_url

        if self.environment in {"dev", "test"}:
            return self._build_local_database_url()

        raise ValueError(
            "Database URL is missing for the active environment. "
            f"Set DATABASE_URL or DATABASE_URL_{self.environment.upper()}.",
        )

    @property
    def effective_db_pool_size(self) -> int:
        if self.db_pool_size is not None:
            return self.db_pool_size

        defaults: dict[AppEnvironment, int] = {
            "dev": 2,
            "stage": 4,
            "prod": 8,
            "test": 1,
        }
        return defaults[self.environment]

    @property
    def effective_db_max_overflow(self) -> int:
        if self.db_max_overflow is not None:
            return self.db_max_overflow

        defaults: dict[AppEnvironment, int] = {
            "dev": 2,
            "stage": 4,
            "prod": 8,
            "test": 0,
        }
        return defaults[self.environment]

    @property
    def effective_db_pool_timeout(self) -> int:
        if self.db_pool_timeout is not None:
            return self.db_pool_timeout

        defaults: dict[AppEnvironment, int] = {
            "dev": 15,
            "stage": 20,
            "prod": 30,
            "test": 5,
        }
        return defaults[self.environment]

    @property
    def effective_db_pool_recycle_seconds(self) -> int:
        if self.db_pool_recycle_seconds is not None:
            return self.db_pool_recycle_seconds

        defaults: dict[AppEnvironment, int] = {
            "dev": 900,
            "stage": 1200,
            "prod": 1500,
            "test": 300,
        }
        return defaults[self.environment]

    @property
    def sqlalchemy_engine_options(self) -> dict[str, Any]:
        database_url = self.resolved_database_url
        if database_url.startswith("sqlite"):
            return {
                "pool_pre_ping": True,
            }

        return {
            "pool_pre_ping": True,
            "pool_use_lifo": True,
            "pool_size": self.effective_db_pool_size,
            "max_overflow": self.effective_db_max_overflow,
            "pool_timeout": self.effective_db_pool_timeout,
            "pool_recycle": self.effective_db_pool_recycle_seconds,
        }


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
