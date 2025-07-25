# 🏷️ Affiliate Tags Management Guide

**How to add new affiliate tags and ensure the right tag appears on the right product links**

---

## 🎯 **Quick Overview**

Your scraper generates affiliate links with tags like `?tag=offgriddisc-20`. When you get new affiliate accounts (Amazon Associates, different niches, etc.), you need to:

1. **Add the new tag** to your scraper configuration
2. **Map tags to product categories** or sites
3. **Test that links generate correctly**
4. **Verify on your live site**

---

## 📋 **Current Setup**

### **Where tags are configured:**

**File**: `simple_scraper.py` (line 106)
```python
affiliate_tag = "offgriddisc-20"  # Your current affiliate tag
```

**Generated URL format**:
```
https://www.amazon.com/dp/B0123456?tag=YOUR_TAG_HERE
```

---

## 🔧 **Method 1: Single Tag Per Category**

### **Step 1: Update simple_scraper.py**

Replace the hardcoded tag with category-based mapping:

```python
# Affiliate tag mapping by category
AFFILIATE_TAGS = {
    "outdoor-gear": "offgriddisc-20",
    "camping-tents": "offgriddisc-20", 
    "hiking-backpacks": "trailblaze-20",
    "smartphone-accessories": "techdeals-20",
    "wireless-headphones": "techdeals-20"
}

# Default fallback tag
DEFAULT_AFFILIATE_TAG = "offgriddisc-20"
```

### **Step 2: Update the generate_product_data function**

Find this section (around line 104-106):
```python
# OLD CODE:
asin = f"B0{random.randint(100000, 999999):06d}"
affiliate_tag = "offgriddisc-20"  # Your affiliate tag
```

Replace with:
```python
# NEW CODE:
asin = f"B0{random.randint(100000, 999999):06d}"
affiliate_tag = AFFILIATE_TAGS.get(template["category"], DEFAULT_AFFILIATE_TAG)
```

---

## 🔧 **Method 2: Multiple Tags Per Site**

### **Step 1: Create site-based tag mapping**

```python
# Affiliate tag mapping by site
SITE_AFFILIATE_TAGS = {
    "outdoor-gear-site": {
        "primary": "offgriddisc-20",
        "backup": "outdoordeals-20"
    },
    "tech-deals-site": {
        "primary": "techdeals-20", 
        "backup": "gadgetguru-20"
    }
}
```

### **Step 2: Update scrape_site function**

Add site parameter to generate_product_data:
```python
# In scrape_site function (around line 149):
product = generate_product_data(template_copy, site_type, site_name)
```

### **Step 3: Update generate_product_data**

```python
def generate_product_data(template: Dict[str, Any], site_type: str, site_name: str = None) -> Dict[str, Any]:
    # ... existing code ...
    
    # Get affiliate tag for this site
    site_tags = SITE_AFFILIATE_TAGS.get(site_name, {})
    affiliate_tag = site_tags.get("primary", DEFAULT_AFFILIATE_TAG)
    
    # ... rest of function ...
```

---

## 🔧 **Method 3: Brand-Specific Tags** 

### **For when you have different affiliate programs per brand:**

```python
# Brand-specific affiliate tags
BRAND_AFFILIATE_TAGS = {
    "Coleman": "camping-20",
    "Osprey": "hiking-20", 
    "MSR": "outdoorgear-20",
    "Apple": "techdeals-20",
    "Samsung": "smartphones-20",
    "Sony": "audiotech-20"
}
```

Update generate_product_data:
```python
# Get tag by brand first, then category, then default
affiliate_tag = (
    BRAND_AFFILIATE_TAGS.get(template["brand"]) or 
    AFFILIATE_TAGS.get(template["category"]) or 
    DEFAULT_AFFILIATE_TAG
)
```

---

## ✅ **Testing Your Tags**

### **Step 1: Test the scraper**
```bash
# Run scraper
python3 simple_scraper.py

# Check generated data
cat output/outdoor-gear-site-products.json | grep "affiliate_url" | head -5
```

### **Step 2: Verify tag mapping**
```bash
# Check outdoor products have outdoor tags
cat output/outdoor-gear-site-products.json | jq '.products[].affiliate_url' | grep "offgriddisc-20"

# Check tech products have tech tags  
cat output/tech-deals-site-products.json | jq '.products[].affiliate_url' | grep "techdeals-20"
```

### **Step 3: Test API response**
```bash
# Test your API
curl http://localhost:8000/products | jq '.data[0].affiliate_url'
```

### **Step 4: Check live website**
1. Visit your Vercel site
2. Right-click on product links → "Copy link address"
3. Verify the `?tag=` parameter is correct

---

## 🔄 **Adding New Tags - Step by Step**

### **When you get a new affiliate account:**

1. **Add to configuration** (choose your method above):
   ```python
   AFFILIATE_TAGS = {
       "outdoor-gear": "offgriddisc-20",
       "new-category": "yournewag-20"  # ← Add this
   }
   ```

2. **Test locally**:
   ```bash
   python3 simple_scraper.py
   grep "yournewag-20" output/*.json
   ```

3. **Deploy to GCP**:
   ```bash
   # Upload updated scraper
   scp simple_scraper.py your-vm:~/scrape-me/
   
   # SSH to VM and restart
   ssh your-vm
   cd ~/scrape-me
   python3 simple_scraper.py
   sudo systemctl restart scraper-api
   ```

4. **Test live API**:
   ```bash
   curl http://YOUR_VM_IP:8000/products | grep "yournewag-20"
   ```

5. **Check your website** - Links should now have the new tag

---

## 🚨 **Tag Validation Script**

Create this script to validate all your tags:

**File**: `validate_tags.py`
```python
#!/usr/bin/env python3
import json
from pathlib import Path
from collections import defaultdict

def validate_affiliate_tags():
    """Check all products have correct affiliate tags."""
    
    output_dir = Path("./output")
    tag_counts = defaultdict(int)
    issues = []
    
    for json_file in output_dir.glob("*-products.json"):
        with open(json_file) as f:
            data = json.load(f)
            
        site_name = data["site"]
        print(f"\n📁 Checking {site_name}...")
        
        for product in data["products"]:
            url = product["affiliate_url"]
            
            # Extract tag from URL
            if "?tag=" in url:
                tag = url.split("?tag=")[1].split("&")[0]
                tag_counts[tag] += 1
                print(f"  ✅ {product['title'][:30]}... → {tag}")
            else:
                issues.append(f"❌ Missing tag: {product['title']}")
    
    print(f"\n📊 Tag Summary:")
    for tag, count in tag_counts.items():
        print(f"  {tag}: {count} products")
    
    if issues:
        print(f"\n🚨 Issues found:")
        for issue in issues:
            print(f"  {issue}")
    else:
        print(f"\n✅ All products have affiliate tags!")

if __name__ == "__main__":
    validate_affiliate_tags()
```

**Run validation**:
```bash
python3 validate_tags.py
```

---

## 💰 **Tag Revenue Tracking**

### **Track which tags perform best:**

Add this to your scraper output:
```python
# In generate_product_data function, add:
"affiliate_info": {
    "tag": affiliate_tag,
    "category": template["category"],
    "brand": template["brand"],
    "commission_rate": "3-8%"  # Update based on your rates
}
```

### **Export for analysis:**
```bash
# Get all affiliate tags used
curl http://YOUR_IP:8000/products | jq '.data[].affiliate_info.tag' | sort | uniq -c
```

---

## 🎯 **Best Practices**

1. **Use descriptive tag names**: `outdoorgear-20` not `xyz123-20`
2. **Keep a mapping spreadsheet**: Tag → Niche → Commission Rate
3. **Test new tags immediately** before going live
4. **Monitor click-through rates** per tag in Amazon Associates
5. **Use different tags for different traffic sources** if allowed
6. **Keep backup tags** in case primary ones get suspended

---

## 🔧 **Quick Commands Reference**

```bash
# Test scraper with new tags
python3 simple_scraper.py && python3 validate_tags.py

# Deploy to production
scp simple_scraper.py your-vm:~/scrape-me/
ssh your-vm "cd ~/scrape-me && python3 simple_scraper.py && sudo systemctl restart scraper-api"

# Verify live tags
curl http://YOUR_IP:8000/products | jq '.data[].affiliate_url' | head -10
```

---

**🎉 Your affiliate tag system is now scalable and trackable!**

Each new niche gets its proper tag automatically, and you can track performance by category, brand, or site.