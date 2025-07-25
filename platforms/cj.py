"""
Commission Junction (CJ) specific scraper implementation.

This module implements the CJ affiliate network scraper for various merchant sites
that participate in the CJ affiliate program.
"""

from typing import List, Dict, Any, Optional
from playwright.async_api import Page
import re
import asyncio
import random
from urllib.parse import urlparse

from .base import BasePlatformScraper, ProductExtractionError
from agents.models import AffiliateNetwork


class CJScraper(BasePlatformScraper):
    """
    Commission Junction (CJ) affiliate network scraper.
    
    Handles various merchant sites under the CJ network with generic
    selectors that work across multiple CJ merchants.
    """
    
    def __init__(self):
        super().__init__(AffiliateNetwork.CJ)
        self.affiliate_id = "your_cj_affiliate_id"  # Should be configurable
        
    @property
    def platform_name(self) -> str:
        return "Commission Junction"
    
    @property
    def default_selectors(self) -> Dict[str, str]:
        """Default selectors for CJ merchant sites."""
        return {
            "product_container": ".product, .item, .deal-item, .product-item",
            "title": ".product-title, .item-title, .deal-title, h3, h4",
            "price": ".price, .product-price, .deal-price, .cost, .amount",
            "image": ".product-image img, .item-image img, .deal-image img, img",
            "link": ".product-link, .item-link, .deal-link, a[href*='/product/']",
            "discount": ".discount, .savings, .off",
        }
    
    async def extract_products(
        self,
        page: Page,
        expected_count: int = 10,
        custom_selectors: Optional[Dict[str, str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Extract product data from CJ merchant pages.
        
        Args:
            page: Playwright page object
            expected_count: Expected number of products
            custom_selectors: Optional custom selectors
            
        Returns:
            List of raw product data dictionaries
        """
        selectors = self.get_selectors(custom_selectors)
        
        try:
            # Wait for content to load
            await self._handle_cj_loading(page)
            
            # Find all product containers
            containers = await page.query_selector_all(selectors["product_container"])
            self.logger.info(f"Found {len(containers)} product containers on CJ merchant site")
            
            if not containers:
                raise ProductExtractionError("No product containers found on CJ merchant page")
            
            products = []
            for i, container in enumerate(containers[:expected_count]):
                try:
                    product_data = await self._extract_single_product(container, selectors, page)
                    if product_data:
                        products.append(product_data)
                        
                    # Delay between products
                    await asyncio.sleep(random.uniform(0.3, 0.7))
                    
                except Exception as e:
                    self.logger.warning(f"Failed to extract CJ product {i}: {e}")
                    continue
            
            self.logger.info(f"Successfully extracted {len(products)} products from CJ merchant")
            return products
            
        except Exception as e:
            raise ProductExtractionError(f"CJ product extraction failed: {e}")
    
    async def _handle_cj_loading(self, page: Page) -> None:
        """Handle CJ merchant site loading."""
        try:
            # Wait for product containers with longer timeout (CJ sites can be slow)
            await page.wait_for_selector(
                self.default_selectors["product_container"],
                state="visible",
                timeout=20000
            )
            
            # Wait for network idle
            await page.wait_for_load_state("networkidle", timeout=15000)
            
        except Exception as e:
            self.logger.warning(f"CJ loading handling issue: {e}")
    
    async def _extract_single_product(
        self,
        container,
        selectors: Dict[str, str],
        page: Page
    ) -> Optional[Dict[str, Any]]:
        """Extract data from a single CJ product container."""
        try:
            # Extract title using multiple possible selectors
            title = await self._extract_with_fallbacks(container, selectors["title"].split(", "))
            
            # Extract price
            price = await self._extract_with_fallbacks(container, selectors["price"].split(", "))
            
            # Extract image
            image_url = await self._extract_image(container, selectors["image"].split(", "))
            
            # Extract link
            link = await self._extract_link(container, selectors["link"].split(", "), page)
            
            # Basic validation
            if not all([title, price, image_url, link]):
                return None
            
            return {
                "title": title,
                "price": price,
                "image": image_url,
                "link": link,
                "platform": "cj"
            }
            
        except Exception as e:
            self.logger.warning(f"Failed to extract single CJ product: {e}")
            return None
    
    async def _extract_with_fallbacks(self, container, selectors: List[str]) -> str:
        """Extract text using fallback selectors."""
        for selector in selectors:
            try:
                element = await container.query_selector(selector.strip())
                if element:
                    text = await element.text_content()
                    if text and text.strip():
                        return text.strip()
            except Exception:
                continue
        return ""
    
    async def _extract_image(self, container, selectors: List[str]) -> str:
        """Extract image URL using fallback selectors."""
        for selector in selectors:
            try:
                element = await container.query_selector(selector.strip())
                if element:
                    for attr in ["src", "data-src", "data-lazy-src"]:
                        image_url = await element.get_attribute(attr)
                        if image_url and image_url.startswith("http"):
                            return image_url
            except Exception:
                continue
        return ""
    
    async def _extract_link(self, container, selectors: List[str], page: Page) -> str:
        """Extract product link using fallback selectors."""
        for selector in selectors:
            try:
                element = await container.query_selector(selector.strip())
                if element:
                    link = await element.get_attribute("href")
                    if link:
                        # Make absolute if relative
                        if link.startswith("/"):
                            base_url = page.url
                            parsed = urlparse(base_url)
                            link = f"{parsed.scheme}://{parsed.netloc}{link}"
                        return link
            except Exception:
                continue
        return ""
    
    def validate_product_data(self, product_data: Dict[str, Any]) -> bool:
        """Validate CJ product data."""
        required_fields = ["title", "price", "image", "link"]
        
        # Check all required fields exist and are non-empty
        for field in required_fields:
            if not product_data.get(field, "").strip():
                return False
        
        # Validate title
        title = product_data["title"].strip()
        if len(title) < 3 or len(title) > 500:
            return False
        
        # Validate price format
        price = product_data["price"]
        if not any(c.isdigit() for c in price):
            return False
        
        # Validate image URL
        image_url = product_data["image"]
        if not image_url.startswith("http"):
            return False
        
        # Validate link
        link = product_data["link"]
        if not link.startswith("http"):
            return False
        
        return True
    
    def clean_price(self, price_text: str) -> str:
        """Clean and normalize CJ price text."""
        if not price_text:
            return ""
        
        price = price_text.strip()
        
        # Extract price with dollar sign
        if "$" in price:
            matches = re.findall(r'\$[\d,]+\.?\d*', price)
            if matches:
                return matches[0]
        
        # Extract just numbers and add $
        numbers = re.findall(r'[\d,]+\.?\d*', price)
        if numbers and len(numbers[0]) >= 2:
            return f"${numbers[0]}"
        
        return price
    
    def build_affiliate_url(self, original_url: str) -> str:
        """Build CJ affiliate URL with tracking parameters."""
        if not original_url:
            return ""
        
        # CJ uses click tracking URLs
        # This is a simplified version - actual CJ links are more complex
        separator = "&" if "?" in original_url else "?"
        affiliate_params = f"cjevent=cj_affiliate_{self.affiliate_id}"
        
        return f"{original_url}{separator}{affiliate_params}"