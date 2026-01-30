"""Application configuration using Pydantic Settings."""
from typing import Literal
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # Application Settings
    app_name: str = Field(default="CiteScan", description="Application name")
    app_version: str = Field(default="1.0.0", description="Application version")
    environment: Literal["development", "staging", "production"] = Field(
        default="development",
        description="Runtime environment"
    )

    # Server Configuration
    api_host: str = Field(default="0.0.0.0", description="API server host")
    api_port: int = Field(default=8000, description="API server port")
    gradio_host: str = Field(default="0.0.0.0", description="Gradio server host")
    gradio_port: int = Field(default=7860, description="Gradio server port")

    # API Rate Limiting
    rate_limit_enabled: bool = Field(default=True, description="Enable rate limiting")
    rate_limit_requests: int = Field(default=100, description="Max requests per period")
    rate_limit_period: int = Field(default=60, description="Rate limit period in seconds")

    # Cache Configuration
    cache_enabled: bool = Field(default=True, description="Enable caching")
    cache_ttl: int = Field(default=3600, description="Cache TTL in seconds")
    cache_max_size: int = Field(default=1000, description="Max cached items")

    # Fetcher Configuration
    arxiv_rate_limit_delay: float = Field(default=3.0, description="arXiv rate limit delay")
    crossref_rate_limit_delay: float = Field(default=1.0, description="CrossRef rate limit delay")
    semantic_scholar_rate_limit_delay: float = Field(default=1.0, description="Semantic Scholar rate limit delay")
    dblp_rate_limit_delay: float = Field(default=1.0, description="DBLP rate limit delay")
    openalex_rate_limit_delay: float = Field(default=1.0, description="OpenAlex rate limit delay")
    scholar_rate_limit_delay: float = Field(default=5.0, description="Google Scholar rate limit delay")

    # API Timeouts
    request_timeout: int = Field(default=30, description="Request timeout in seconds")
    max_workers: int = Field(default=10, description="Max concurrent workers")

    # Logging
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO",
        description="Logging level"
    )
    log_format: Literal["json", "text"] = Field(default="json", description="Log format")
    log_file: str = Field(default="logs/citescan.log", description="Log file path")

    # CORS Settings
    cors_origins: str = Field(
        default="http://localhost:3000,http://localhost:8080",
        description="Comma-separated CORS origins"
    )

    # Optional API Keys
    semantic_scholar_api_key: str | None = Field(default=None, description="Semantic Scholar API key")
    crossref_api_key: str | None = Field(default=None, description="CrossRef API key")

    @property
    def cors_origins_list(self) -> list[str]:
        """Parse CORS origins into a list."""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def is_production(self) -> bool:
        """Check if running in production."""
        return self.environment == "production"

    @property
    def is_development(self) -> bool:
        """Check if running in development."""
        return self.environment == "development"


# Global settings instance
settings = Settings()
