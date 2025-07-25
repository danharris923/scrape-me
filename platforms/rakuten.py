"""
Rakuten-specific scraper implementation.

This module implements the Rakuten affiliate product scraper with specific selectors
and handling for Rakuten's product pages and affiliate link construction.
"""

from typing import List, Dict, Any, Optional
from playwright.async_api import Page
import re
import asyncio
import random
from urllib.parse import urlparse

from .base import BasePlatformScraper, ProductExtractionError
from agents.models import AffiliateNetwork


class RakutenScraper(BasePlatformScraper):
    """
    Rakuten-specific product scraper.
    
    Handles Rakuten marketplace pages with their specific HTML structure
    and affiliate link construction.
    """
    
    def __init__(self):
        super().__init__(AffiliateNetwork.RAKUTEN)
        self.affiliate_id = "your_rakuten_affiliate_id"  # Should be configurable
        
    @property
    def platform_name(self) -> str:
        return "Rakuten"
    
    @property
    def default_selectors(self) -> Dict[str, str]:
        """Default selectors for Rakuten product pages."""
        return {
            "product_container": ".product-item, .item, .product-card",
            "title": ".product-title, .item-title, h3 a, .title",
            "price": ".price, .product-price, .item-price, .cost",
            "image": ".product-image img, .item-image img, img",
            "link": ".product-link, .item-link, a[href*='/product/'], a[href*='/item/']",
            "rating": ".rating, .stars, .review-rating",
            "shop": ".shop-name, .store-name, .merchant",
        }
    
    async def extract_products(
        self,
        page: Page,
        expected_count: int = 10,
        custom_selectors: Optional[Dict[str, str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Extract product data from Rakuten pages.
        
        Args:
            page: Playwright page object
            expected_count: Expected number of products
            custom_selectors: Optional custom selectors
            
        Returns:
            List of raw product data dictionaries
        """
        selectors = self.get_selectors(custom_selectors)
        
        try:
            # Wait for Rakuten's content to load
            await self._handle_rakuten_loading(page)
            
            # Find all product containers
            containers = await page.query_selector_all(selectors["product_container"])
            self.logger.info(f"Found {len(containers)} product containers on Rakuten")
            
            if not containers:
                raise ProductExtractionError("No product containers found on Rakuten page")
            
            products = []
            for i, container in enumerate(containers[:expected_count]):
                try:
                    product_data = await self._extract_single_product(container, selectors, page)
                    if product_data:
                        products.append(product_data)
                        
                    # Delay between products to be respectful
                    await asyncio.sleep(random.uniform(0.2, 0.5))
                    
                except Exception as e:
                    self.logger.warning(f"Failed to extract Rakuten product {i}: {e}")
                    continue
            
            self.logger.info(f"Successfully extracted {len(products)} products from Rakuten")
            return products
            
        except Exception as e:
            raise ProductExtractionError(f"Rakuten product extraction failed: {e}")
    
    async def _handle_rakuten_loading(self, page: Page) -> None:
        """Handle Rakuten's loading states."""
        try:
            # Wait for product containers to appear
            await page.wait_for_selector(
                self.default_selectors["product_container"],
                state="visible",
                timeout=15000
            )
            
            # Wait for network to be idle
            await page.wait_for_load_state("networkidle", timeout=10000)
            
            # Scroll to trigger any lazy loading
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight / 3)")
            await asyncio.sleep(1)
            
        except Exception as e:
            self.logger.warning(f"Rakuten loading handling issue: {e}")
    
    async def _extract_single_product(
        self,
        container,
        selectors: Dict[str, str],
        page: Page
    ) -> Optional[Dict[str, Any]]:
        """Extract data from a single Rakuten product container."""
        try:
            # Extract title
            title = await self._extract_rakuten_title(container, selectors)
            
            # Extract price
            price = await self._extract_rakuten_price(container, selectors)
            
            # Extract image URL
            image_url = await self._extract_rakuten_image(container, selectors)
            
            # Extract product link
            link = await self._extract_rakuten_link(container, selectors, page)
            
            # Basic validation
            if not all([title, price, image_url, link]):
                self.logger.debug(f"Incomplete Rakuten product data: title={bool(title)}, price={bool(price)}, image={bool(image_url)}, link={bool(link)}")
                return None
            
            return {
                "title": title,
                "price": price, 
                "image": image_url,
                "link": link,
                "platform": "rakuten"
            }
            
        except Exception as e:
            self.logger.warning(f"Failed to extract single Rakuten product: {e}")
            return None
    
    async def _extract_rakuten_title(self, container, selectors: Dict[str, str]) -> str:
        """Extract title from Rakuten product."""
        title_selectors = selectors["title"].split(", ")
        
        for title_selector in title_selectors:
            try:
                title_element = await container.query_selector(title_selector.strip())
                if title_element:
                    title = await title_element.text_content()
                    if title and title.strip():
                        return title.strip()
            except Exception:
                continue
        
        return ""
    
    async def _extract_rakuten_price(self, container, selectors: Dict[str, str]) -> str:
        """Extract price from Rakuten product."""
        price_selectors = selectors["price"].split(", ")
        
        for price_selector in price_selectors:
            try:
                price_element = await container.query_selector(price_selector.strip())
                if price_element:
                    price_text = await price_element.text_content()
                    if price_text and price_text.strip():
                        price = price_text.strip()
                        # Check if it looks like a price
                        if any(c.isdigit() for c in price) and ("$" in price or "¥" in price or "price" in price_selector.lower()):
                            return price
            except Exception:
                continue
        
        return ""
    
    async def _extract_rakuten_image(self, container, selectors: Dict[str, str]) -> str:
        """Extract image URL from Rakuten product."""
        image_selectors = selectors["image"].split(", ")
        
        for image_selector in image_selectors:
            try:
                image_element = await container.query_selector(image_selector.strip())
                if image_element:
                    # Try different image attributes
                    for attr in ["src", "data-src", "data-lazy-src"]:
                        image_url = await image_element.get_attribute(attr)
                        if image_url and image_url.startswith("http") and not image_url.startswith("data:"):
                            return image_url
            except Exception:
                continue
        
        return ""
    
    async def _extract_rakuten_link(self, container, selectors: Dict[str, str], page: Page) -> str:
        """Extract product link from Rakuten product."""
        link_selectors = selectors["link"].split(", ")
        
        for link_selector in link_selectors:
            try:
                link_element = await container.query_selector(link_selector.strip())
                if link_element:
                    link = await link_element.get_attribute("href")
                    if link:
                        # Make absolute URL if relative
                        if link.startswith("/"):
                            base_url = page.url
                            parsed = urlparse(base_url)
                            link = f"{parsed.scheme}://{parsed.netloc}{link}"
                        elif not link.startswith("http"):
                            continue
                        return link
            except Exception:
                continue
        
        return ""
    
    def validate_product_data(self, product_data: Dict[str, Any]) -> bool:
        """Validate Rakuten product data."""
        required_fields = ["title", "price", "image", "link"]
        
        # Check all required fields exist and are non-empty
        for field in required_fields:
            if not product_data.get(field, "").strip():
                return False
        
        # Validate title length
        title = product_data["title"].strip()
        if len(title) < 3 or len(title) > 300:
            return False
        
        # Validate price contains currency or numbers
        price = product_data["price"]
        if not (any(c.isdigit() for c in price) or any(symbol in price for symbol in ["$", "¥", "USD", "JPY"])):
            return False
        
        # Validate image URL
        image_url = product_data["image"]
        if not (image_url.startswith("http") and any(ext in image_url.lower() for ext in [".jpg", ".jpeg", ".png", ".webp", ".gif"])):
            return False
        
        # Validate Rakuten link
        link = product_data["link"]
        if not (("rakuten" in link.lower() or "rms.rakuten" in link.lower()) and link.startswith("http")):
            return False
        
        return True
    
    def clean_price(self, price_text: str) -> str:
        """Clean and normalize Rakuten price text."""
        if not price_text:
            return ""
        
        # Remove extra whitespace
        price = price_text.strip()
        
        # Handle different currency formats
        if "¥" in price:
            # Japanese Yen format
            numbers = re.findall(r'¥[\d,]+', price)
            if numbers:
                return numbers[0]
        
        if "$" in price:
            # USD format
            numbers = re.findall(r'\$[\d,]+\.?\d*', price)
            if numbers:
                return numbers[0]
        
        # Try to extract just numeric value and add $
        numbers = re.findall(r'[\d,]+\.?\d*', price)
        if numbers:
            numeric_price = numbers[0]
            if len(numeric_price) >= 2:  # Reasonable price
                return f"${numeric_price}"
        
        return price
    
    def build_affiliate_url(self, original_url: str) -> str:
        """Build Rakuten affiliate URL with tracking parameters."""
        if not original_url:
            return ""
        
        # Rakuten affiliate links typically need specific parameters
        separator = "&" if "?" in original_url else "?"
        
        # Add Rakuten affiliate parameters
        affiliate_params = f"ranMID={self.affiliate_id}&ranEAID=123456&ranSiteID=affiliate"
        
        return f"{original_url}{separator}{affiliate_params}"
    
    async def handle_pagination(self, page: Page) -> bool:
        """
        Handle Rakuten pagination to get more products.
        
        Args:
            page: Playwright page object
            
        Returns:
            True if next page exists and was navigated to, False otherwise
        """
        try:
            # Look for next page link (various formats on Rakuten)
            next_selectors = [
                "a[rel='next']",
                ".next a",
                ".pagination-next",
                "a:has-text('Next')",
                "a:has-text('次へ')"  # Japanese "Next"
            ]
            
            for selector in next_selectors:
                next_link = await page.query_selector(selector)
                if next_link:
                    # Check if link is enabled
                    classes = await next_link.get_attribute("class") or ""
                    if "disabled" not in classes:
                        await next_link.click()
                        await self._handle_rakuten_loading(page)
                        return True
            
            return False
            
        except Exception as e:
            self.logger.warning(f"Rakuten pagination handling failed: {e}")
            return False