"""
API server for serving scraped product data to websites.
Runs alongside the scraper to provide real-time access to product data.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import json
import os
from pathlib import Path
from typing import List, Dict, Any
import uvicorn

app = FastAPI(title="Affiliate Scraper API", version="1.0.0")

# Configure CORS for your Vercel sites
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://scale-me-testsite.vercel.app",
        "https://scale-me.vercel.app",
        "http://localhost:3000",
        "http://localhost:3001",
        "*"  # Allow all origins in development
    ],
    allow_credentials=True,
    allow_methods=["GET"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """API root endpoint with documentation."""
    return {
        "message": "Affiliate Scraper API",
        "endpoints": {
            "/products": "Get all products from all sites",
            "/products/{site_name}": "Get products from specific site",
            "/sites": "List all available sites",
            "/health": "Check API health status"
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "affiliate-scraper-api"}


@app.get("/sites")
async def get_sites():
    """List all available sites with scraped data."""
    output_dir = Path("./output")
    sites = []
    
    if output_dir.exists():
        for json_file in output_dir.glob("*.json"):
            site_name = json_file.stem.replace("-products", "")
            sites.append({
                "name": site_name,
                "file": json_file.name,
                "last_updated": os.path.getmtime(json_file)
            })
    
    return {"sites": sites, "count": len(sites)}


@app.get("/products")
async def get_all_products():
    """Get all products from all sites."""
    output_dir = Path("./output")
    all_products = []
    
    if not output_dir.exists():
        return {"success": True, "data": [], "count": 0}
    
    for json_file in output_dir.glob("*.json"):
        try:
            with open(json_file, 'r') as f:
                data = json.load(f)
                if isinstance(data, dict) and 'products' in data:
                    all_products.extend(data['products'])
                elif isinstance(data, list):
                    all_products.extend(data)
        except Exception as e:
            print(f"Error reading {json_file}: {e}")
    
    return {
        "success": True,
        "data": all_products,
        "count": len(all_products)
    }


@app.get("/products/{site_name}")
async def get_site_products(site_name: str):
    """Get products from a specific site."""
    json_path = Path(f"./output/{site_name}-products.json")
    
    if not json_path.exists():
        # Try without -products suffix
        json_path = Path(f"./output/{site_name}.json")
        
    if not json_path.exists():
        raise HTTPException(status_code=404, detail=f"No data found for site: {site_name}")
    
    try:
        with open(json_path, 'r') as f:
            data = json.load(f)
            
        products = []
        if isinstance(data, dict) and 'products' in data:
            products = data['products']
        elif isinstance(data, list):
            products = data
            
        return {
            "success": True,
            "site": site_name,
            "data": products,
            "count": len(products),
            "last_updated": os.path.getmtime(json_path)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading data: {str(e)}")


if __name__ == "__main__":
    # Run the API server
    print("Starting Affiliate Scraper API on http://0.0.0.0:8000")
    print("API will serve data from ./output directory")
    uvicorn.run(app, host="0.0.0.0", port=8000)