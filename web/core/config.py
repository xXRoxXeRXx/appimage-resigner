"""
Configuration management using pydantic-settings.
Loads configuration from environment variables and .env file.
"""

import os
from pathlib import Path
from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Server Configuration
    host: str = "127.0.0.1"
    port: int = 8000
    debug: bool = False
    
    # Security
    secret_key: str = "dev-secret-key-change-in-production"
    cors_origins: str = "*"  # Comma-separated list
    
    # File Upload Limits
    max_file_size_mb: int = 500
    cleanup_after_hours: int = 24
    
    # Logging
    log_level: str = "INFO"
    log_to_file: bool = True
    log_to_console: bool = True
    
    # GPG Configuration
    gpg_binary_path: Optional[str] = None
    
    # Directories
    upload_dir: Path = Path("uploads")
    signed_dir: Path = Path("signed")
    temp_keys_dir: Path = Path("temp_keys")
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    @property
    def cors_origins_list(self) -> List[str]:
        """Parse CORS origins from comma-separated string."""
        if self.cors_origins == "*":
            return ["*"]
        return [origin.strip() for origin in self.cors_origins.split(",")]
    
    @property
    def max_file_size_bytes(self) -> int:
        """Convert MB to bytes."""
        return self.max_file_size_mb * 1024 * 1024
    
    def create_directories(self) -> None:
        """Create required directories if they don't exist."""
        self.upload_dir.mkdir(exist_ok=True)
        self.signed_dir.mkdir(exist_ok=True)
        self.temp_keys_dir.mkdir(exist_ok=True)


# Global settings instance
settings = Settings()
