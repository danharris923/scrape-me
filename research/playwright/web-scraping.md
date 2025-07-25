# Playwright Python Web Scraping Documentation

## Installation
```bash
pip install playwright
playwright install chromium  # or firefox, webkit
```

## Basic Usage
```python
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)  # headless=False for debugging
    page = browser.new_page()
    page.goto("https://example.com")
    
    # Take screenshot
    page.screenshot(path="screenshot.png")
    
    # Extract data
    title = page.title()
    
    browser.close()
```

## Locators and Element Selection
```python
# Role-based (recommended)
page.get_by_role("button", name="Sign in").click()

# Text-based
page.get_by_text("Welcome").is_visible()

# CSS selector
page.locator(".product-card").all()

# Filter and chain
product = page.get_by_role("listitem").filter(has_text="Product Name")
```

## Data Extraction
```python
# Get text content
text = element.text_content()
inner_text = element.inner_text()

# Get all text from multiple elements
texts = page.locator(".product-title").all_text_contents()

# Get attribute
href = element.get_attribute("href")
src = element.get_attribute("src")

# Handle multiple elements
products = page.locator(".product-card").all()
for product in products:
    title = product.locator(".title").text_content()
    price = product.locator(".price").text_content()
    link = product.locator("a").get_attribute("href")
```

## Waiting and Navigation
```python
# Auto-wait is built-in
page.wait_for_load_state("networkidle")  # Wait for network
page.wait_for_selector(".product-list")  # Wait for element

# Manual wait (avoid if possible)
page.wait_for_timeout(1000)  # milliseconds
```

## Key Features for Scraping
- Headful mode for debugging
- Auto-waiting for elements
- Network interception
- JavaScript execution
- Screenshot capabilities
- Mobile emulation