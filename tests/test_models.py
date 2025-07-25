"""
Unit tests for data models.
"""

import pytest
from datetime import datetime
from pydantic import ValidationError, HttpUrl

from agents.models import (
    ProductCard, ScrapedProduct, AffiliateNetwork, URLConfig, 
    SiteConfig, AgentDependencies, ScrapingResult, StateData
)


class TestProductCard:
    """Test ProductCard model."""
    
    def test_valid_product_card_creation(self):
        """Test creating a valid ProductCard."""
        product = ProductCard(
            title="Test Product",
            price="$19.99",
            affiliate_url="https://example.com/product/1",
            image_url="https://example.com/image.jpg",
            slug="test-product"
        )
        
        assert product.title == "Test Product"
        assert product.price == "$19.99"
        assert str(product.affiliate_url) == "https://example.com/product/1"
        assert str(product.image_url) == "https://example.com/image.jpg"
        assert product.slug == "test-product"
    
    def test_invalid_url_validation(self):
        """Test that invalid URLs are rejected."""
        with pytest.raises(ValidationError):
            ProductCard(
                title="Test Product",
                price="$19.99",
                affiliate_url="not-a-valid-url",
                image_url="https://example.com/image.jpg",
                slug="test-product"
            )


class TestScrapedProduct:
    """Test ScrapedProduct model."""
    
    def test_valid_scraped_product_creation(self):
        """Test creating a valid ScrapedProduct."""
        product = ScrapedProduct(
            title="Gaming Laptop",
            price="$999.99",
            affiliate_url="https://amazon.com/dp/B123456",
            original_image_url="https://m.media-amazon.com/image.jpg",
            category="electronics",
            platform=AffiliateNetwork.AMAZON,
            validation_score=0.85
        )
        
        assert product.title == "Gaming Laptop"
        assert product.platform == AffiliateNetwork.AMAZON
        assert product.validation_score == 0.85
        assert product.category == "electronics"
    
    def test_quality_score_calculation(self):
        """Test quality score calculation."""
        product = ScrapedProduct(
            title="High Quality Product with Great Specs",
            price="$299.99",
            affiliate_url="https://amazon.com/dp/B123456",
            original_image_url="https://m.media-amazon.com/images/product.jpg",
            category="electronics",
            platform=AffiliateNetwork.AMAZON,
            validation_score=0.0  # Will be recalculated
        )
        
        score = product.calculate_quality_score()
        assert isinstance(score, float)
        assert 0.0 <= score <= 1.0
        assert score > 0.5  # Should be decent quality with good data
    
    def test_slug_generation(self):
        """Test SEO slug generation."""
        product = ScrapedProduct(
            title="Gaming Laptop - High Performance!",
            price="$999.99",
            affiliate_url="https://amazon.com/dp/B123456",
            original_image_url="https://m.media-amazon.com/image.jpg",
            category="electronics",
            platform=AffiliateNetwork.AMAZON,
            validation_score=0.85
        )
        
        slug = product._generate_slug(product.title)
        assert slug == "gaming-laptop-high-performance"
        assert len(slug) <= 50
        assert "--" not in slug  # No double hyphens
    
    def test_to_product_card_conversion(self):
        """Test conversion to ProductCard."""
        scraped = ScrapedProduct(
            title="Test Product",
            price="$49.99",
            affiliate_url="https://example.com/product",
            original_image_url="https://example.com/image.jpg",
            category="test",
            platform=AffiliateNetwork.AMAZON,
            validation_score=0.8
        )
        
        card = scraped.to_product_card()
        
        assert isinstance(card, ProductCard)
        assert card.title == scraped.title
        assert card.price == scraped.price
        assert card.affiliate_url == scraped.affiliate_url
        assert card.image_url == scraped.original_image_url
        assert card.slug == "test-product"


class TestAffiliateNetwork:
    """Test AffiliateNetwork enum."""
    
    def test_enum_values(self):
        """Test enum has expected values."""
        assert AffiliateNetwork.AMAZON == "amazon"
        assert AffiliateNetwork.RAKUTEN == "rakuten"
        assert AffiliateNetwork.CJ == "cj"
    
    def test_enum_creation_from_string(self):
        """Test creating enum from string."""
        network = AffiliateNetwork("amazon")
        assert network == AffiliateNetwork.AMAZON


class TestURLConfig:
    """Test URLConfig model."""
    
    def test_valid_url_config(self):
        """Test creating valid URLConfig."""
        config = URLConfig(
            url="https://amazon.com/s?k=laptops",
            platform=AffiliateNetwork.AMAZON,
            category="electronics",
            expected_count=20
        )
        
        assert str(config.url) == "https://amazon.com/s?k=laptops"
        assert config.platform == AffiliateNetwork.AMAZON
        assert config.expected_count == 20
        assert config.custom_selectors is None
    
    def test_default_expected_count(self):
        """Test default expected count."""
        config = URLConfig(
            url="https://example.com",
            platform=AffiliateNetwork.AMAZON,
            category="test"
        )
        
        assert config.expected_count == 10  # Default value
    
    def test_expected_count_validation(self):
        """Test expected count validation."""
        with pytest.raises(ValidationError):
            URLConfig(
                url="https://example.com",
                platform=AffiliateNetwork.AMAZON,
                category="test",
                expected_count=0  # Below minimum
            )
        
        with pytest.raises(ValidationError):
            URLConfig(
                url="https://example.com",
                platform=AffiliateNetwork.AMAZON,
                category="test",
                expected_count=150  # Above maximum
            )


class TestAgentDependencies:
    """Test AgentDependencies model."""
    
    def test_valid_dependencies(self):
        """Test creating valid AgentDependencies."""
        deps = AgentDependencies(
            gcs_credentials_path="./test-creds.json",
            output_directory="./output",
            state_directory="./state",
            scraping_delay_seconds=1.5,
            max_retries=5,
            quality_threshold=0.8
        )
        
        assert deps.gcs_credentials_path == "./test-creds.json"
        assert deps.scraping_delay_seconds == 1.5
        assert deps.max_retries == 5
        assert deps.quality_threshold == 0.8
    
    def test_validation_constraints(self):
        """Test validation constraints."""
        # Test delay seconds constraints
        with pytest.raises(ValidationError):
            AgentDependencies(
                gcs_credentials_path="./test.json",
                scraping_delay_seconds=0.1  # Below minimum
            )
        
        # Test quality threshold constraints
        with pytest.raises(ValidationError):
            AgentDependencies(
                gcs_credentials_path="./test.json",
                quality_threshold=1.5  # Above maximum
            )


class TestScrapingResult:
    """Test ScrapingResult model."""
    
    def test_valid_result(self):
        """Test creating valid ScrapingResult."""
        result = ScrapingResult(
            site_name="test-site",
            total_products_found=50,
            valid_products=45,
            failed_products=5,
            processing_time_seconds=30.5,
            quality_score=0.85,
            output_file_path="./output/test-site.json"
        )
        
        assert result.site_name == "test-site"
        assert result.total_products_found == 50
        assert result.valid_products == 45
        assert result.failed_products == 5
    
    def test_success_rate_calculation(self):
        """Test success rate property."""
        result = ScrapingResult(
            site_name="test",
            total_products_found=100,
            valid_products=80,
            failed_products=20,
            processing_time_seconds=60.0,
            quality_score=0.8,
            output_file_path="./output/test.json"
        )
        
        assert result.success_rate == 0.8  # 80/100
    
    def test_zero_products_success_rate(self):
        """Test success rate when no products found."""
        result = ScrapingResult(
            site_name="test",
            total_products_found=0,
            valid_products=0,
            failed_products=0,
            processing_time_seconds=5.0,
            quality_score=0.0,
            output_file_path="./output/test.json"
        )
        
        assert result.success_rate == 0.0


class TestStateData:
    """Test StateData model."""
    
    def test_valid_state_data(self):
        """Test creating valid StateData."""
        products = [
            ProductCard(
                title="Test Product",
                price="$29.99",
                affiliate_url="https://example.com/product",
                image_url="https://example.com/image.jpg",
                slug="test-product"
            )
        ]
        
        result = ScrapingResult(
            site_name="test-site",
            total_products_found=1,
            valid_products=1,
            failed_products=0,
            processing_time_seconds=10.0,
            quality_score=0.9,
            output_file_path="./output/test.json"
        )
        
        state = StateData(
            site_name="test-site",
            last_successful_scrape=datetime.now(),
            last_products=products,
            last_result=result,
            consecutive_failures=0
        )
        
        assert state.site_name == "test-site"
        assert len(state.last_products) == 1
        assert state.consecutive_failures == 0
    
    def test_should_use_cached_data(self):
        """Test cached data decision logic."""
        state = StateData(
            site_name="test",
            last_successful_scrape=datetime.now(),
            last_products=[],
            last_result=ScrapingResult(
                site_name="test",
                total_products_found=0,
                valid_products=0,
                failed_products=0,
                processing_time_seconds=0.0,
                quality_score=0.0,
                output_file_path="./test.json"
            ),
            consecutive_failures=5  # Above threshold
        )
        
        # Should use cached data when failures >= max_failures
        assert state.should_use_cached_data(max_failures=3) is True
        assert state.should_use_cached_data(max_failures=10) is False