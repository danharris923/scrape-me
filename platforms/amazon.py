"""
Amazon-specific scraper implementation.

This module implements the Amazon affiliate product scraper with specific selectors
and handling for Amazon's search results and anti-bot measures.
"""

from typing import List, Dict, Any, Optional
from playwright.async_api import Page
import re
import asyncio
import random

from .base import BasePlatformScraper, ProductExtractionError
from agents.models import AffiliateNetwork


class AmazonScraper(BasePlatformScraper):
    """
    Amazon-specific product scraper.
    
    Handles Amazon search results pages with their specific HTML structure,
    anti-bot measures, and affiliate link construction.
    """
    
    def __init__(self):
        super().__init__(AffiliateNetwork.AMAZON)
        self.affiliate_tag = "your_affiliate_tag"  # Should be configurable
        
    @property
    def platform_name(self) -> str:
        return "Amazon"
    
    @property 
    def default_selectors(self) -> Dict[str, str]:
        """Default selectors for Amazon search results."""
        return {
            "product_container": "[data-component-type='s-search-result']",
            "title": "h2 a span, h2 span",
            "price": ".a-price-whole, .a-price .a-offscreen",
            "image": ".s-image",
            "link": "h2 a",
            "rating": ".a-icon-alt",
            "reviews": "a[href*='#customerReviews'] span",
        }
    
    async def extract_products(
        self,
        page: Page,
        expected_count: int = 10,
        custom_selectors: Optional[Dict[str, str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Extract product data from Amazon search results.
        
        Args:
            page: Playwright page object
            expected_count: Expected number of products
            custom_selectors: Optional custom selectors
            
        Returns:
            List of raw product data dictionaries
        """
        selectors = self.get_selectors(custom_selectors)
        
        try:
            # Wait for Amazon's dynamic content to load
            await self._handle_amazon_loading(page)
            
            # Find all product containers
            containers = await page.query_selector_all(selectors["product_container"])
            self.logger.info(f"Found {len(containers)} product containers on Amazon")
            
            if not containers:
                raise ProductExtractionError("No product containers found on Amazon page")
            
            products = []
            for i, container in enumerate(containers[:expected_count]):
                try:
                    product_data = await self._extract_single_product(container, selectors, page)
                    if product_data:
                        products.append(product_data)
                        
                    # Random delay between products to avoid detection
                    await asyncio.sleep(random.uniform(0.1, 0.3))
                    
                except Exception as e:
                    self.logger.warning(f"Failed to extract product {i}: {e}")
                    continue
            
            self.logger.info(f"Successfully extracted {len(products)} products from Amazon")
            return products
            
        except Exception as e:
            raise ProductExtractionError(f"Amazon product extraction failed: {e}")
    
    async def _handle_amazon_loading(self, page: Page) -> None:
        """Handle Amazon's loading states and potential bot detection."""
        try:
            # Wait for search results to appear
            await page.wait_for_selector(
                self.default_selectors["product_container"],
                state="visible", 
                timeout=15000
            )
            
            # Check for bot detection page
            captcha_selector = "#captchacharacters, .a-box-inner h4"
            if await page.query_selector(captcha_selector):
                raise ProductExtractionError("Amazon bot detection triggered - CAPTCHA required")
            
            # Wait for images to load (Amazon loads them dynamically)
            await page.wait_for_load_state("networkidle", timeout=10000)
            
            # Scroll to trigger lazy loading
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight / 2)")
            await asyncio.sleep(1)
            
        except Exception as e:
            self.logger.warning(f"Amazon loading handling issue: {e}")
    
    async def _extract_single_product(
        self, 
        container, 
        selectors: Dict[str, str], 
        page: Page
    ) -> Optional[Dict[str, Any]]:
        """Extract data from a single Amazon product container."""
        try:
            # Extract title
            title_element = await container.query_selector(selectors["title"])
            title = ""
            if title_element:
                title = await title_element.text_content()
                title = title.strip() if title else ""
            
            # Extract price - Amazon has multiple price formats
            price = await self._extract_amazon_price(container, selectors)
            
            # Extract image URL
            image_element = await container.query_selector(selectors["image"])
            image_url = ""
            if image_element:
                # Try src first, then data-src for lazy loaded images
                image_url = await image_element.get_attribute("src")
                if not image_url or "data:image" in image_url:
                    image_url = await image_element.get_attribute("data-src") or ""
            
            # Extract product link
            link_element = await container.query_selector(selectors["link"])
            link = ""
            if link_element:
                link = await link_element.get_attribute("href")
                if link and link.startswith("/"):
                    link = f"https://www.amazon.com{link}"
            
            # Basic validation
            if not all([title, price, image_url, link]):
                self.logger.debug(f"Incomplete product data: title={bool(title)}, price={bool(price)}, image={bool(image_url)}, link={bool(link)}")
                return None
            
            return {
                "title": title,
                "price": price,
                "image": image_url,
                "link": link,
                "platform": "amazon"
            }
            
        except Exception as e:
            self.logger.warning(f"Failed to extract single Amazon product: {e}")
            return None
    
    async def _extract_amazon_price(self, container, selectors: Dict[str, str]) -> str:
        """Extract price from Amazon's various price formats."""
        price_selectors = [
            ".a-price-whole",
            ".a-price .a-offscreen", 
            ".a-price-range .a-offscreen",
            ".a-price-symbol + .a-price-whole",
            ".a-text-price .a-offscreen"
        ]
        
        for price_selector in price_selectors:
            try:
                price_element = await container.query_selector(price_selector)
                if price_element:
                    price_text = await price_element.text_content()
                    if price_text and price_text.strip():
                        # Clean up the price text
                        price = price_text.strip()
                        if "$" in price or any(c.isdigit() for c in price):
                            return price
            except Exception:
                continue
        
        return ""
    
    def validate_product_data(self, product_data: Dict[str, Any]) -> bool:
        """Validate Amazon product data."""
        required_fields = ["title", "price", "image", "link"]
        
        # Check all required fields exist and are non-empty
        for field in required_fields:
            if not product_data.get(field, "").strip():
                return False
        
        # Validate title length
        title = product_data["title"].strip()
        if len(title) < 5 or len(title) > 200:
            return False
        
        # Validate price contains currency or numbers
        price = product_data["price"]
        if not (any(c.isdigit() for c in price) or "$" in price):
            return False
        
        # Validate image URL
        image_url = product_data["image"]
        if not (image_url.startswith("http") and any(ext in image_url.lower() for ext in [".jpg", ".jpeg", ".png", ".webp"])):
            return False
        
        # Validate Amazon link
        link = product_data["link"]
        if not ("amazon.com" in link and link.startswith("http")):
            return False
        
        return True
    
    def clean_price(self, price_text: str) -> str:
        """Clean and normalize Amazon price text."""
        if not price_text:
            return ""
        
        # Remove extra whitespace
        price = price_text.strip()
        
        # Handle price ranges (take the first price)
        if " - " in price:
            price = price.split(" - ")[0]
        
        # Ensure dollar sign is present
        if "$" not in price and any(c.isdigit() for c in price):
            # Try to extract just the numeric part and add $
            numbers = re.findall(r'[\d,]+\.?\d*', price)
            if numbers:
                price = f"${numbers[0]}"
        
        # Clean up common formatting issues
        price = re.sub(r'\s+', ' ', price)  # Normalize whitspace
        price = price.replace('$ ', '$')     # Remove space after $
        
        return price
    
    def build_affiliate_url(self, original_url: str) -> str:
        """Build Amazon affiliate URL with tracking parameters."""
        if not original_url:
            return ""
        
        # Extract ASIN or product ID from URL
        asin_match = re.search(r'/dp/([A-Z0-9]{10})', original_url)
        if not asin_match:
            # Fallback: just add affiliate tag to existing URL
            separator = "&" if "?" in original_url else "?"
            return f"{original_url}{separator}tag={self.affiliate_tag}"
        
        asin = asin_match.group(1)
        
        # Build clean affiliate URL
        affiliate_url = f"https://www.amazon.com/dp/{asin}?tag={self.affiliate_tag}"
        
        return affiliate_url
        
    async def handle_pagination(self, page: Page) -> bool:
        """
        Handle Amazon pagination to get more products.
        
        Args:
            page: Playwright page object
            
        Returns:
            True if next page exists and was navigated to, False otherwise
        """
        try:
            # Look for next page link
            next_link = await page.query_selector("a[aria-label='Go to next page']")
            if not next_link:
                next_link = await page.query_selector(".s-pagination-next")
            
            if next_link:
                # Check if next link is disabled
                classes = await next_link.get_attribute("class") or ""
                if "disabled" in classes:
                    return False
                
                # Click next page
                await next_link.click()
                
                # Wait for new page to load
                await self._handle_amazon_loading(page)
                
                return True
            
            return False
            
        except Exception as e:
            self.logger.warning(f"Amazon pagination handling failed: {e}")
            return False