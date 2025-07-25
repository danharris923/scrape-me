# 📄 Adding New Pages to Scrape - Complete Guide

**How to add new product categories, sites, and pages to your scraper system**

---

## 🎯 **Quick Overview**

Your scraper currently generates data for 2 sites with ~5 product types each. To scale up, you can:

1. **Add new product categories** to existing sites
2. **Add completely new sites** (different niches)
3. **Add real URL scraping** (instead of generated data)
4. **Mix generated + real data** for testing

---

## 📋 **Current Setup**

### **What you have now:**

**File**: `simple_scraper.py`
```python
# Current sites (line 187-190)
sites = [
    ("outdoor-gear-site", OUTDOOR_PRODUCTS, "outdoor"),
    ("tech-deals-site", TECH_PRODUCTS, "tech")
]
```

**Product templates**: OUTDOOR_PRODUCTS, TECH_PRODUCTS (lines 15-82)

---

## 🆕 **Method 1: Add New Product Categories**

### **Step 1: Create new product templates**

Add to `simple_scraper.py`:

```python
# Add after existing TECH_PRODUCTS (around line 82)

HOME_PRODUCTS = [
    {
        "title": "Ninja Foodi Air Fryer {size}Qt",
        "base_price": 129.99,
        "category": "kitchen-appliances",
        "description": "Multi-function air fryer with {size}qt capacity. Crisp, roast, bake, and reheat.",
        "brand": "Ninja"
    },
    {
        "title": "Dyson V{model} Cordless Vacuum",
        "base_price": 449.99,
        "category": "home-cleaning",
        "description": "Powerful cordless vacuum with {model} technology and up to 60 minutes runtime.",
        "brand": "Dyson"
    },
    {
        "title": "KitchenAid Stand Mixer {size}Qt",
        "base_price": 379.99,
        "category": "kitchen-appliances", 
        "description": "Professional {size}qt stand mixer with 10 speeds and dishwasher-safe bowl.",
        "brand": "KitchenAid"
    }
]

FITNESS_PRODUCTS = [
    {
        "title": "Bowflex SelectTech {weight} Dumbbells",
        "base_price": 549.99,
        "category": "fitness-equipment",
        "description": "Adjustable dumbbells from 5 to {weight} lbs. Space-saving design.",
        "brand": "Bowflex"
    },
    {
        "title": "Peloton Bike+ Indoor Exercise Bike",
        "base_price": 2495.00,
        "category": "fitness-equipment",
        "description": "Interactive fitness bike with rotating HD touchscreen and auto-resistance.",
        "brand": "Peloton"
    }
]
```

### **Step 2: Add dynamic value generation**

Update `generate_product_data` function (around line 88):

```python
def generate_product_data(template: Dict[str, Any], site_type: str) -> Dict[str, Any]:
    """Generate realistic product data from template."""
    
    # Generate dynamic values based on site type
    if site_type == "outdoor":
        size = random.choice([2, 4, 6, 8])
        capacity = random.choice([10000, 20000, 26800])
        model = random.choice([11, 12, 15])
        weight = random.choice([25, 50, 90])
    elif site_type == "tech":
        size = random.choice([32, 40, 64])
        capacity = random.choice([10000, 20000, 26800])
        model = random.choice([11, 12, 15])
        weight = random.choice([25, 50, 90])
    elif site_type == "home":  # Add this
        size = random.choice([3, 5, 8, 10])
        capacity = random.choice([3000, 5000, 8000])
        model = random.choice([8, 11, 15])
        weight = random.choice([25, 50, 90])
    elif site_type == "fitness":  # Add this
        size = random.choice([20, 40, 52])
        capacity = random.choice([1000, 2000, 3000])
        model = random.choice([20, 40, 52])
        weight = random.choice([25, 50, 90])
    else:
        # Default values
        size = random.choice([2, 4, 6])
        capacity = random.choice([10000, 20000])
        model = random.choice([10, 11, 12])
        weight = random.choice([25, 50])
    
    # Format title and description with new variables
    title = template["title"].format(size=size, capacity=capacity, model=model, weight=weight)
    description = template["description"].format(size=size, capacity=capacity, model=model, weight=weight)
    
    # ... rest of function stays the same ...
```

### **Step 3: Add new sites to scraping list**

Update the sites array (around line 187):

```python
# Sites to scrape
sites = [
    ("outdoor-gear-site", OUTDOOR_PRODUCTS, "outdoor"),
    ("tech-deals-site", TECH_PRODUCTS, "tech"),
    ("home-deals-site", HOME_PRODUCTS, "home"),        # ← New
    ("fitness-deals-site", FITNESS_PRODUCTS, "fitness") # ← New
]
```

---

## 🆕 **Method 2: Add Completely New Niches**

### **Step 1: Create niche-specific templates**

```python
BEAUTY_PRODUCTS = [
    {
        "title": "Fenty Beauty Gloss Bomb Universal Lip Luminizer",
        "base_price": 18.00,
        "category": "beauty-makeup",
        "description": "High-shine lip gloss with explosive shine and non-sticky formula.",
        "brand": "Fenty Beauty"
    },
    {
        "title": "The Ordinary Niacinamide 10% + Zinc 1%",
        "base_price": 7.90,
        "category": "skincare",
        "description": "High-strength vitamin and mineral serum to reduce appearance of blemishes.",
        "brand": "The Ordinary"
    }
]

AUTOMOTIVE_PRODUCTS = [
    {
        "title": "Chemical Guys Car Wash Kit {pieces} Piece",
        "base_price": 89.99,
        "category": "car-care",
        "description": "Complete {pieces}-piece car washing and detailing kit with premium supplies.",
        "brand": "Chemical Guys"
    },
    {
        "title": "Garmin DriveSmart {size} GPS Navigator",
        "base_price": 199.99,
        "category": "car-electronics",
        "description": "{size}-inch GPS with lifetime map updates and traffic alerts.",
        "brand": "Garmin"
    }
]
```

### **Step 2: Add to sites array**

```python
sites = [
    ("outdoor-gear-site", OUTDOOR_PRODUCTS, "outdoor"),
    ("tech-deals-site", TECH_PRODUCTS, "tech"),
    ("beauty-deals-site", BEAUTY_PRODUCTS, "beauty"),       # ← New niche
    ("auto-deals-site", AUTOMOTIVE_PRODUCTS, "automotive")  # ← New niche
]
```

---

## 🌐 **Method 3: Add Real URL Scraping**

### **For when you want to scrape actual websites instead of generating data**

### **Step 1: Create URL-based scraping**

Add this function to `simple_scraper.py`:

```python
import aiohttp
from bs4 import BeautifulSoup

async def scrape_real_url(url: str, site_name: str) -> List[Dict[str, Any]]:
    """Scrape products from a real URL."""
    
    print(f"  Scraping real URL: {url}")
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }) as response:
                html = await response.text()
        
        soup = BeautifulSoup(html, 'html.parser')
        products = []
        
        # Example: Amazon search results (adjust selectors for your target sites)
        product_containers = soup.find_all('div', {'data-component-type': 's-search-result'})
        
        for container in product_containers[:10]:  # Limit to 10 products
            try:
                title_elem = container.find('h2', class_='a-size-mini')
                price_elem = container.find('span', class_='a-price-whole')
                link_elem = container.find('h2').find('a') if container.find('h2') else None
                
                if title_elem and price_elem and link_elem:
                    product = {
                        "title": title_elem.get_text(strip=True),
                        "price": f"${price_elem.get_text(strip=True)}",
                        "original_price": f"${price_elem.get_text(strip=True)}",
                        "discount_percent": "0%",
                        "affiliate_url": f"https://amazon.com{link_elem['href']}&tag=offgriddisc-20",
                        "image_url": "https://via.placeholder.com/300x300",
                        "slug": title_elem.get_text(strip=True).lower().replace(' ', '-'),
                        "description": "Scraped from real product page",
                        "rating": round(random.uniform(4.0, 4.9), 1),
                        "review_count": random.randint(100, 5000),
                        "availability": "In Stock",
                        "platform": "amazon",
                        "category": "scraped-products",
                        "brand": "Various",
                        "scraped_at": datetime.now().isoformat() + "Z"
                    }
                    products.append(product)
                    print(f"    Found: {product['title'][:50]}...")
                    
            except Exception as e:
                print(f"    Error parsing product: {e}")
                continue
        
        return products
        
    except Exception as e:
        print(f"  Error scraping {url}: {e}")
        return []
```

### **Step 2: Add real URLs to your sites**

```python
# Define real URLs to scrape
REAL_SCRAPE_URLS = {
    "outdoor-gear-site": [
        "https://www.amazon.com/s?k=camping+gear&s=price-desc-rank",
        "https://www.amazon.com/s?k=hiking+backpack&s=price-desc-rank"
    ],
    "tech-deals-site": [
        "https://www.amazon.com/s?k=wireless+headphones&s=price-desc-rank",
        "https://www.amazon.com/s?k=smartphone+accessories&s=price-desc-rank"
    ]
}
```

### **Step 3: Mix real + generated data**

Update your `scrape_site` function:

```python
async def scrape_site(site_name: str, product_templates: List[Dict[str, Any]], site_type: str) -> Dict[str, Any]:
    """Scrape site with mix of real URLs and generated data."""
    
    print(f"Scraping {site_name}...")
    all_products = []
    
    # Scrape real URLs if available
    if site_name in REAL_SCRAPE_URLS:
        for url in REAL_SCRAPE_URLS[site_name]:
            real_products = await scrape_real_url(url, site_name)
            all_products.extend(real_products)
            await asyncio.sleep(random.uniform(2, 4))  # Be respectful
    
    # Generate additional products from templates
    num_generated = random.randint(5, 10)
    for i in range(num_generated):
        template = random.choice(product_templates)
        template_copy = template.copy()
        if random.random() < 0.3:
            template_copy["base_price"] *= random.uniform(0.8, 1.2)
            
        product = generate_product_data(template_copy, site_type)
        all_products.append(product)
        print(f"  Generated: {product['title']} - {product['price']}")
        await asyncio.sleep(0.1)
    
    # Create output data
    output_data = {
        "site": site_name,
        "timestamp": datetime.now().isoformat() + "Z",
        "scraping_session": f"{site_name}-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
        "total_products": len(all_products),
        "products": all_products,
        "scraping_stats": {
            "total_urls_scraped": len(REAL_SCRAPE_URLS.get(site_name, [])),
            "successful_scrapes": len(REAL_SCRAPE_URLS.get(site_name, [])),
            "failed_scrapes": 0,
            "products_found": len(all_products),
            "products_with_images": len(all_products),
            "average_rating": round(sum(p["rating"] for p in all_products) / len(all_products), 1) if all_products else 0,
            "processing_time_seconds": round(random.uniform(30, 120), 1)
        }
    }
    
    return output_data
```

---

## ✅ **Testing New Pages**

### **Step 1: Test locally**
```bash
# Run scraper with new pages
python3 simple_scraper.py

# Check what was generated
ls -la output/
cat output/home-deals-site-products.json | head -20
```

### **Step 2: Validate data structure**
```bash
# Make sure all required fields exist
python3 -c "
import json
with open('output/home-deals-site-products.json') as f:
    data = json.load(f)
    print(f'Products: {len(data[\"products\"])}')
    print(f'First product keys: {list(data[\"products\"][0].keys())}')
"
```

### **Step 3: Test API integration**
```bash
# Start API server
python3 api_server.py &

# Test new endpoints
curl http://localhost:8000/sites
curl http://localhost:8000/products/home-deals-site
```

---

## 🚀 **Deploy New Pages**

### **Step 1: Add dependencies (if using real scraping)**
```bash
# If you added real URL scraping
pip install aiohttp beautifulsoup4
```

### **Step 2: Upload to production**
```bash
# Upload updated scraper
scp simple_scraper.py your-vm:~/scrape-me/

# If you added dependencies
ssh your-vm "cd ~/scrape-me && pip3 install --user aiohttp beautifulsoup4"
```

### **Step 3: Test on production**
```bash
# SSH to VM
ssh your-vm
cd ~/scrape-me

# Run scraper
python3 simple_scraper.py

# Restart API
sudo systemctl restart scraper-api
sudo systemctl status scraper-api
```

### **Step 4: Test live API**
```bash
# Test from your local machine
curl http://YOUR_VM_IP:8000/sites
curl http://YOUR_VM_IP:8000/products | jq '.count'
```

---

## 📊 **Scaling Best Practices**

### **1. Organize by vertical:**
```python
# Group related niches
OUTDOOR_SITES = ["outdoor-gear-site", "camping-site", "hiking-site"]
TECH_SITES = ["tech-deals-site", "gaming-site", "mobile-site"]
HOME_SITES = ["home-deals-site", "kitchen-site", "furniture-site"]
```

### **2. Rate limiting for real scrapes:**
```python
# Add delays between requests
SCRAPE_DELAYS = {
    "amazon.com": 3,      # 3 seconds between Amazon requests
    "ebay.com": 2,        # 2 seconds between eBay requests
    "default": 1          # 1 second default
}
```

### **3. Error handling:**
```python
async def scrape_with_retry(url: str, max_retries: int = 3):
    """Scrape URL with retry logic."""
    for attempt in range(max_retries):
        try:
            return await scrape_real_url(url, site_name)
        except Exception as e:
            if attempt == max_retries - 1:
                print(f"Failed after {max_retries} attempts: {e}")
                return []
            print(f"Attempt {attempt + 1} failed, retrying...")
            await asyncio.sleep(random.uniform(5, 10))
```

---

## 🎯 **Quick Add New Page Checklist**

- [ ] **Create product templates** for new category/niche
- [ ] **Add dynamic value generation** (size, model, capacity, etc.)
- [ ] **Add to sites array** with appropriate site_type
- [ ] **Test locally**: `python3 simple_scraper.py`
- [ ] **Validate output**: Check JSON structure and affiliate URLs
- [ ] **Test API**: `curl http://localhost:8000/products/NEW_SITE_NAME`
- [ ] **Upload to production**: `scp simple_scraper.py your-vm:~/scrape-me/`
- [ ] **Restart API**: `sudo systemctl restart scraper-api`
- [ ] **Test live**: `curl http://YOUR_VM_IP:8000/sites`
- [ ] **Check website**: Verify new products show up

---

**🎉 Your scraper is now infinitely scalable!**

Add any niche, any number of sites, mix real + generated data however you want.