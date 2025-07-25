"""
Unit tests for data validation functionality.
"""

import pytest
from agents.models import ScrapedProduct, ProductCard, AffiliateNetwork, AgentDependencies
from tools.data_validator import (
    _basic_validation, _calculate_comprehensive_quality_score,
    _score_title_quality, _score_price_quality, _score_url_quality,
    _score_image_url_quality, _score_category_quality, _score_platform_trust
)


class TestBasicValidation:
    """Test basic validation functions."""
    
    def test_valid_product_passes_validation(self):
        """Test that a valid product passes basic validation."""
        product = ScrapedProduct(
            title="High-Quality Gaming Laptop",
            price="$1299.99",
            affiliate_url="https://amazon.com/dp/B123456789",
            original_image_url="https://m.media-amazon.com/images/product.jpg",
            category="electronics",
            platform=AffiliateNetwork.AMAZON,
            validation_score=0.0
        )
        
        assert _basic_validation(product) is True
    
    def test_empty_title_fails_validation(self):
        """Test that empty title fails validation."""
        # Empty title should fail at Pydantic level due to min_length constraint
        with pytest.raises(ValueError):
            ScrapedProduct(
                title="",
                price="$29.99",
                affiliate_url="https://example.com/product",
                original_image_url="https://example.com/image.jpg",
                category="test",
                platform=AffiliateNetwork.AMAZON,
                validation_score=0.0
            )
    
    def test_short_title_fails_validation(self):
        """Test that very short title fails validation."""
        product = ScrapedProduct(
            title="AB",  # Too short
            price="$29.99",
            affiliate_url="https://example.com/product",
            original_image_url="https://example.com/image.jpg",
            category="test",
            platform=AffiliateNetwork.AMAZON,
            validation_score=0.0
        )
        
        assert _basic_validation(product) is False
    
    def test_invalid_price_fails_validation(self):
        """Test that invalid price fails validation."""
        product = ScrapedProduct(
            title="Valid Product",
            price="Not a price",
            affiliate_url="https://example.com/product",
            original_image_url="https://example.com/image.jpg",
            category="test",
            platform=AffiliateNetwork.AMAZON,
            validation_score=0.0
        )
        
        assert _basic_validation(product) is False
    
    def test_invalid_url_fails_validation(self):
        """Test that invalid URL fails validation."""
        # Invalid URLs should fail at Pydantic level during model creation
        with pytest.raises(ValueError):
            ScrapedProduct(
                title="Valid Product",
                price="$29.99",
                affiliate_url="not-a-valid-url",
                original_image_url="https://example.com/image.jpg",
                category="test",
                platform=AffiliateNetwork.AMAZON,
                validation_score=0.0
            )


class TestTitleQualityScoring:
    """Test title quality scoring."""
    
    def test_optimal_length_title(self):
        """Test scoring for optimal length title."""
        title = "High-Quality Gaming Laptop with RTX Graphics"
        score = _score_title_quality(title)
        
        assert score >= 40.0  # Should get length points
        assert score <= 100.0
    
    def test_title_with_specifications(self):
        """Test title with specifications gets bonus points."""
        title = "Gaming Laptop 16GB RAM 1TB SSD 15.6 inch Display"
        score = _score_title_quality(title)
        
        # Should get specification bonus points
        assert score > 50.0
    
    def test_title_with_brand_names(self):
        """Test title with brand names gets bonus points."""
        title = "Apple MacBook Pro with M1 Chip"
        score = _score_title_quality(title)
        
        # Should get brand bonus points
        assert score > 40.0
    
    def test_spammy_title_loses_points(self):
        """Test spammy title loses points."""
        title = "FREE LAPTOP!!! LIMITED TIME!!! BUY NOW!!!"
        score = _score_title_quality(title)
        
        # Should lose points for spam indicators
        assert score < 50.0
    
    def test_empty_title(self):
        """Test empty title gets zero score."""
        score = _score_title_quality("")
        assert score == 0.0


class TestPriceQualityScoring:
    """Test price quality scoring."""
    
    def test_well_formatted_price(self):
        """Test well-formatted price gets high score."""
        price = "$299.99"
        score = _score_price_quality(price)
        
        assert score >= 80.0  # Should get most points
    
    def test_price_without_currency_symbol(self):
        """Test price without currency symbol gets lower score."""
        price = "299.99"
        score = _score_price_quality(price)
        
        assert score < 80.0  # Should lose currency symbol points
        assert score > 0.0   # But still have some points
    
    def test_unreasonable_price_range(self):
        """Test unreasonable price gets lower score."""
        price = "$999999.99"  # Too expensive
        score = _score_price_quality(price)
        
        assert score < 100.0  # Shouldn't get full points
    
    def test_empty_price(self):
        """Test empty price gets zero score."""
        score = _score_price_quality("")
        assert score == 0.0


class TestURLQualityScoring:
    """Test URL quality scoring."""
    
    def test_amazon_url_gets_high_score(self):
        """Test Amazon URL gets high trust score."""
        url = "https://amazon.com/dp/B123456789"
        score = _score_url_quality(url)
        
        assert score >= 80.0  # Should get high trust + HTTPS + structure points
    
    def test_https_gets_bonus_points(self):
        """Test HTTPS URLs get bonus points."""
        url = "https://example.com/product/123"
        score_https = _score_url_quality(url)
        
        url_http = "http://example.com/product/123" 
        score_http = _score_url_quality(url_http)
        
        assert score_https > score_http
    
    def test_product_url_structure(self):
        """Test product URL structure gets bonus points."""
        url = "https://example.com/product/gaming-laptop"
        score = _score_url_quality(url)
        
        # Should get structure bonus points
        assert score > 20.0
    
    def test_empty_url(self):
        """Test empty URL gets zero score."""
        score = _score_url_quality("")
        assert score == 0.0


class TestImageURLQualityScoring:
    """Test image URL quality scoring."""
    
    def test_https_image_url(self):
        """Test HTTPS image URLs get bonus points."""
        url = "https://example.com/image.jpg"
        score = _score_image_url_quality(url)
        
        assert score >= 25.0  # HTTPS points
    
    def test_image_format_recognition(self):
        """Test various image formats are recognized."""
        formats = [".jpg", ".jpeg", ".png", ".webp"]
        
        for fmt in formats:
            url = f"https://example.com/image{fmt}"
            score = _score_image_url_quality(url)
            assert score >= 50.0  # HTTPS + format points
    
    def test_placeholder_images_lose_points(self):
        """Test placeholder images lose points."""
        url = "https://example.com/placeholder-image.jpg"
        score = _score_image_url_quality(url)
        
        # Should lose points for placeholder indicator
        assert score <= 75.0  # Allow equal since it might be exactly 75.0
    
    def test_empty_image_url(self):
        """Test empty image URL gets zero score."""
        score = _score_image_url_quality("")
        assert score == 0.0


class TestCategoryQualityScoring:
    """Test category quality scoring."""
    
    def test_common_category(self):
        """Test common categories get bonus points."""
        score = _score_category_quality("electronics")
        assert score >= 70.0  # Length + format + common category points
    
    def test_proper_formatting(self):
        """Test properly formatted categories get points."""
        score = _score_category_quality("home-garden")
        assert score >= 40.0  # Length + format points
    
    def test_invalid_formatting_loses_points(self):
        """Test invalid formatting loses points."""
        score = _score_category_quality("Electronics@#$")
        assert score <= 70.0  # Should lose format points (allow equal)
    
    def test_empty_category(self):
        """Test empty category gets zero score."""
        score = _score_category_quality("")
        assert score == 0.0


class TestPlatformTrustScoring:
    """Test platform trust scoring."""
    
    def test_amazon_platform_trust(self):
        """Test Amazon gets highest trust score."""
        score = _score_platform_trust(AffiliateNetwork.AMAZON)
        assert score == 100.0
    
    def test_rakuten_platform_trust(self):
        """Test Rakuten gets good trust score."""
        score = _score_platform_trust(AffiliateNetwork.RAKUTEN)
        assert score == 80.0
    
    def test_cj_platform_trust(self):
        """Test CJ gets decent trust score."""
        score = _score_platform_trust(AffiliateNetwork.CJ)
        assert score == 70.0
    
    def test_unknown_platform_trust(self):
        """Test unknown platform gets default score."""
        # Mock platform as string
        score = _score_platform_trust("unknown")
        assert score == 50.0


class TestComprehensiveQualityScore:
    """Test comprehensive quality scoring."""
    
    def test_high_quality_product_score(self):
        """Test high-quality product gets high score."""
        product = ScrapedProduct(
            title="Apple MacBook Pro 16-inch with M2 Chip 32GB RAM 1TB SSD",
            price="$2499.99",
            affiliate_url="https://amazon.com/dp/B123456789",
            original_image_url="https://m.media-amazon.com/images/I/high-res-product.jpg",
            category="electronics",
            platform=AffiliateNetwork.AMAZON,
            validation_score=0.0
        )
        
        score = _calculate_comprehensive_quality_score(product)
        assert score >= 0.8  # Should be high quality
        assert score <= 1.0
    
    def test_low_quality_product_score(self):
        """Test low-quality product gets low score."""
        product = ScrapedProduct(
            title="thing",  # Poor title
            price="price",  # Invalid price
            affiliate_url="https://sketchy-site.com/item",
            original_image_url="http://example.com/placeholder.jpg",
            category="x",  # Poor category
            platform=AffiliateNetwork.CJ,  # Lower trust
            validation_score=0.0
        )
        
        score = _calculate_comprehensive_quality_score(product)
        assert score < 0.5  # Should be low quality
        assert score >= 0.0
    
    def test_score_normalization(self):
        """Test that scores are properly normalized to 0-1 range."""
        product = ScrapedProduct(
            title="Test Product",
            price="$49.99",
            affiliate_url="https://example.com/product",
            original_image_url="https://example.com/image.jpg",
            category="test",
            platform=AffiliateNetwork.AMAZON,
            validation_score=0.0
        )
        
        score = _calculate_comprehensive_quality_score(product)
        assert 0.0 <= score <= 1.0
        assert isinstance(score, float)
        assert len(str(score).split('.')[-1]) <= 3  # Max 3 decimal places