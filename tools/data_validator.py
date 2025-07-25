"""
Data validation and quality scoring tools for scraped products.

This module provides tools for the Pydantic AI agent to validate, score,
and filter product data to ensure only high-quality products are output.
"""

from typing import List, Dict, Any, Optional
import re
import logging
from urllib.parse import urlparse
from datetime import datetime

from pydantic import ValidationError
from pydantic_ai import RunContext

from agents.models import ScrapedProduct, ProductCard, AgentDependencies

logger = logging.getLogger(__name__)


class DataValidationError(Exception):
    """Exception raised when data validation fails."""
    pass


async def validate_and_score_products(
    ctx: RunContext[AgentDependencies],
    products: List[ScrapedProduct],
    min_quality_score: Optional[float] = None
) -> List[ScrapedProduct]:
    """
    Validate and score a list of scraped products.
    
    This tool performs comprehensive validation and quality scoring on
    scraped products, filtering out low-quality items.
    
    Args:
        ctx: Pydantic AI run context with dependencies
        products: List of ScrapedProduct objects to validate
        min_quality_score: Minimum quality score (overrides default)
        
    Returns:
        List of validated products that meet quality standards
    """
    if not products:
        return []
    
    quality_threshold = min_quality_score or ctx.deps.quality_threshold
    
    logger.info(f"Validating {len(products)} products with quality threshold {quality_threshold}")
    
    validated_products = []
    validation_stats = {
        "total": len(products),
        "passed_basic": 0,
        "passed_quality": 0,
        "failed_basic": 0,
        "failed_quality": 0
    }
    
    for product in products:
        try:
            # Perform basic validation
            if not _basic_validation(product):
                validation_stats["failed_basic"] += 1
                logger.debug(f"Basic validation failed for: {product.title[:50]}")
                continue
            
            validation_stats["passed_basic"] += 1
            
            # Calculate comprehensive quality score
            quality_score = _calculate_comprehensive_quality_score(product)
            product.validation_score = quality_score
            
            # Check quality threshold
            if quality_score >= quality_threshold:
                validation_stats["passed_quality"] += 1
                validated_products.append(product)
            else:
                validation_stats["failed_quality"] += 1
                logger.debug(f"Quality score {quality_score:.2f} below threshold for: {product.title[:50]}")
                
        except Exception as e:
            validation_stats["failed_basic"] += 1
            logger.warning(f"Validation error for product '{product.title[:50]}': {e}")
            continue
    
    logger.info(
        f"Validation complete: {validation_stats['passed_quality']} passed, "
        f"{validation_stats['failed_basic'] + validation_stats['failed_quality']} failed"
    )
    
    return validated_products


def _basic_validation(product: ScrapedProduct) -> bool:
    """Perform basic validation checks on a product."""
    # Title validation
    if not product.title or len(product.title.strip()) < 3:
        return False
    
    if len(product.title) > 500:  # Unreasonably long title
        return False
    
    # Price validation
    if not product.price or not any(c.isdigit() for c in product.price):
        return False
    
    # URL validation
    if not product.affiliate_url or not str(product.affiliate_url).startswith(('http://', 'https://')):
        return False
    
    # Image URL validation
    if not product.original_image_url or not str(product.original_image_url).startswith(('http://', 'https://')):
        return False
    
    # Category validation
    if not product.category or len(product.category.strip()) < 2:
        return False
    
    return True


def _calculate_comprehensive_quality_score(product: ScrapedProduct) -> float:
    """Calculate a comprehensive quality score for a product."""
    score = 0.0
    max_score = 100.0
    
    # Title quality (25 points)
    title_score = _score_title_quality(product.title)
    score += title_score * 0.25
    
    # Price quality (20 points)
    price_score = _score_price_quality(product.price)
    score += price_score * 0.20
    
    # URL quality (20 points)
    url_score = _score_url_quality(str(product.affiliate_url))
    score += url_score * 0.20
    
    # Image quality (15 points)
    image_score = _score_image_url_quality(str(product.original_image_url))
    score += image_score * 0.15
    
    # Category quality (10 points)
    category_score = _score_category_quality(product.category)
    score += category_score * 0.10
    
    # Platform trust (10 points)
    platform_score = _score_platform_trust(product.platform)
    score += platform_score * 0.10
    
    return round(score / max_score, 3)  # Normalize to 0-1 scale


def _score_title_quality(title: str) -> float:
    """Score title quality based on various factors."""
    if not title:
        return 0.0
    
    score = 0.0
    
    # Length scoring (optimal 20-100 characters)
    length = len(title.strip())
    if 20 <= length <= 100:
        score += 40.0
    elif 10 <= length < 20 or 100 < length <= 150:
        score += 25.0
    elif 5 <= length < 10 or 150 < length <= 200:
        score += 15.0
    
    # Content quality checks
    title_lower = title.lower()
    
    # Positive indicators
    if any(brand in title_lower for brand in ['amazon', 'apple', 'samsung', 'nike', 'adidas']):
        score += 10.0  # Brand names
    
    if re.search(r'\b\d+\s*(gb|tb|inch|"|\'|oz|lbs?|kg)\b', title_lower):
        score += 15.0  # Specifications
    
    if any(word in title_lower for word in ['new', 'latest', 'premium', 'professional']):
        score += 10.0  # Quality indicators
    
    # Negative indicators
    if title.count('!') > 2 or title.count('?') > 1:
        score -= 15.0  # Too many exclamations/questions
    
    if len([c for c in title if c.isupper()]) > len(title) * 0.5:
        score -= 10.0  # Too much uppercase
    
    if any(spam_word in title_lower for spam_word in ['free', 'limited time', 'act now', 'buy now']):
        score -= 10.0  # Spammy words
    
    return max(0.0, min(100.0, score))


def _score_price_quality(price: str) -> float:
    """Score price format and validity."""
    if not price:
        return 0.0
    
    score = 0.0
    
    # Has currency symbol
    if '$' in price or '¥' in price or '€' in price or '£' in price:
        score += 30.0
    
    # Proper decimal format
    if re.search(r'\d+\.\d{2}', price):
        score += 25.0  # Has cents
    elif re.search(r'\d+', price):
        score += 15.0  # Has numbers
    
    # Reasonable price range (assuming USD)
    numbers = re.findall(r'[\d.]+', price)
    if numbers:
        try:
            price_value = float(numbers[0])
            if 1.0 <= price_value <= 10000.0:  # Reasonable range
                score += 25.0
            elif 0.01 <= price_value < 1.0 or 10000.0 < price_value <= 50000.0:
                score += 15.0
        except ValueError:
            pass
    
    # Clean formatting
    if not re.search(r'[^\d\.\$\,\s]', price):  # Only digits, dots, dollars, commas, spaces
        score += 20.0
    
    return max(0.0, min(100.0, score))


def _score_url_quality(url: str) -> float:
    """Score URL structure and trustworthiness."""
    if not url:
        return 0.0
    
    try:
        parsed = urlparse(url)
        score = 0.0
        
        # Domain trust
        domain = parsed.netloc.lower()
        trusted_domains = [
            'amazon.com', 'amazon.co.uk', 'amazon.ca', 'amazon.de',
            'rakuten.com', 'walmart.com', 'target.com', 'bestbuy.com',
            'ebay.com', 'etsy.com', 'shopify.com'
        ]
        
        if any(trusted in domain for trusted in trusted_domains):
            score += 40.0
        elif domain.endswith('.com') or domain.endswith('.co.uk'):
            score += 20.0
        
        # HTTPS
        if parsed.scheme == 'https':
            score += 20.0
        
        # URL structure
        if '/dp/' in url or '/product/' in url or '/item/' in url:
            score += 20.0  # Product-specific URL structure
        
        # Not too long or complex
        if len(url) < 200 and url.count('?') <= 2:
            score += 20.0
        
        return max(0.0, min(100.0, score))
        
    except Exception:
        return 10.0  # Some points for having a URL at all


def _score_image_url_quality(image_url: str) -> float:
    """Score image URL quality and format."""
    if not image_url:
        return 0.0
    
    score = 0.0
    image_lower = image_url.lower()
    
    # HTTPS
    if image_url.startswith('https://'):
        score += 25.0
    elif image_url.startswith('http://'):
        score += 10.0
    
    # Image format
    if any(ext in image_lower for ext in ['.jpg', '.jpeg', '.png', '.webp']):
        score += 25.0
    
    # Not a placeholder or broken image
    if not any(placeholder in image_lower for placeholder in ['placeholder', 'no-image', 'missing', 'default']):
        score += 25.0
    
    # Reasonable URL length
    if 20 <= len(image_url) <= 300:
        score += 25.0
    
    return max(0.0, min(100.0, score))


def _score_category_quality(category: str) -> float:
    """Score category relevance and format."""
    if not category:
        return 0.0
    
    score = 0.0
    category_lower = category.lower().strip()
    
    # Reasonable length
    if 3 <= len(category_lower) <= 50:
        score += 40.0
    
    # Proper formatting (no special characters except hyphens)
    if re.match(r'^[a-z0-9\-\s]+$', category_lower):
        score += 30.0
    
    # Common categories
    common_categories = [
        'electronics', 'clothing', 'books', 'home', 'sports', 'toys',
        'automotive', 'health', 'beauty', 'food', 'tools', 'outdoor'
    ]
    if any(cat in category_lower for cat in common_categories):
        score += 30.0
    
    return max(0.0, min(100.0, score))


def _score_platform_trust(platform) -> float:
    """Score platform trustworthiness."""
    platform_scores = {
        'amazon': 100.0,
        'rakuten': 80.0,
        'cj': 70.0,
    }
    
    platform_name = platform.value if hasattr(platform, 'value') else str(platform).lower()
    return platform_scores.get(platform_name, 50.0)


async def convert_to_product_cards(
    ctx: RunContext[AgentDependencies],
    validated_products: List[ScrapedProduct]
) -> List[ProductCard]:
    """
    Convert validated ScrapedProduct objects to ProductCard format.
    
    Args:
        ctx: Pydantic AI run context
        validated_products: List of validated ScrapedProduct objects
        
    Returns:
        List of ProductCard objects ready for output
    """
    if not validated_products:
        return []
    
    logger.info(f"Converting {len(validated_products)} products to ProductCard format")
    
    product_cards = []
    conversion_errors = 0
    
    for product in validated_products:
        try:
            product_card = product.to_product_card()
            
            # Final validation of ProductCard
            try:
                # This will raise ValidationError if invalid
                ProductCard.model_validate(product_card.model_dump())
                product_cards.append(product_card)
            except ValidationError as e:
                logger.warning(f"ProductCard validation failed for '{product.title[:50]}': {e}")
                conversion_errors += 1
                continue
                
        except Exception as e:
            logger.warning(f"Conversion failed for product '{product.title[:50]}': {e}")
            conversion_errors += 1
            continue
    
    logger.info(f"Conversion complete: {len(product_cards)} successful, {conversion_errors} failed")
    
    return product_cards


async def generate_quality_report(
    ctx: RunContext[AgentDependencies],
    products: List[ScrapedProduct]
) -> Dict[str, Any]:
    """
    Generate a quality report for scraped products.
    
    Args:
        ctx: Pydantic AI run context
        products: List of products to analyze
        
    Returns:
        Dictionary with quality statistics and insights
    """
    if not products:
        return {"error": "No products to analyze"}
    
    scores = [p.validation_score for p in products if p.validation_score is not None]
    
    if not scores:
        return {"error": "No quality scores available"}
    
    # Calculate statistics
    avg_score = sum(scores) / len(scores)
    min_score = min(scores)
    max_score = max(scores)
    
    # Score distribution
    high_quality = len([s for s in scores if s >= 0.8])
    medium_quality = len([s for s in scores if 0.6 <= s < 0.8])
    low_quality = len([s for s in scores if s < 0.6])
    
    # Platform breakdown
    platform_stats: Dict[str, Dict[str, Any]] = {}
    for product in products:
        platform = product.platform.value if hasattr(product.platform, 'value') else str(product.platform)
        if platform not in platform_stats:
            platform_stats[platform] = {"count": 0, "avg_score": 0.0, "scores": []}
        platform_stats[platform]["count"] += 1
        platform_stats[platform]["scores"].append(product.validation_score or 0.0)
    
    # Calculate platform averages
    for platform in platform_stats:
        scores_list = platform_stats[platform]["scores"]
        platform_stats[platform]["avg_score"] = sum(scores_list) / len(scores_list) if scores_list else 0.0
        del platform_stats[platform]["scores"]  # Remove raw scores from output
    
    return {
        "total_products": len(products),
        "quality_scores": {
            "average": round(avg_score, 3),
            "minimum": round(min_score, 3),
            "maximum": round(max_score, 3)
        },
        "quality_distribution": {
            "high_quality": high_quality,
            "medium_quality": medium_quality,
            "low_quality": low_quality
        },
        "platform_breakdown": platform_stats,
        "threshold": ctx.deps.quality_threshold,
        "passing_products": len([s for s in scores if s >= ctx.deps.quality_threshold]),
        "generated_at": datetime.now().isoformat()
    }