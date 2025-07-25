"""
Environment configuration and settings management for the affiliate scraper.

This module uses Pydantic Settings to load and validate environment variables
with sensible defaults for development and production environments.
"""

from pydantic import Field, validator
from pydantic_settings import BaseSettings
from typing import Optional
import os
from pathlib import Path


class ScraperSettings(BaseSettings):
    """Main configuration class for the affiliate scraper system."""
    
    # LLM Configuration
    llm_provider: str = Field(default="anthropic", description="LLM provider (anthropic, openai, openrouter)")
    llm_model: str = Field(default="claude-3-5-sonnet-latest", description="LLM model name")
    llm_api_key: str = Field(default="", description="API key for LLM provider")
    
    # Google Cloud Storage Configuration
    gcs_credentials_path: str = Field(default="", description="Path to GCS service account JSON")
    gcs_bucket_name: str = Field(default="", description="Default GCS bucket for image uploads")
    
    # Scraping Configuration
    scraping_delay_seconds: float = Field(default=2.0, ge=0.5, le=10.0)
    max_retries: int = Field(default=3, ge=1, le=10)
    quality_threshold: float = Field(default=0.7, ge=0.0, le=1.0)
    browser_headless: bool = Field(default=False, description="Run browser in headless mode")
    
    # File System Configuration
    output_directory: str = Field(default="./output")
    state_directory: str = Field(default="./state")
    config_directory: str = Field(default="./config/sites")
    
    # Logging Configuration
    log_level: str = Field(default="INFO", description="Logging level")
    log_file: Optional[str] = Field(default=None, description="Log file path")
    
    # Development Configuration
    debug_mode: bool = Field(default=False, description="Enable debug mode")
    test_mode: bool = Field(default=False, description="Enable test mode with mocked requests")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        env_prefix = "SCRAPER_"
    
    @validator("gcs_credentials_path")
    def validate_gcs_credentials(cls, v):
        """Validate that GCS credentials file exists."""
        if v and not os.path.exists(v):
            raise ValueError(f"GCS credentials file not found at: {v}")
        return v
    
    @validator("llm_provider")
    def validate_llm_provider(cls, v):
        """Validate LLM provider is supported."""
        supported_providers = ["anthropic", "openai", "google", "openrouter"]
        if v not in supported_providers:
            raise ValueError(f"LLM provider must be one of: {supported_providers}")
        return v
    
    @validator("output_directory", "state_directory", "config_directory")
    def create_directories(cls, v):
        """Ensure directories exist, create if they don't."""
        Path(v).mkdir(parents=True, exist_ok=True)
        return v
    
    def get_llm_model_string(self) -> str:
        """Get the full LLM model string for Pydantic AI."""
        return f"{self.llm_provider}:{self.llm_model}"
    
    def get_browser_args(self) -> list[str]:
        """Get browser launch arguments for GCP VM."""
        args = [
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--disable-background-timer-throttling",
            "--disable-backgrounding-occluded-windows",
            "--disable-renderer-backgrounding"
        ]
        
        if not self.browser_headless:
            # Additional args for headful mode on VM
            args.extend([
                "--disable-gpu",
                "--no-first-run",
                "--disable-default-apps"
            ])
        
        return args


class TestSettings(ScraperSettings):
    """Test-specific configuration that overrides production settings."""
    
    test_mode: bool = Field(default=True)
    browser_headless: bool = Field(default=True)
    scraping_delay_seconds: float = Field(default=0.1)  # Fast for testing
    max_retries: int = Field(default=1)  # Fewer retries in tests
    
    # Use test credentials and buckets
    gcs_credentials_path: str = Field(default="./tests/fixtures/test_credentials.json")
    gcs_bucket_name: str = Field(default="test-scraper-bucket")
    
    class Config:
        env_file = ".env.test"
        env_file_encoding = "utf-8"


def get_settings(test_mode: bool = False) -> ScraperSettings:
    """
    Get the appropriate settings instance.
    
    Args:
        test_mode: Whether to use test settings
        
    Returns:
        ScraperSettings instance
    """
    if test_mode or os.getenv("SCRAPER_TEST_MODE", "").lower() == "true":
        return TestSettings()
    return ScraperSettings()


# Global settings instance
settings = get_settings()


def reload_settings(test_mode: bool = False) -> ScraperSettings:
    """
    Reload settings from environment variables.
    
    Args:
        test_mode: Whether to use test settings
        
    Returns:
        Fresh ScraperSettings instance
    """
    global settings
    settings = get_settings(test_mode)
    return settings