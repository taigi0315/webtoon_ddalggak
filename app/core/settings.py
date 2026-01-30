from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = Field(default="sqlite+pysqlite:///./dev.db", validation_alias="DATABASE_URL")
    db_auto_create: bool = Field(default=True, validation_alias="DB_AUTO_CREATE")

    log_level: str = Field(default="INFO", validation_alias="LOG_LEVEL")

    google_cloud_project: str | None = Field(default=None, validation_alias="GOOGLE_CLOUD_PROJECT")
    google_cloud_location: str = Field(default="us-central1", validation_alias="GOOGLE_CLOUD_LOCATION")

    gemini_api_key: str | None = Field(default=None, validation_alias="GEMINI_API_KEY")
    gemini_text_model: str = Field(default="gemini-2.5-flash", validation_alias="GEMINI_TEXT_MODEL")
    gemini_image_model: str = Field(default="gemini-2.5-flash-image", validation_alias="GEMINI_IMAGE_MODEL")
    gemini_fallback_text_model: str | None = Field(
        default="gemini-2.0-flash",
        validation_alias="GEMINI_FALLBACK_TEXT_MODEL",
    )
    gemini_fallback_image_model: str | None = Field(
        default=None,
        validation_alias="GEMINI_FALLBACK_IMAGE_MODEL",
    )
    gemini_max_retries: int = Field(default=3, validation_alias="GEMINI_MAX_RETRIES")
    gemini_initial_backoff_seconds: float = Field(
        default=0.8,
        validation_alias="GEMINI_INITIAL_BACKOFF_SECONDS",
    )
    gemini_timeout_seconds: float = Field(default=60.0, validation_alias="GEMINI_TIMEOUT_SECONDS")
    gemini_circuit_breaker_threshold: int = Field(
        default=5,
        validation_alias="GEMINI_CIRCUIT_BREAKER_THRESHOLD",
    )
    gemini_circuit_breaker_timeout: int = Field(
        default=60,
        validation_alias="GEMINI_CIRCUIT_BREAKER_TIMEOUT",
    )

    media_root: str = Field(default="./storage/media", validation_alias="MEDIA_ROOT")
    media_url_prefix: str = Field(default="/media", validation_alias="MEDIA_URL_PREFIX")
    log_file: str | None = Field(default=None, validation_alias="LOG_FILE")

    @property
    def DATABASE_URL(self) -> str:  # pragma: no cover
        return self.database_url

    @property
    def DB_AUTO_CREATE(self) -> bool:  # pragma: no cover
        return self.db_auto_create


settings = Settings()
