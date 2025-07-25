name: "Modular Affiliate Scraper Engine - Single Agent with Intelligent Tools"
description: |

## Purpose
Build a production-ready intelligent affiliate scraper engine using Pydantic AI with Playwright tools that feeds multiple affiliate marketing websites. The system will be deployed via GCP browser SSH and run on Ubuntu 22.04 VM, scraping product data from multiple affiliate platforms and outputting validated JSON that directly feeds Vercel-hosted affiliate sites.

## Core Principles
1. **Quality Over Quantity**: Only publish validated, complete product data
2. **Intelligent Scraping**: AI agent makes scraping decisions rather than hard-coded rules
3. **Graceful Degradation**: Preserve last good data on failures
4. **Scalability**: Easy to add new sites and affiliate platforms
5. **Stealth Operation**: Slow scraping to avoid detection

---

## Goal
Create an intelligent scraper engine that automatically extracts affiliate product data, processes images, validates content, and outputs JSON files that directly feed multiple affiliate marketing websites built from the site template architecture.

## Why
- **Business Value**: Automates content creation for multiple affiliate sites
- **Integration**: Directly feeds the D:/git/scale-me/site template ecosystem
- **Problems Solved**: Manual product data entry, image processing, content validation
- **Scale**: One engine feeding dozens of affiliate sites

## What
A single intelligent Pydantic AI agent with specialized tools that:
- Reads site-specific config files to determine what to scrape
- Uses Playwright to intelligently extract product data
- Downloads and uploads images to GCS with SEO naming
- Validates all data through Pydantic models
- Outputs JSON that matches the site template's ProductSchema
- Handles scheduling and manual refresh triggers
- Maintains state for graceful error recovery

### Success Criteria
- [ ] Agent successfully scrapes Amazon, Rakuten, and CJ affiliate links
- [ ] Images are downloaded, renamed, uploaded to GCS, and made public
- [ ] Output JSON matches ProductSchema from site template exactly
- [ ] System gracefully handles failures without breaking sites
- [ ] Easy to add new sites via config files
- [ ] Runs reliably on GCP VM via browser SSH

## All Needed Context

### Documentation & References
```yaml
# MUST READ - Include these in your context window
- url: https://ai.pydantic.dev/agents/
  why: Core agent creation patterns and tool registration
  
- url: https://ai.pydantic.dev/tools/
  why: Tool creation, error handling, and RunContext usage
  
- url: https://ai.pydantic.dev/models/
  why: LLM provider configuration and model selection
  
- url: https://playwright.dev/python/docs/intro
  why: Playwright Python installation and basic browser automation
  
- url: https://playwright.dev/python/docs/locators
  why: Element selection and data extraction patterns
  
- url: https://cloud.google.com/storage/docs/uploading-objects
  why: GCS file upload and public URL generation

- file: D:/git/scale-me/site/agents/models.py
  why: ProductSchema that output must match exactly
  
- file: D:/git/scale-me/site/templates/react/components/ProductCard.tsx.template  
  why: Understanding how product data is consumed by sites
  
- docfile: research/pydantic-ai/agents.md
  why: Agent creation and system prompt patterns
  
- docfile: research/pydantic-ai/tools.md  
  why: Tool decorator usage and error handling
  
- docfile: research/playwright/web-scraping.md
  why: Playwright scraping techniques and element selection
  
- docfile: research/gcs/upload-and-public.md
  why: Image upload and public URL generation
```

### Current Codebase tree
```bash
D:\git\scale-me\scraper\
├── CLAUDE.md
├── initial.md
├── PRPs/
│   ├── templates/
│   │   └── prp_base.md
│   └── EXAMPLE_multi_agent_prp.md
├── research/
│   ├── pydantic-ai/
│   │   ├── agents.md
│   │   ├── multi-agent.md
│   │   ├── tools.md
│   │   └── models.md
│   ├── playwright/
│   │   └── web-scraping.md
│   └── gcs/
│       └── upload-and-public.md
└── examples/
    └── (empty - no Python files yet)
```

### Desired Codebase tree with files to be added
```bash
D:\git\scale-me\scraper\
├── main.py                           # CLI entry point and orchestration
├── config/
│   ├── __init__.py                   # Package init
│   ├── settings.py                   # Environment and global settings
│   └── sites/                        # Site-specific configurations
│       ├── outdoor-gear-site.json    # Example site config
│       └── tech-deals-site.json      # Example site config
├── agents/
│   ├── __init__.py                   # Package init
│   ├── scraper_agent.py              # Main Pydantic AI agent
│   └── models.py                     # Data models matching site template
├── tools/
│   ├── __init__.py                   # Package init
│   ├── playwright_scraper.py         # Playwright scraping tools
│   ├── image_processor.py            # Image download and GCS upload
│   ├── data_validator.py             # Pydantic validation tools
│   └── state_manager.py              # Last good data preservation
├── platforms/
│   ├── __init__.py                   # Package init
│   ├── base.py                       # Base platform interface
│   ├── amazon.py                     # Amazon-specific selectors
│   ├── rakuten.py                    # Rakuten-specific selectors
│   └── cj.py                         # Commission Junction selectors
├── tests/
│   ├── __init__.py                   # Package init
│   ├── test_scraper_agent.py         # Agent behavior tests
│   ├── test_tools.py                 # Tool functionality tests
│   └── test_integration.py           # End-to-end tests
├── output/                           # Generated JSON files
├── state/                            # Last good data backups
├── requirements.txt                  # Dependencies
├── setup.sh                          # VM setup script
└── Dockerfile                        # Optional containerization
```

### Known Gotchas & Library Quirks
```python
# CRITICAL: Pydantic AI requires async throughout - no sync functions in async context
# CRITICAL: Playwright auto-waits - don't use time.sleep(), use page.wait_for_timeout()
# CRITICAL: GCS requires proper auth - use service account JSON or gcloud auth
# CRITICAL: Product images must be downloaded before upload to avoid 403 errors
# CRITICAL: Slow down scraping with delays to avoid rate limiting/detection
# CRITICAL: Browser must be launched with specific flags on GCP VM for headful mode
# CRITICAL: Always validate data with Pydantic models before output
# CRITICAL: Use absolute imports throughout the project
# CRITICAL: Store sensitive credentials in environment variables, never commit them
```

## Implementation Blueprint

### Data models and structure

```python
# agents/models.py - Mirror site template exactly
from pydantic import BaseModel, Field, HttpUrl
from typing import List, Optional, Dict, Any, Literal
from datetime import datetime
from enum import Enum

class AffiliateNetwork(str, Enum):
    """Supported affiliate networks."""
    AMAZON = "amazon"
    RAKUTEN = "rakuten" 
    CJ = "cj"

class ProductCard(BaseModel):
    """Product data structure - MUST match site template exactly."""
    title: str
    price: str
    affiliate_url: HttpUrl
    image_url: HttpUrl
    slug: str

class ScrapedProduct(BaseModel):
    """Internal scraping result with additional metadata."""
    title: str = Field(..., min_length=1)
    price: str = Field(..., description="Original price string from site")
    affiliate_url: HttpUrl
    original_image_url: HttpUrl = Field(..., description="Source image URL")
    processed_image_url: Optional[HttpUrl] = None
    category: str
    platform: AffiliateNetwork
    scraped_at: datetime = Field(default_factory=datetime.now)
    validation_score: float = Field(..., ge=0.0, le=1.0)
    
    def to_product_card(self) -> ProductCard:
        """Convert to ProductCard format for output."""
        slug = self.title.lower().replace(' ', '-')[:50]
        return ProductCard(
            title=self.title,
            price=self.price,
            affiliate_url=self.affiliate_url,
            image_url=self.processed_image_url or self.original_image_url,
            slug=slug
        )

class SiteConfig(BaseModel):
    """Configuration for each affiliate site."""
    site_name: str
    output_path: str = Field(..., description="Path to write JSON file")
    gcs_bucket: str = Field(..., description="GCS bucket for images")
    image_folder: str = Field(default="products", description="Folder in bucket")
    urls_to_scrape: List[Dict[str, Any]] = Field(..., description="URLs and metadata")
    refresh_interval_hours: int = Field(default=24)
    last_scraped: Optional[datetime] = None
    
class AgentDependencies(BaseModel):
    """Dependencies injected into the agent."""
    gcs_credentials_path: str
    output_directory: str = Field(default="./output")
    state_directory: str = Field(default="./state") 
    scraping_delay_seconds: float = Field(default=2.0)
    max_retries: int = Field(default=3)
```

### List of tasks to be completed

```yaml
Task 1: Setup Project Structure and Configuration
CREATE config/settings.py:
  - PATTERN: Use pydantic-settings for environment variables
  - Load GCS credentials, API keys, directories
  - Validate all required environment variables present

CREATE config/sites/outdoor-gear-site.json:
  - Example site configuration with Amazon and Rakuten URLs
  - Include selectors, categories, output paths
  - Follow SiteConfig model structure

Task 2: Implement Core Data Models
CREATE agents/models.py:
  - CRITICAL: Mirror ProductCard from site template exactly
  - Add ScrapedProduct with validation and conversion
  - Include SiteConfig for per-site configuration
  - Add AgentDependencies for dependency injection

Task 3: Create Platform-Specific Scrapers
CREATE platforms/base.py:
  - Abstract base class for platform scrapers
  - Define interface for product extraction
  - Include retry and error handling patterns

CREATE platforms/amazon.py:
  - Amazon-specific selectors and extraction logic
  - Handle Amazon's anti-bot measures with delays
  - Extract title, price, image, affiliate link

CREATE platforms/rakuten.py:
  - Rakuten-specific selectors and extraction
  - Handle Rakuten's product page structure
  - PATTERN: Follow amazon.py structure

CREATE platforms/cj.py:
  - Commission Junction network extraction
  - Handle various merchant site structures
  - PATTERN: Follow base.py interface

Task 4: Implement Playwright Scraping Tools
CREATE tools/playwright_scraper.py:
  - PATTERN: Use @agent.tool decorator for tool registration
  - Launch browser with headful mode for GCP VM
  - Implement slow scraping with configurable delays
  - Handle element waiting and extraction
  - Include error handling with ModelRetry

Task 5: Create Image Processing Tool
CREATE tools/image_processor.py:
  - PATTERN: Async tool with RunContext
  - Download images from original URLs
  - Generate SEO-friendly filenames (product-title-category.jpg)
  - Upload to GCS and make public
  - Return public URLs for processed images

Task 6: Build Data Validation Tool
CREATE tools/data_validator.py:
  - PATTERN: Use Pydantic models for validation
  - Score products based on completeness and quality
  - Filter out incomplete or suspicious data
  - Convert ScrapedProduct to ProductCard format

Task 7: Implement State Management Tool
CREATE tools/state_manager.py:
  - PATTERN: JSON file-based state persistence
  - Save last good scraping results per site
  - Load previous state on failures
  - Merge new good data with preserved data

Task 8: Create Main Scraper Agent
CREATE agents/scraper_agent.py:
  - PATTERN: Single Agent with multiple tools registered
  - Use Anthropic Claude or OpenAI GPT-4 as model
  - Register all tools with @agent.tool decorators
  - Implement intelligent scraping workflow
  - Include system prompt for decision-making

Task 9: Build CLI and Orchestration
CREATE main.py:
  - PATTERN: CLI with argparse for site selection
  - Load site configs and run scraper agent
  - Handle cron scheduling and manual refresh
  - Output final JSON files for Vercel sites

Task 10: Add Comprehensive Testing
CREATE tests/:
  - PATTERN: Pytest with async test support
  - Mock Playwright and GCS calls for unit tests
  - Test agent decision-making with sample data
  - End-to-end tests with real (rate-limited) scraping

Task 11: Create VM Setup Script
CREATE setup.sh:
  - Install Python 3.10+, pip, Playwright
  - Install Chrome/Chromium for headful browsing
  - Set up GCS authentication
  - Configure cron jobs

Task 12: Add Production Documentation
CREATE README.md:
  - PATTERN: Include setup, configuration, usage
  - Document site config format and examples
  - Include troubleshooting for common GCP VM issues
  - Explain integration with site template
```

### Per task pseudocode

```python
# Task 4: Playwright Scraping Tool
@scraper_agent.tool
async def scrape_products_from_url(
    ctx: RunContext[AgentDependencies], 
    url: str, 
    platform: str, 
    expected_count: int = 10
) -> List[ScrapedProduct]:
    """Intelligently scrape products from affiliate URL."""
    
    # PATTERN: Get platform-specific scraper
    platform_scraper = get_platform_scraper(platform)  # amazon.py, rakuten.py, etc
    
    # CRITICAL: Launch browser with specific flags for GCP VM
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,  # Headful on VM for debugging
            args=['--no-sandbox', '--disable-dev-shm-usage']  # GCP VM flags
        )
        page = await browser.new_page()
        
        # GOTCHA: Add random delays to avoid detection
        await page.wait_for_timeout(random.randint(1000, 3000))
        
        try:
            await page.goto(url)
            await page.wait_for_load_state("networkidle")
            
            # PATTERN: Use platform-specific extraction
            products = await platform_scraper.extract_products(page, expected_count)
            
            # CRITICAL: Validate each product immediately
            validated_products = []
            for product_data in products:
                try:
                    product = ScrapedProduct(**product_data)
                    if product.validation_score >= 0.7:  # Quality threshold
                        validated_products.append(product)
                except ValidationError as e:
                    # PATTERN: Log but continue with good data
                    logger.warning(f"Invalid product data: {e}")
                    continue
            
            return validated_products
            
        except Exception as e:
            # PATTERN: Use ModelRetry for recoverable errors
            if "rate limit" in str(e).lower():
                raise ModelRetry(f"Rate limited on {url}. Try again with longer delay.")
            raise e
        finally:
            await browser.close()

# Task 5: Image Processing Tool  
@scraper_agent.tool
async def process_product_images(
    ctx: RunContext[AgentDependencies],
    products: List[ScrapedProduct]
) -> List[ScrapedProduct]:
    """Download images, upload to GCS, return updated products."""
    
    # PATTERN: Use GCS client from dependencies
    gcs_client = storage.Client.from_service_account_json(
        ctx.deps.gcs_credentials_path
    )
    
    processed_products = []
    for product in products:
        try:
            # CRITICAL: Download image first to avoid 403 on direct upload
            async with httpx.AsyncClient() as client:
                response = await client.get(product.original_image_url)
                response.raise_for_status()
                
                # PATTERN: Generate SEO filename
                safe_title = product.title.lower().replace(' ', '-')[:30]
                safe_category = product.category.lower().replace(' ', '-')
                filename = f"{safe_title}-{safe_category}.jpg"
                
                # Upload to GCS
                bucket = gcs_client.bucket(ctx.deps.gcs_bucket)
                blob = bucket.blob(f"products/{filename}")
                blob.upload_from_string(response.content, content_type='image/jpeg')
                blob.make_public()
                
                # Update product with processed URL
                product.processed_image_url = blob.public_url
                processed_products.append(product)
                
        except Exception as e:
            # GOTCHA: Continue with original image if processing fails
            logger.warning(f"Image processing failed for {product.title}: {e}")
            processed_products.append(product)  # Keep original image_url
            
        # CRITICAL: Rate limiting for GCS
        await asyncio.sleep(0.5)
    
    return processed_products

# Task 8: Main Agent System Prompt and Orchestration
scraper_agent = Agent(
    'anthropic:claude-3-5-sonnet-latest',
    deps_type=AgentDependencies,
    system_prompt="""You are an intelligent affiliate product scraper. Your job is to:

1. **Quality Decision Making**: Only extract products with complete information (title, price, image, link)
2. **Platform Intelligence**: Adapt scraping strategy based on the affiliate platform (Amazon, Rakuten, CJ)
3. **Error Recovery**: When scraping fails, preserve last good data and continue with successful extractions
4. **Content Validation**: Score each product's data quality and only output products scoring 0.7 or higher
5. **Stealth Operation**: Use random delays and human-like browsing patterns to avoid detection

When scraping a URL:
- First determine the affiliate platform and expected product count
- Use appropriate selectors for that platform
- Validate each product immediately after extraction
- Process images and upload to GCS with SEO-friendly names
- Only include products in final output if all data is valid and complete
- If a site is temporarily unavailable, use the last good data from state

Remember: Broken sites are worse than missing products. Quality over quantity always."""
)
```

### Integration Points
```yaml
GCP VM SETUP:
  - Ubuntu 22.04 with Python 3.10+
  - Playwright with Chromium installed
  - GCS service account authentication
  - Cron job configuration for scheduling

ENVIRONMENT VARIABLES:
  - GCP_CREDENTIALS_PATH: Path to service account JSON
  - GCS_BUCKET_NAME: Default bucket for image uploads
  - SCRAPER_DELAY_SECONDS: Default delay between requests
  - OUTPUT_DIRECTORY: Path for JSON files
  - LLM_API_KEY: API key for Pydantic AI model

SITE TEMPLATE INTEGRATION:
  - Output JSON must match ProductCard schema exactly
  - JSON files placed where Vercel sites can read them
  - Image URLs must be publicly accessible GCS URLs
  - File naming convention: {site-name}-products.json

CRON SCHEDULING:
  - Daily runs: 0 2 * * * /path/to/scraper/main.py --site all
  - Manual refresh: /path/to/scraper/main.py --site site-name --force-refresh
```

## Validation Loop

### Level 1: Syntax & Style
```bash
# Run these FIRST - fix any errors before proceeding
ruff check . --fix              # Auto-fix style issues
mypy .                          # Type checking

# Expected: No errors. If errors, READ and fix.
```

### Level 2: Unit Tests
```python
# test_scraper_agent.py
async def test_agent_scrapes_amazon_products():
    """Test agent can extract valid Amazon products."""
    deps = AgentDependencies(
        gcs_credentials_path="test_creds.json",
        scraping_delay_seconds=0.1  # Fast for testing
    )
    
    result = await scraper_agent.run(
        "Scrape 5 products from Amazon camping gear URL",
        deps=deps
    )
    
    assert len(result.data) > 0
    assert all(p.platform == AffiliateNetwork.AMAZON for p in result.data)
    assert all(p.validation_score >= 0.7 for p in result.data)

async def test_agent_handles_failed_scrape_gracefully():
    """Test agent preserves last good data on failures."""
    # Mock a failing URL
    result = await scraper_agent.run(
        "Scrape from invalid URL: https://fake-site.com",
        deps=test_deps
    )
    
    # Should return last good data, not crash
    assert result.data is not None
    assert "using last good data" in result.message.lower()

# test_tools.py
async def test_image_processor_uploads_to_gcs():
    """Test image processing and GCS upload."""
    product = ScrapedProduct(
        title="Test Product",
        price="$19.99", 
        affiliate_url="https://example.com",
        original_image_url="https://example.com/image.jpg",
        category="test",
        platform=AffiliateNetwork.AMAZON,
        validation_score=0.8
    )
    
    processed = await process_product_images(test_ctx, [product])
    
    assert processed[0].processed_image_url is not None
    assert "storage.googleapis.com" in str(processed[0].processed_image_url)
```

```bash
# Run tests iteratively until passing:
pytest tests/ -v --asyncio-mode=auto

# If failing: Debug specific test, fix code, re-run
```

### Level 3: Integration Test
```bash
# Test on GCP VM via browser SSH
cd /home/ubuntu/scraper
python main.py --site outdoor-gear-site --test-run

# Expected output:
# ✅ Loaded site config: outdoor-gear-site.json
# ✅ Scraped 15 products from Amazon
# ✅ Scraped 12 products from Rakuten  
# ✅ Processed 27 images and uploaded to GCS
# ✅ Generated outdoor-gear-site-products.json
# 📊 Quality score: 0.85 (23/27 products passed validation)

# Verify JSON output matches ProductCard schema
python -c "
import json
from agents.models import ProductCard
data = json.load(open('output/outdoor-gear-site-products.json'))
products = [ProductCard(**p) for p in data]
print(f'✅ All {len(products)} products valid')
"
```

## Final Validation Checklist
- [ ] All tests pass: `pytest tests/ -v --asyncio-mode=auto`
- [ ] No linting errors: `ruff check .`
- [ ] No type errors: `mypy .`
- [ ] Agent successfully scrapes Amazon, Rakuten, and CJ products
- [ ] Images are uploaded to GCS and made public
- [ ] Output JSON exactly matches site template ProductCard schema
- [ ] System preserves last good data on scraping failures
- [ ] Setup script works on clean Ubuntu 22.04 VM
- [ ] Cron scheduling works with manual refresh option
- [ ] Rate limiting prevents detection/blocking

---

## Anti-Patterns to Avoid
- ❌ Don't hardcode selectors - use platform-specific modules
- ❌ Don't skip data validation - broken sites are worse than missing data
- ❌ Don't use sync functions in async agent context  
- ❌ Don't ignore rate limiting - slow and steady wins
- ❌ Don't commit credentials or API keys
- ❌ Don't assume all scraped data is valid - validate everything
- ❌ Don't let one site failure break others - isolate failures

## Confidence Score: 9/10

High confidence due to:
- Clear examples from site template to match exactly
- Well-documented external APIs and libraries
- Established patterns for Pydantic AI agents and tools
- Comprehensive validation gates for quality assurance
- Modular architecture for easy scaling to new sites

Minor uncertainty on GCP VM browser automation setup, but documentation provides clear guidance for headful Playwright on VMs.