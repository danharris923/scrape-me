"""
Unit tests for configuration system.
"""

import pytest
import os
import tempfile
from pathlib import Path

from config.settings import ScraperSettings, TestSettings, get_settings


class TestScraperSettings:
    """Test ScraperSettings configuration."""
    
    def test_default_settings(self):
        """Test default configuration values."""
        settings = ScraperSettings()
        
        assert settings.llm_provider == "anthropic"
        assert settings.llm_model == "claude-3-5-sonnet-latest"
        assert settings.scraping_delay_seconds == 2.0
        assert settings.max_retries == 3
        assert settings.quality_threshold == 0.7
        assert settings.browser_headless is False
        assert settings.debug_mode is False
        assert settings.test_mode is False
    
    def test_llm_model_string_generation(self):
        """Test LLM model string generation."""
        settings = ScraperSettings()
        model_string = settings.get_llm_model_string()
        
        assert model_string == "anthropic:claude-3-5-sonnet-latest"
    
    def test_browser_args_generation(self):
        """Test browser arguments for GCP VM."""
        settings = ScraperSettings(browser_headless=True)
        args = settings.get_browser_args()
        
        # Should contain basic args for headless mode
        expected_args = [
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--disable-background-timer-throttling",
            "--disable-backgrounding-occluded-windows",
            "--disable-renderer-backgrounding"
        ]
        
        for arg in expected_args:
            assert arg in args
    
    def test_browser_args_headful_mode(self):
        """Test browser arguments for headful mode."""
        settings = ScraperSettings(browser_headless=False)
        args = settings.get_browser_args()
        
        # Should contain additional args for headful mode
        headful_args = [
            "--disable-gpu",
            "--no-first-run",
            "--disable-default-apps"
        ]
        
        for arg in headful_args:
            assert arg in args
    
    def test_llm_provider_validation(self):
        """Test LLM provider validation."""
        # Valid provider
        settings = ScraperSettings(llm_provider="openai")
        assert settings.llm_provider == "openai"
        
        # Invalid provider should raise validation error
        with pytest.raises(ValueError, match="LLM provider must be one of"):
            ScraperSettings(llm_provider="invalid_provider")
    
    def test_delay_seconds_constraints(self):
        """Test scraping delay constraints."""
        # Valid delay
        settings = ScraperSettings(scraping_delay_seconds=1.0)
        assert settings.scraping_delay_seconds == 1.0
        
        # Below minimum should raise validation error
        with pytest.raises(ValueError):
            ScraperSettings(scraping_delay_seconds=0.1)
        
        # Above maximum should raise validation error  
        with pytest.raises(ValueError):
            ScraperSettings(scraping_delay_seconds=15.0)
    
    def test_quality_threshold_constraints(self):
        """Test quality threshold constraints."""
        # Valid threshold
        settings = ScraperSettings(quality_threshold=0.8)
        assert settings.quality_threshold == 0.8
        
        # Below minimum should raise validation error
        with pytest.raises(ValueError):
            ScraperSettings(quality_threshold=-0.1)
        
        # Above maximum should raise validation error
        with pytest.raises(ValueError):
            ScraperSettings(quality_threshold=1.5)
    
    def test_directory_creation(self):
        """Test that directories are created automatically."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_output_dir = os.path.join(temp_dir, "test_output")
            test_state_dir = os.path.join(temp_dir, "test_state")
            test_config_dir = os.path.join(temp_dir, "test_config")
            
            settings = ScraperSettings(
                output_directory=test_output_dir,
                state_directory=test_state_dir,
                config_directory=test_config_dir
            )
            
            # Directories should be created
            assert os.path.exists(test_output_dir)
            assert os.path.exists(test_state_dir)
            assert os.path.exists(test_config_dir)


class TestTestSettings:
    """Test TestSettings configuration."""
    
    def test_test_settings_defaults(self):
        """Test test-specific configuration defaults."""
        settings = TestSettings()
        
        assert settings.test_mode is True
        assert settings.browser_headless is True
        assert settings.scraping_delay_seconds == 0.1  # Faster for testing
        assert settings.max_retries == 1  # Fewer retries for testing
    
    def test_test_credentials_paths(self):
        """Test test credential paths."""
        settings = TestSettings()
        
        assert "test" in settings.gcs_credentials_path
        assert "test" in settings.gcs_bucket_name


class TestGetSettings:
    """Test get_settings function."""
    
    def test_get_production_settings(self):
        """Test getting production settings."""
        settings = get_settings(test_mode=False)
        
        assert isinstance(settings, ScraperSettings)
        assert not isinstance(settings, TestSettings)
        assert settings.test_mode is False
    
    def test_get_test_settings(self):
        """Test getting test settings."""
        settings = get_settings(test_mode=True)
        
        assert isinstance(settings, TestSettings)
        assert settings.test_mode is True
    
    def test_environment_variable_override(self):
        """Test environment variable override for test mode."""
        # Set environment variable
        original_value = os.environ.get("SCRAPER_TEST_MODE")
        os.environ["SCRAPER_TEST_MODE"] = "true"
        
        try:
            settings = get_settings(test_mode=False)  # Should be overridden
            assert isinstance(settings, TestSettings)
        finally:
            # Restore original environment
            if original_value is not None:
                os.environ["SCRAPER_TEST_MODE"] = original_value
            else:
                os.environ.pop("SCRAPER_TEST_MODE", None)


class TestEnvironmentVariables:
    """Test environment variable loading."""
    
    def test_env_prefix(self):
        """Test that environment variables use SCRAPER_ prefix."""
        # Set test environment variable
        original_value = os.environ.get("SCRAPER_LLM_PROVIDER")
        os.environ["SCRAPER_LLM_PROVIDER"] = "openai"
        
        try:
            settings = ScraperSettings()
            assert settings.llm_provider == "openai"
        finally:
            # Restore original environment
            if original_value is not None:
                os.environ["SCRAPER_LLM_PROVIDER"] = original_value
            else:
                os.environ.pop("SCRAPER_LLM_PROVIDER", None)
    
    def test_case_insensitive_env_vars(self):
        """Test that environment variables are case insensitive."""
        # Test with lowercase env var name
        original_value = os.environ.get("scraper_max_retries")
        os.environ["scraper_max_retries"] = "5"
        
        try:
            settings = ScraperSettings()
            assert settings.max_retries == 5
        finally:
            # Restore original environment
            if original_value is not None:
                os.environ["scraper_max_retries"] = original_value
            else:
                os.environ.pop("scraper_max_retries", None)