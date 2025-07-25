"""
Playwright-based scraping tools for the Pydantic AI agent.

This module provides tools that the AI agent can use to perform intelligent
web scraping using Playwright browser automation.
"""

from typing import List, Dict, Any, Optional
import asyncio
import random
from playwright.async_api import async_playwright, Page
from pydantic_ai import RunContext
from pydantic_ai import ModelRetry
import logging

from agents.models import ScrapedProduct, AgentDependencies, AffiliateNetwork
from platforms.amazon import AmazonScraper
from platforms.rakuten import RakutenScraper
from platforms.cj import CJScraper
from config.settings import settings

logger = logging.getLogger(__name__)


class PlaywrightScrapingError(Exception):
    """Exception raised when Playwright scraping fails."""
    pass


class PlatformScraperRegistry:
    """Registry for platform-specific scrapers."""
    
    _scrapers: Dict[AffiliateNetwork, Any] = {}
    
    @classmethod
    def get_scraper(cls, platform: AffiliateNetwork):
        """Get the appropriate scraper for the platform."""
        if platform not in cls._scrapers:
            if platform == AffiliateNetwork.AMAZON:
                cls._scrapers[platform] = AmazonScraper()
            elif platform == AffiliateNetwork.RAKUTEN:
                cls._scrapers[platform] = RakutenScraper()
            elif platform == AffiliateNetwork.CJ:
                cls._scrapers[platform] = CJScraper()
            else:
                raise ValueError(f"Unsupported platform: {platform}")
        
        return cls._scrapers[platform]


async def create_browser_context():
    """Create a Playwright browser context with optimal settings for scraping."""
    playwright = await async_playwright().start()
    
    browser = await playwright.chromium.launch(
        headless=settings.browser_headless,
        args=settings.get_browser_args()
    )
    
    # Create context with realistic user agent and settings
    context = await browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        viewport={"width": 1920, "height": 1080},
        locale="en-US",
        timezone_id="America/New_York"
    )
    
    return playwright, browser, context


async def scrape_products_from_url(
    ctx: RunContext[AgentDependencies],
    url: str,
    platform: str,
    category: str = "general",
    expected_count: int = 10,
    custom_selectors: Optional[Dict[str, str]] = None
) -> List[ScrapedProduct]:
    """
    Scrape products from a specific URL using platform-specific logic.
    
    This tool allows the AI agent to intelligently scrape products from
    affiliate URLs while handling platform-specific quirks and anti-bot measures.
    
    Args:
        ctx: Pydantic AI run context with dependencies
        url: URL to scrape products from
        platform: Platform name (amazon, rakuten, cj)
        category: Product category for organization
        expected_count: Expected number of products to extract
        custom_selectors: Optional custom CSS selectors
        
    Returns:
        List of validated ScrapedProduct objects
        
    Raises:
        ModelRetry: For recoverable errors that should trigger retry
    """
    try:
        # Convert platform string to enum
        platform_enum = AffiliateNetwork(platform.lower())
        scraper = PlatformScraperRegistry.get_scraper(platform_enum)
        
        logger.info(f"Starting scrape of {url} for {platform} platform")
        
        # Create browser context
        playwright, browser, context = await create_browser_context()
        
        try:
            page = await context.new_page()
            
            # Add delay to avoid detection
            delay = ctx.deps.scraping_delay_seconds + random.uniform(-0.5, 0.5)
            await asyncio.sleep(delay)
            
            # Navigate to URL with error handling
            try:
                response = await page.goto(url, wait_until="networkidle", timeout=30000)
                
                if not response or response.status >= 400:
                    raise ModelRetry(f"Failed to load {url}: HTTP {response.status if response else 'timeout'}")
                
            except Exception as e:
                if "timeout" in str(e).lower() or "net::" in str(e).lower():
                    raise ModelRetry(f"Network timeout loading {url}. Please retry with longer delay.")
                raise e
            
            # Check for common bot detection patterns
            await _handle_bot_detection(page, url)
            
            # Extract products using platform-specific scraper
            products = await scraper.extract_and_validate_products(
                page=page,
                expected_count=expected_count,
                custom_selectors=custom_selectors,
                category=category
            )
            
            logger.info(f"Successfully scraped {len(products)} products from {url}")
            
            # Filter by quality threshold
            quality_threshold = ctx.deps.quality_threshold
            high_quality_products = [
                p for p in products 
                if p.validation_score >= quality_threshold
            ]
            
            logger.info(f"Filtered to {len(high_quality_products)} high-quality products (score >= {quality_threshold})")
            
            return high_quality_products
            
        finally:
            # Clean up browser resources
            await context.close()
            await browser.close()
            await playwright.stop()
            
    except ModelRetry:
        # Re-raise ModelRetry exceptions so agent can retry
        raise
    except Exception as e:
        error_msg = f"Scraping failed for {url}: {str(e)}"
        logger.error(error_msg)
        
        # Determine if this is a recoverable error
        if any(keyword in str(e).lower() for keyword in ["rate limit", "429", "blocked", "captcha"]):
            raise ModelRetry(f"Rate limited or blocked on {url}. Try again with longer delay.")
        
        # For other errors, return empty list rather than failing completely
        logger.warning(f"Non-recoverable error, returning empty results: {error_msg}")
        return []


async def scrape_multiple_urls(
    ctx: RunContext[AgentDependencies],
    url_configs: List[Dict[str, Any]]
) -> List[ScrapedProduct]:
    """
    Scrape products from multiple URLs efficiently.
    
    Args:
        ctx: Pydantic AI run context
        url_configs: List of URL configuration dictionaries
        
    Returns:
        Combined list of all scraped products
    """
    all_products = []
    
    for url_config in url_configs:
        try:
            # Parse URL config
            url = url_config["url"]
            platform = url_config["platform"]
            category = url_config.get("category", "general")
            expected_count = url_config.get("expected_count", 10)
            custom_selectors = url_config.get("custom_selectors")
            
            # Scrape products from this URL
            products = await scrape_products_from_url(
                ctx=ctx,
                url=url,
                platform=platform,
                category=category,
                expected_count=expected_count,
                custom_selectors=custom_selectors
            )
            
            all_products.extend(products)
            
            # Delay between URLs to be respectful
            inter_url_delay = ctx.deps.scraping_delay_seconds * 2
            await asyncio.sleep(inter_url_delay)
            
        except Exception as e:
            logger.warning(f"Failed to scrape URL {url_config.get('url', 'unknown')}: {e}")
            continue
    
    logger.info(f"Scraped total of {len(all_products)} products from {len(url_configs)} URLs")
    return all_products


async def test_url_accessibility(
    ctx: RunContext[AgentDependencies],
    url: str
) -> Dict[str, Any]:
    """
    Test if a URL is accessible and extract basic page info.
    
    Args:
        ctx: Pydantic AI run context
        url: URL to test
        
    Returns:
        Dictionary with accessibility info
    """
    playwright, browser, context = await create_browser_context()
    
    try:
        page = await context.new_page()
        
        start_time = asyncio.get_event_loop().time()
        response = await page.goto(url, wait_until="domcontentloaded", timeout=15000)
        load_time = asyncio.get_event_loop().time() - start_time
        
        # Extract basic page info
        title = await page.title()
        url_final = page.url  # After redirects
        
        # Check for common issues
        issues = []
        if response.status >= 400:
            issues.append(f"HTTP {response.status}")
        
        if await page.query_selector("#captcha, .captcha"):
            issues.append("CAPTCHA detected")
        
        if "blocked" in title.lower() or "access denied" in title.lower():
            issues.append("Access blocked")
        
        return {
            "accessible": response.status < 400 and not issues,
            "status_code": response.status,
            "load_time_seconds": round(load_time, 2),
            "title": title,
            "final_url": url_final,
            "issues": issues
        }
        
    except Exception as e:
        return {
            "accessible": False,
            "error": str(e),
            "issues": ["Connection failed"]
        }
    finally:
        await context.close()
        await browser.close()
        await playwright.stop()


async def _handle_bot_detection(page: Page, url: str) -> None:
    """Handle common bot detection mechanisms."""
    # Wait a moment for any detection scripts to run
    await asyncio.sleep(1)
    
    # Check for common bot detection indicators
    bot_indicators = [
        "#captcha",
        ".captcha",
        "[aria-label*='captcha']",
        "input[name*='captcha']",
        ".cf-browser-verification",  # Cloudflare
        "#challenge-form",  # Generic challenge
        ".anti-bot",
        ".bot-detection"
    ]
    
    for indicator in bot_indicators:
        if await page.query_selector(indicator):
            raise ModelRetry(f"Bot detection triggered on {url}. Please retry with different parameters.")
    
    # Check page title for bot detection
    title = await page.title()
    if any(phrase in title.lower() for phrase in ["blocked", "captcha", "verification", "challenge"]):
        raise ModelRetry(f"Bot detection in page title on {url}: {title}")
    
    # Check for redirects to known bot detection pages
    current_url = page.url
    if any(domain in current_url.lower() for domain in ["captcha", "challenge", "blocked"]):
        raise ModelRetry(f"Redirected to bot detection page: {current_url}")


async def simulate_human_behavior(page: Page) -> None:
    """Simulate realistic human browsing behavior."""
    # Random mouse movements
    await page.mouse.move(
        random.randint(100, 500),
        random.randint(100, 400)
    )
    
    # Random scroll
    scroll_distance = random.randint(100, 800)
    await page.evaluate(f"window.scrollBy(0, {scroll_distance})")
    
    # Brief pause
    await asyncio.sleep(random.uniform(0.5, 2.0))
    
    # Hover over a random element occasionally
    if random.random() < 0.3:  # 30% chance
        try:
            elements = await page.query_selector_all("a, button, .product")
            if elements:
                random_element = random.choice(elements)
                await random_element.hover()
                await asyncio.sleep(random.uniform(0.2, 0.8))
        except Exception:
            pass  # Ignore hover errors