"""Configuration management for SkillMeat API service.

This module provides environment-based configuration using Pydantic Settings.
Supports both development and production environments with secure defaults.
"""

import logging
import os
from enum import Enum
from pathlib import Path
from typing import List, Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(str, Enum):
    """Application environment types."""

    DEVELOPMENT = "development"
    PRODUCTION = "production"
    TESTING = "testing"


class APISettings(BaseSettings):
    """API service configuration.

    Configuration is loaded from environment variables with SKILLMEAT_ prefix.
    Example: SKILLMEAT_ENV=production, SKILLMEAT_PORT=8080

    For development, a .env file can be used in the project root.
    """

    model_config = SettingsConfigDict(
        env_prefix="SKILLMEAT_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Environment
    env: Environment = Field(
        default=Environment.DEVELOPMENT,
        description="Application environment (development, production, testing)",
    )

    # Server configuration
    host: str = Field(
        default="127.0.0.1",
        description="Host address to bind the server",
    )

    port: int = Field(
        default=8080,
        ge=1024,
        le=65535,
        description="Port number to bind the server",
    )

    reload: bool = Field(
        default=False,
        description="Enable auto-reload on code changes (dev only)",
    )

    workers: int = Field(
        default=1,
        ge=1,
        le=8,
        description="Number of worker processes",
    )

    # API configuration
    api_version: str = Field(
        default="v1",
        description="API version prefix",
    )

    api_title: str = Field(
        default="SkillMeat API",
        description="API title for OpenAPI documentation",
    )

    api_description: str = Field(
        default="REST API for SkillMeat collection manager",
        description="API description for OpenAPI documentation",
    )

    # CORS configuration
    cors_enabled: bool = Field(
        default=True,
        description="Enable CORS middleware",
    )

    cors_origins: List[str] = Field(
        default=[
            "http://localhost:3000",
            "http://localhost:3001",
            "http://localhost:5173",
            "http://localhost:8080",
        ],
        description="Allowed CORS origins",
    )

    cors_allow_credentials: bool = Field(
        default=True,
        description="Allow credentials in CORS requests",
    )

    cors_allow_methods: List[str] = Field(
        default=["*"],
        description="Allowed HTTP methods for CORS",
    )

    cors_allow_headers: List[str] = Field(
        default=["*"],
        description="Allowed headers for CORS",
    )

    # Logging configuration
    log_level: str = Field(
        default="INFO",
        description="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)",
    )

    log_format: str = Field(
        default="json",
        description="Log format (json or text)",
    )

    # Collection configuration
    collection_dir: Optional[Path] = Field(
        default=None,
        description="Override default collection directory (defaults to ~/.skillmeat/collections)",
    )

    # Security
    api_key_enabled: bool = Field(
        default=False,
        description="Enable API key authentication",
    )

    api_key: Optional[str] = Field(
        default=None,
        description="API key for authentication (if enabled)",
    )

    # Token authentication
    auth_enabled: bool = Field(
        default=False,
        description="Require bearer token authentication for API routes",
    )

    # Rate limiting
    rate_limit_enabled: bool = Field(
        default=False,
        description="Enable rate limiting",
    )

    rate_limit_requests: int = Field(
        default=100,
        ge=1,
        description="Maximum requests per minute",
    )

    # Discovery feature flags
    enable_auto_discovery: bool = Field(
        default=True,
        description="Enable artifact auto-discovery feature",
    )

    enable_auto_population: bool = Field(
        default=True,
        description="Enable automatic GitHub metadata population",
    )

    discovery_cache_ttl: int = Field(
        default=3600,
        ge=0,
        description="Cache TTL for discovery metadata in seconds (default: 1 hour)",
    )

    github_token: Optional[str] = Field(
        default=None,
        description="GitHub personal access token for higher API rate limits (5000/hr vs 60/hr)",
    )

    # Composite artifact feature flags
    composite_artifacts_enabled: bool = Field(
        default=True,
        description="Enable composite artifact detection during discovery. "
        "When disabled, discover_artifacts() always performs flat discovery "
        "and skips detect_composites(). "
        "Configurable via SKILLMEAT_COMPOSITE_ARTIFACTS_ENABLED env var.",
    )

    # Memory & Context Intelligence System feature flags
    memory_context_enabled: bool = Field(
        default=True,
        description="Enable Memory & Context Intelligence System (memory items, context modules, context packing)",
    )

    memory_auto_extract: bool = Field(
        default=False,
        description="Enable automatic memory extraction from conversations (Phase 5 feature)",
    )

    # Diff operation configuration
    diff_exclude_dirs: List[str] = Field(
        default=[
            ".git",
            "node_modules",
            "__pycache__",
            ".venv",
            "venv",
            ".tox",
            ".pytest_cache",
            ".mypy_cache",
            "dist",
            "build",
            ".next",
            ".turbo",
        ],
        description="Directories to exclude from artifact diff operations. "
        "Files inside these directories are skipped during collection/project/upstream diff comparisons. "
        "Add patterns like 'vendor' or '.cache' for your environment.",
    )

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level is a valid logging level."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        v_upper = v.upper()
        if v_upper not in valid_levels:
            raise ValueError(f"Invalid log level: {v}. Must be one of {valid_levels}")
        return v_upper

    @field_validator("log_format")
    @classmethod
    def validate_log_format(cls, v: str) -> str:
        """Validate log format is either json or text."""
        valid_formats = ["json", "text"]
        v_lower = v.lower()
        if v_lower not in valid_formats:
            raise ValueError(f"Invalid log format: {v}. Must be one of {valid_formats}")
        return v_lower

    @property
    def is_development(self) -> bool:
        """Check if running in development mode."""
        return self.env == Environment.DEVELOPMENT

    @property
    def is_production(self) -> bool:
        """Check if running in production mode."""
        return self.env == Environment.PRODUCTION

    @property
    def is_testing(self) -> bool:
        """Check if running in testing mode."""
        return self.env == Environment.TESTING

    @property
    def api_prefix(self) -> str:
        """Get API path prefix."""
        return f"/api/{self.api_version}"

    def configure_logging(self) -> None:
        """Configure application logging based on settings."""
        # Get numeric log level
        numeric_level = getattr(logging, self.log_level)

        if self.log_format == "json":
            # JSON structured logging
            import json
            import sys
            from datetime import datetime

            class JSONFormatter(logging.Formatter):
                """JSON log formatter."""

                def format(self, record: logging.LogRecord) -> str:
                    """Format log record as JSON."""
                    log_data = {
                        "timestamp": datetime.utcnow().isoformat(),
                        "level": record.levelname,
                        "logger": record.name,
                        "message": record.getMessage(),
                        "module": record.module,
                        "function": record.funcName,
                        "line": record.lineno,
                    }

                    # Add exception info if present
                    if record.exc_info:
                        log_data["exception"] = self.formatException(record.exc_info)

                    # Add extra fields
                    if hasattr(record, "extra"):
                        log_data.update(record.extra)

                    return json.dumps(log_data)

            handler = logging.StreamHandler(sys.stdout)
            handler.setFormatter(JSONFormatter())
        else:
            # Text logging with color support (development mode)
            format_string = (
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
                if not self.is_development
                else "%(levelname)s:     %(name)s - %(message)s"
            )
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter(format_string))

        # Configure root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(numeric_level)
        root_logger.handlers.clear()
        root_logger.addHandler(handler)

        # Configure uvicorn loggers
        for logger_name in ["uvicorn", "uvicorn.access", "uvicorn.error"]:
            logger = logging.getLogger(logger_name)
            logger.setLevel(numeric_level)
            logger.handlers.clear()
            logger.addHandler(handler)
            logger.propagate = False

    def get_collection_dir(self) -> Path:
        """Get the collection directory path.

        Returns:
            Path to collections directory
        """
        if self.collection_dir:
            return self.collection_dir

        # Use default from SkillMeat config
        return Path.home() / ".skillmeat" / "collections"


# Global settings instance
_settings: Optional[APISettings] = None


def get_settings() -> APISettings:
    """Get or create settings instance.

    This function provides a singleton pattern for settings,
    ensuring configuration is loaded only once.

    Returns:
        APISettings instance
    """
    global _settings
    if _settings is None:
        _settings = APISettings()
    return _settings


def reload_settings() -> APISettings:
    """Force reload settings from environment.

    Useful for testing or when environment changes at runtime.

    Returns:
        New APISettings instance
    """
    global _settings
    _settings = APISettings()
    return _settings
