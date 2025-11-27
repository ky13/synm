"""Configuration management for Sanctum."""

from functools import lru_cache
from pathlib import Path
from typing import List, Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # API Server
    api_host: str = Field(default="0.0.0.0", description="API server host")
    api_port: int = Field(default=8080, description="API server port")
    api_workers: int = Field(default=4, description="Number of API workers")
    log_level: str = Field(default="INFO", description="Logging level")

    # Security
    secret_key: str = Field(
        default="change-this-secret-key-in-production",
        description="Secret key for JWT signing",
    )
    jwt_algorithm: str = Field(default="HS256", description="JWT algorithm")
    jwt_expiration_minutes: int = Field(default=30, description="JWT expiration time")
    api_key_salt: str = Field(
        default="change-this-salt", description="Salt for API key hashing"
    )

    # Database
    database_url: str = Field(
        default="sqlite+aiosqlite:///./data/sanctum.db",
        description="Main database URL",
    )
    audit_log_db: str = Field(
        default="sqlite+aiosqlite:///./data/audit.db",
        description="Audit log database URL",
    )

    # Vector Database
    chroma_host: str = Field(default="localhost", description="Chroma host")
    chroma_port: int = Field(default=8000, description="Chroma port")
    chroma_collection: str = Field(
        default="sanctum_vault", description="Chroma collection name"
    )

    # Ollama
    ollama_host: str = Field(
        default="http://localhost:11434", description="Ollama API host"
    )
    ollama_embedding_model: str = Field(
        default="nomic-embed-text", description="Ollama embedding model"
    )
    ollama_summarization_model: str = Field(
        default="llama2", description="Ollama summarization model"
    )

    # Redis Cache
    redis_url: str = Field(
        default="redis://localhost:6379/0", description="Redis connection URL"
    )
    cache_ttl_seconds: int = Field(default=900, description="Cache TTL in seconds")

    # Policy Settings
    policy_file: str = Field(
        default="./policies/default.yaml", description="Policy configuration file"
    )
    default_context_ttl_minutes: int = Field(
        default=15, description="Default context TTL"
    )
    max_context_tokens: int = Field(
        default=2000, description="Maximum context tokens"
    )

    # Redaction Settings
    enable_pii_redaction: bool = Field(
        default=True, description="Enable PII redaction"
    )
    redaction_confidence_threshold: float = Field(
        default=0.7, description="Redaction confidence threshold"
    )

    # Rate Limiting
    rate_limit_requests_per_minute: int = Field(
        default=60, description="Rate limit per minute"
    )
    rate_limit_burst: int = Field(default=10, description="Rate limit burst size")

    # Audit Settings
    audit_retention_days: int = Field(
        default=90, description="Audit log retention in days"
    )
    audit_export_format: str = Field(
        default="json", description="Audit export format"
    )

    # CORS
    cors_origins: List[str] = Field(
        default_factory=lambda: ["http://localhost:3000", "http://localhost:8080"],
        description="Allowed CORS origins",
    )

    # TLS/mTLS
    tls_enabled: bool = Field(default=False, description="Enable TLS")
    tls_cert_file: str = Field(
        default="./certs/server.crt", description="TLS certificate file"
    )
    tls_key_file: str = Field(
        default="./certs/server.key", description="TLS key file"
    )
    mtls_enabled: bool = Field(default=False, description="Enable mTLS")
    mtls_ca_file: str = Field(default="./certs/ca.crt", description="mTLS CA file")

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        """Parse CORS origins from comma-separated string."""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v

    @property
    def chroma_url(self) -> str:
        """Get Chroma database URL."""
        return f"http://{self.chroma_host}:{self.chroma_port}"

    @property
    def data_dir(self) -> Path:
        """Get data directory path."""
        return Path("./data")

    @property
    def logs_dir(self) -> Path:
        """Get logs directory path."""
        return Path("./logs")

    def ensure_directories(self) -> None:
        """Ensure required directories exist."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        Path("./policies").mkdir(parents=True, exist_ok=True)
        Path("./notes").mkdir(parents=True, exist_ok=True)


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    settings = Settings()
    settings.ensure_directories()
    return settings