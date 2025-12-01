"""
Configuration management using pydantic-settings.
Loads configuration from environment variables and .env file.
"""

import os
from pathlib import Path
from typing import List, Optional
from functools import cached_property
from pydantic import field_validator, model_validator, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Application version
VERSION = "2.0.0"


class Settings(BaseSettings):
    """Application settings loaded from environment variables and .env file.
    
    Provides validated configuration with automatic type conversion,
    computed properties, and directory management.
    """
    
    # Application
    app_name: str = Field(
        default="AppImage Re-Signer",
        description="Application name"
    )
    version: str = Field(
        default=VERSION,
        description="Application version"
    )
    
    # Server Configuration
    host: str = Field(
        default="127.0.0.1",
        description="Server host address"
    )
    port: int = Field(
        default=8000,
        ge=1,
        le=65535,
        description="Server port number"
    )
    debug: bool = Field(
        default=False,
        description="Enable debug mode"
    )
    
    # Security
    secret_key: str = Field(
        default="dev-secret-key-change-in-production",
        min_length=32,
        description="Secret key for session management"
    )
    cors_origins: str = Field(
        default="*",
        description="Comma-separated list of allowed CORS origins"
    )
    
    # File Upload Limits
    max_file_size_mb: int = Field(
        default=500,
        ge=1,
        le=5000,
        description="Maximum file size in MB"
    )
    cleanup_after_hours: int = Field(
        default=24,
        ge=1,
        le=168,
        description="Hours before session cleanup (max 1 week)"
    )
    
    # Logging
    log_level: str = Field(
        default="INFO",
        description="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)"
    )
    log_to_file: bool = Field(
        default=True,
        description="Enable file logging"
    )
    log_to_console: bool = Field(
        default=True,
        description="Enable console logging"
    )
    log_file_path: Path = Field(
        default=Path("logs/appimage-resigner.log"),
        description="Log file path"
    )
    
    # GPG Configuration
    gpg_binary_path: Optional[str] = Field(
        default=None,
        description="Path to GPG binary (auto-detected if None)"
    )
    
    # Directories
    upload_dir: Path = Field(
        default=Path("uploads"),
        description="Directory for uploaded files"
    )
    signed_dir: Path = Field(
        default=Path("signed"),
        description="Directory for signed files"
    )
    temp_keys_dir: Path = Field(
        default=Path("temp_keys"),
        description="Directory for temporary GPG keys"
    )
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        validate_default=True,
        frozen=False  # Allow create_directories to work
    )
    
    @field_validator('log_level')
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level is one of the allowed values."""
        allowed = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        v_upper = v.upper()
        if v_upper not in allowed:
            raise ValueError(f'log_level must be one of {allowed}')
        return v_upper
    
    @field_validator('secret_key')
    @classmethod
    def validate_secret_key(cls, v: str) -> str:
        """Warn if using default secret key in production."""
        if v == "dev-secret-key-change-in-production":
            import warnings
            warnings.warn(
                "Using default secret key! Change SECRET_KEY in production!",
                UserWarning
            )
        return v
    
    @field_validator('upload_dir', 'signed_dir', 'temp_keys_dir', 'log_file_path')
    @classmethod
    def validate_path(cls, v: Path) -> Path:
        """Convert string paths to Path objects and validate."""
        if isinstance(v, str):
            v = Path(v)
        # Ensure absolute paths
        if not v.is_absolute():
            v = Path.cwd() / v
        return v
    
    @model_validator(mode='after')
    def create_directories_validator(self) -> 'Settings':
        """Create required directories after validation."""
        self.create_directories()
        return self
    
    @cached_property
    def cors_origins_list(self) -> List[str]:
        """Parse CORS origins from comma-separated string.
        
        Returns:
            List of allowed CORS origins. Returns ["*"] for wildcard.
        """
        if self.cors_origins == "*":
            return ["*"]
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]
    
    @cached_property
    def max_file_size_bytes(self) -> int:
        """Convert MB to bytes.
        
        Returns:
            Maximum file size in bytes.
        """
        return self.max_file_size_mb * 1024 * 1024
    
    def create_directories(self) -> None:
        """Create required directories if they don't exist.
        
        Creates:
            - upload_dir: For uploaded AppImage files
            - signed_dir: For signed AppImage files
            - temp_keys_dir: For temporary GPG keys
            - log directory: For log files
        """
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.signed_dir.mkdir(parents=True, exist_ok=True)
        self.temp_keys_dir.mkdir(parents=True, exist_ok=True)
        
        # Create log directory
        if self.log_to_file:
            self.log_file_path.parent.mkdir(parents=True, exist_ok=True)
    
    def get_summary(self) -> dict:
        """Get configuration summary for health checks.
        
        Returns:
            Dictionary with non-sensitive configuration values.
        """
        return {
            "app_name": self.app_name,
            "version": self.version,
            "host": self.host,
            "port": self.port,
            "debug": self.debug,
            "max_file_size_mb": self.max_file_size_mb,
            "cleanup_after_hours": self.cleanup_after_hours,
            "log_level": self.log_level,
            "cors_origins": self.cors_origins_list,
            "directories": {
                "upload": str(self.upload_dir),
                "signed": str(self.signed_dir),
                "temp_keys": str(self.temp_keys_dir)
            }
        }


# Global settings instance
settings = Settings()
