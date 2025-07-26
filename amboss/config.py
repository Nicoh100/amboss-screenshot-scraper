"""Configuration management for AMBOSS scraper."""

import os
from pathlib import Path
from typing import Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    # Authentication
    cookie_path: Path = Field(
        default=Path("secrets/auth_state.json"),
        description="Path to Playwright cookie state file"
    )
    
    # Browser settings
    viewport_width: int = Field(default=1280, description="Browser viewport width")
    viewport_height: int = Field(default=720, description="Browser viewport height")
    device_scale_factor: float = Field(default=2.0, description="Device scale factor for retina screenshots")
    
    # Rate limiting
    requests_per_minute: int = Field(default=30, description="Maximum requests per minute")
    min_delay: float = Field(default=2.0, description="Minimum delay between requests (seconds)")
    max_delay: float = Field(default=4.0, description="Maximum delay between requests (seconds)")
    
    # Screenshot settings
    output_dir: Path = Field(default=Path("captures"), description="Output directory for screenshots")
    screenshot_format: str = Field(default="png", description="Screenshot format")
    screenshot_quality: int = Field(default=100, description="Screenshot quality (1-100)")
    
    # Validation settings
    min_ocr_density: float = Field(default=0.95, description="Minimum OCR text density threshold")
    ocr_stddev_threshold: int = Field(default=20, description="OCR standard deviation threshold")
    
    # Database
    database_path: Path = Field(default=Path("amboss_scraper.db"), description="SQLite database path")
    
    # S3 settings (optional)
    s3_bucket: Optional[str] = Field(default=None, description="S3 bucket for uploads")
    s3_prefix: str = Field(default="screenshots", description="S3 key prefix")
    aws_access_key_id: Optional[str] = Field(default=None, description="AWS access key ID")
    aws_secret_access_key: Optional[str] = Field(default=None, description="AWS secret access key")
    aws_region: str = Field(default="us-east-1", description="AWS region")
    
    # Logging
    log_level: str = Field(default="INFO", description="Logging level")
    log_format: str = Field(default="json", description="Log format (json or text)")
    
    # AMBOSS URLs
    base_url: str = Field(default="https://next.amboss.com", description="AMBOSS base URL")
    article_pattern: str = Field(
        default=r"https://next\.amboss\.com/de/(?:article|knowledge)/([a-z0-9-]+)",
        description="Regex pattern for article URLs"
    )
    
    # Expansion settings
    max_expansion_attempts: int = Field(default=4, description="Maximum expansion attempts")
    expansion_delay: int = Field(default=400, description="Delay between expansion clicks (ms)")
    
    @field_validator("cookie_path")
    @classmethod
    def validate_cookie_path(cls, v: Path) -> Path:
        """Validate cookie path exists."""
        if not v.exists():
            raise ValueError(f"Cookie file not found: {v}")
        return v
    
    @field_validator("output_dir")
    @classmethod
    def create_output_dir(cls, v: Path) -> Path:
        """Create output directory if it doesn't exist."""
        v.mkdir(parents=True, exist_ok=True)
        return v
    
    @field_validator("database_path")
    @classmethod
    def create_db_dir(cls, v: Path) -> Path:
        """Create database directory if it doesn't exist."""
        v.parent.mkdir(parents=True, exist_ok=True)
        return v
    
    class Config:
        env_prefix = "AMBOSS_"
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings() 