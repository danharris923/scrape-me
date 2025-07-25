"""
Core data structures for the affiliate scraper engine.

This module defines all Pydantic models used across the system for data validation,
serialization, and type safety. All models must maintain compatibility with the
site template's ProductSchema.
"""

from pydantic import BaseModel, Field, HttpUrl
from typing import List, Optional, Dict
from datetime import datetime
from enum import Enum
import re


class AffiliateNetwork(str, Enum):
    """Supported affiliate networks."""
    AMAZON = "amazon"
    RAKUTEN = "rakuten"
    CJ = "cj"


class ProductCard(BaseModel):
    """
    Product data structure - MUST match site template exactly.
    
    This schema is consumed directly by the Vercel-hosted affiliate sites
    and must remain compatible with the React ProductCard components.
    """
    title: str
    price: str
    affiliate_url: HttpUrl
    image_url: HttpUrl
    slug: str


class ScrapedProduct(BaseModel):
    """
    Internal scraping result with additional metadata for processing.
    
    This model includes validation, quality scoring, and processing metadata
    that gets filtered out before final output to ProductCard format.
    """
    title: str = Field(..., min_length=1, max_length=200)
    price: str = Field(..., description="Original price string from site")
    affiliate_url: HttpUrl
    original_image_url: HttpUrl = Field(..., description="Source image URL")
    processed_image_url: Optional[HttpUrl] = None
    category: str = Field(..., min_length=1)
    platform: AffiliateNetwork
    scraped_at: datetime = Field(default_factory=datetime.now)
    validation_score: float = Field(..., ge=0.0, le=1.0)
    
    def to_product_card(self) -> ProductCard:
        """Convert to ProductCard format for final output."""
        # Generate SEO-friendly slug
        slug = self._generate_slug(self.title)
        
        return ProductCard(
            title=self.title,
            price=self.price,
            affiliate_url=self.affiliate_url,
            image_url=self.processed_image_url or self.original_image_url,
            slug=slug
        )
    
    def _generate_slug(self, title: str) -> str:
        """Generate SEO-friendly slug from product title."""
        # Convert to lowercase and replace spaces/special chars with hyphens
        slug = re.sub(r'[^\w\s-]', '', title.lower())
        slug = re.sub(r'[-\s]+', '-', slug)
        
        # Limit length and remove trailing hyphens
        return slug[:50].strip('-')
    
    def calculate_quality_score(self) -> float:
        """
        Calculate product quality score based on data completeness and validity.
        
        Returns:
            float: Quality score between 0.0 and 1.0
        """
        score = 0.0
        
        # Title quality (30% of score)
        if self.title and len(self.title.strip()) >= 10:
            score += 0.3
        elif self.title and len(self.title.strip()) >= 5:
            score += 0.15
            
        # Price validity (25% of score)
        if self.price and any(char.isdigit() for char in self.price):
            score += 0.25
            
        # URL validity (25% of score) 
        if self.affiliate_url and str(self.affiliate_url).startswith(('http://', 'https://')):
            score += 0.25
            
        # Image URL validity (20% of score)
        if (self.processed_image_url or self.original_image_url) and \
           str(self.processed_image_url or self.original_image_url).startswith(('http://', 'https://')):
            score += 0.2
            
        return round(score, 2)


class URLConfig(BaseModel):
    """Configuration for a specific URL to scrape."""
    url: HttpUrl
    platform: AffiliateNetwork
    category: str
    expected_count: int = Field(default=10, ge=1, le=100)
    custom_selectors: Optional[Dict[str, str]] = None


class SiteConfig(BaseModel):
    """Configuration for each affiliate site."""
    site_name: str = Field(..., min_length=1)
    output_path: str = Field(..., description="Path to write JSON file") 
    gcs_bucket: str = Field(..., description="GCS bucket for images")
    image_folder: str = Field(default="products", description="Folder in bucket")
    urls_to_scrape: List[URLConfig] = Field(description="URLs and metadata", min_length=1)
    refresh_interval_hours: int = Field(default=24, ge=1, le=168)  # Max 1 week
    last_scraped: Optional[datetime] = None
    
    def needs_refresh(self) -> bool:
        """Check if site needs refreshing based on interval."""
        if not self.last_scraped:
            return True
            
        time_since_scrape = datetime.now() - self.last_scraped
        return time_since_scrape.total_seconds() > (self.refresh_interval_hours * 3600)


class AgentDependencies(BaseModel):
    """Dependencies injected into the Pydantic AI agent."""
    gcs_credentials_path: str = Field(..., description="Path to GCS service account JSON")
    output_directory: str = Field(default="./output")
    state_directory: str = Field(default="./state")
    scraping_delay_seconds: float = Field(default=2.0, ge=0.5, le=10.0)
    max_retries: int = Field(default=3, ge=1, le=10)
    quality_threshold: float = Field(default=0.7, ge=0.0, le=1.0)
    

class ScrapingResult(BaseModel):
    """Result of a scraping operation."""
    site_name: str
    total_products_found: int
    valid_products: int
    failed_products: int
    processing_time_seconds: float
    quality_score: float
    output_file_path: str
    timestamp: datetime = Field(default_factory=datetime.now)
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate of scraping operation."""
        if self.total_products_found == 0:
            return 0.0
        return round(self.valid_products / self.total_products_found, 2)


class StateData(BaseModel):
    """State persistence model for graceful error recovery."""
    site_name: str
    last_successful_scrape: datetime
    last_products: List[ProductCard]
    last_result: ScrapingResult
    consecutive_failures: int = 0
    
    def should_use_cached_data(self, max_failures: int = 3) -> bool:
        """Determine if cached data should be used due to consecutive failures."""
        return self.consecutive_failures >= max_failures