"""
Abstract base class for platform-specific scrapers.

This module defines the interface that all affiliate platform scrapers must implement,
ensuring consistent behavior across Amazon, Rakuten, CJ, and future platforms.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from playwright.async_api import Page
from agents.models import ScrapedProduct, AffiliateNetwork
from pydantic import HttpUrl
import logging

logger = logging.getLogger(__name__)


class PlatformScraperError(Exception):
    """Base exception for platform scraper errors."""
    pass


class ProductExtractionError(PlatformScraperError):
    """Raised when product extraction fails."""
    pass


class BasePlatformScraper(ABC):
    """
    Abstract base class for platform-specific product scrapers.
    
    Each platform (Amazon, Rakuten, CJ) implements this interface to provide
    platform-specific scraping logic while maintaining consistent behavior.
    """
    
    def __init__(self, platform: AffiliateNetwork):
        """
        Initialize the platform scraper.
        
        Args:
            platform: The affiliate network this scraper handles
        """
        self.platform = platform
        self.logger = logging.getLogger(f"{__name__}.{platform.value}")
    
    @property
    @abstractmethod
    def platform_name(self) -> str:
        """Return the human-readable platform name."""
        pass
    
    @property
    @abstractmethod
    def default_selectors(self) -> Dict[str, str]:
        """
        Return default CSS selectors for this platform.
        
        Returns:
            Dict with keys: product_container, title, price, image, link
        """
        pass
    
    @abstractmethod
    async def extract_products(
        self, 
        page: Page, 
        expected_count: int = 10,
        custom_selectors: Optional[Dict[str, str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Extract product data from the page.
        
        Args:
            page: Playwright page object
            expected_count: Expected number of products to extract
            custom_selectors: Optional custom selectors to override defaults
            
        Returns:
            List of raw product data dictionaries
            
        Raises:
            ProductExtractionError: If extraction fails
        """
        pass
    
    @abstractmethod
    def validate_product_data(self, product_data: Dict[str, Any]) -> bool:
        """
        Validate that product data is complete and valid for this platform.
        
        Args:
            product_data: Raw product data dictionary
            
        Returns:
            True if valid, False otherwise
        """
        pass
    
    @abstractmethod
    def clean_price(self, price_text: str) -> str:
        """
        Clean and normalize price text for this platform.
        
        Args:
            price_text: Raw price text from the page
            
        Returns:
            Cleaned price string
        """
        pass
    
    @abstractmethod
    def build_affiliate_url(self, original_url: str) -> str:
        """
        Build the affiliate URL from the original product URL.
        
        Args:
            original_url: Original product URL
            
        Returns:
            Affiliate URL with tracking parameters
        """
        pass
    
    def get_selectors(self, custom_selectors: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        """
        Get selectors, preferring custom over defaults.
        
        Args:
            custom_selectors: Optional custom selectors
            
        Returns:
            Combined selector dictionary
        """
        selectors = self.default_selectors.copy()
        if custom_selectors:
            selectors.update(custom_selectors)
        return selectors
    
    async def safe_extract_text(self, page: Page, selector: str, default: str = "") -> str:
        """
        Safely extract text from an element, returning default if not found.
        
        Args:
            page: Playwright page object
            selector: CSS selector
            default: Default value if element not found
            
        Returns:
            Extracted text or default
        """
        try:
            element = await page.query_selector(selector)
            if element:
                text = await element.text_content()
                return text.strip() if text else default
            return default
        except Exception as e:
            self.logger.warning(f"Failed to extract text with selector '{selector}': {e}")
            return default
    
    async def safe_extract_attribute(
        self, 
        page: Page, 
        selector: str, 
        attribute: str, 
        default: str = ""
    ) -> str:
        """
        Safely extract an attribute from an element.
        
        Args:
            page: Playwright page object
            selector: CSS selector
            attribute: Attribute name (e.g., 'href', 'src')
            default: Default value if element or attribute not found
            
        Returns:
            Extracted attribute value or default
        """
        try:
            element = await page.query_selector(selector)
            if element:
                attr_value = await element.get_attribute(attribute)
                return attr_value.strip() if attr_value else default
            return default
        except Exception as e:
            self.logger.warning(f"Failed to extract attribute '{attribute}' with selector '{selector}': {e}")
            return default
    
    async def wait_for_products_to_load(self, page: Page, timeout: float = 10.0) -> None:
        """
        Wait for products to load on the page.
        
        Args:
            page: Playwright page object
            timeout: Maximum time to wait in seconds
        """
        try:
            # Wait for product containers to be visible
            await page.wait_for_selector(
                self.default_selectors["product_container"], 
                state="visible",
                timeout=timeout * 1000
            )
            
            # Additional wait for dynamic content
            await page.wait_for_load_state("networkidle", timeout=timeout * 1000)
            
        except Exception as e:
            self.logger.warning(f"Timeout waiting for products to load: {e}")
            # Continue anyway, might still be able to extract some products
    
    def calculate_extraction_score(
        self, 
        extracted_count: int, 
        expected_count: int,
        valid_count: int
    ) -> float:
        """
        Calculate quality score for the extraction process.
        
        Args:
            extracted_count: Number of products extracted
            expected_count: Expected number of products
            valid_count: Number of valid products after validation
            
        Returns:
            Quality score between 0.0 and 1.0
        """
        if extracted_count == 0:
            return 0.0
        
        # Base score on extraction success rate
        extraction_rate = min(extracted_count / expected_count, 1.0)
        
        # Validation success rate
        validation_rate = valid_count / extracted_count if extracted_count > 0 else 0.0
        
        # Combined score (weighted)
        score = (extraction_rate * 0.4) + (validation_rate * 0.6)
        
        return round(score, 2)
    
    async def extract_and_validate_products(
        self,
        page: Page,
        expected_count: int = 10,
        custom_selectors: Optional[Dict[str, str]] = None,
        category: str = "general"
    ) -> List[ScrapedProduct]:
        """
        Extract products and convert to validated ScrapedProduct objects.
        
        Args:
            page: Playwright page object
            expected_count: Expected number of products
            custom_selectors: Optional custom selectors
            category: Product category
            
        Returns:
            List of validated ScrapedProduct objects
        """
        # Extract raw product data
        raw_products = await self.extract_products(page, expected_count, custom_selectors)
        
        validated_products = []
        for product_data in raw_products:
            try:
                # Validate raw data
                if not self.validate_product_data(product_data):
                    self.logger.warning(f"Invalid product data: {product_data}")
                    continue
                
                # Create ScrapedProduct
                scraped_product = ScrapedProduct(
                    title=product_data["title"],
                    price=self.clean_price(product_data["price"]),
                    affiliate_url=HttpUrl(self.build_affiliate_url(product_data["link"])),
                    original_image_url=product_data["image"],
                    category=category,
                    platform=self.platform,
                    validation_score=0.0  # Will be calculated
                )
                
                # Calculate and set quality score
                scraped_product.validation_score = scraped_product.calculate_quality_score()
                
                validated_products.append(scraped_product)
                
            except Exception as e:
                self.logger.error(f"Failed to create ScrapedProduct: {e}")
                continue
        
        self.logger.info(
            f"Extracted {len(validated_products)} valid products out of "
            f"{len(raw_products)} raw products from {self.platform_name}"
        )
        
        return validated_products