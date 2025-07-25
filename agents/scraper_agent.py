"""
Main Pydantic AI scraper agent that orchestrates affiliate product scraping.

This module implements the intelligent scraper agent that coordinates all tools
to perform end-to-end affiliate product scraping with error recovery.
"""

import json
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional

from pydantic_ai import Agent, RunContext
from pydantic_ai import ModelRetry

from agents.models import (
    AgentDependencies, SiteConfig, ScrapingResult, 
    ProductCard
)
from config.settings import settings
from tools.playwright_scraper import scrape_multiple_urls, test_url_accessibility
from tools.image_processor import process_product_images
from tools.data_validator import validate_and_score_products, convert_to_product_cards
from tools.state_manager import (
    save_scraping_state, load_last_good_state, should_use_cached_data,
    merge_with_cached_data, increment_failure_count
)

logger = logging.getLogger(__name__)

# Initialize the main scraper agent
scraper_agent = Agent(
    model=settings.get_llm_model_string(),
    deps_type=AgentDependencies,
    system_prompt="""You are an intelligent affiliate product scraper. Your job is to:

1. **Quality Decision Making**: Only extract products with complete information (title, price, image, link)
2. **Platform Intelligence**: Adapt scraping strategy based on the affiliate platform (Amazon, Rakuten, CJ)
3. **Error Recovery**: When scraping fails, preserve last good data and continue with successful extractions
4. **Content Validation**: Score each product's data quality and only output products scoring above threshold
5. **Stealth Operation**: Use random delays and human-like browsing patterns to avoid detection

When scraping a site:
- First check if we should use cached data due to recent failures
- Test URL accessibility before attempting full scraping
- Use appropriate platform-specific scrapers for each URL
- Validate and score all extracted products
- Process images and upload to GCS with SEO-friendly names
- Only include products in final output if all data is valid and complete
- Save successful results to state for future error recovery
- If scraping fails, increment failure count and consider using cached data

Remember: Broken sites are worse than missing products. Quality over quantity always.
Graceful degradation is key - if new scraping fails, preserve and use the last good data."""
)


@scraper_agent.tool
async def scrape_site_products(
    ctx: RunContext[AgentDependencies],
    site_config: Dict[str, Any],
    force_refresh: bool = False
) -> Dict[str, Any]:
    """
    Orchestrate complete site scraping with error recovery.
    
    This is the main tool that coordinates the entire scraping workflow
    for a single affiliate site.
    
    Args:
        ctx: Pydantic AI run context
        site_config: Site configuration dictionary
        force_refresh: Whether to force refresh ignoring cached data
        
    Returns:
        Dictionary with scraping results and metadata
    """
    start_time = datetime.now()
    site_name = site_config.get("site_name", "unknown")
    
    logger.info(f"Starting scrape for site: {site_name}")
    
    try:
        # Parse site config
        try:
            config = SiteConfig(**site_config)
        except Exception as e:
            raise ModelRetry(f"Invalid site configuration: {e}")
        
        # Check if we should use cached data (unless forcing refresh)
        if not force_refresh:
            use_cache, cached_products = await should_use_cached_data(
                ctx, site_name, max_failures=3, max_age_hours=48
            )
            
            if use_cache and cached_products:
                logger.info(f"Using cached data for {site_name} due to consecutive failures")
                
                # Save the cached data as current output
                await _save_products_to_file(cached_products, config.output_path)
                
                return {
                    "success": True,
                    "site_name": site_name,
                    "total_products": len(cached_products),
                    "source": "cached_data",
                    "message": "Used cached data due to recent failures",
                    "output_file": config.output_path
                }
        
        # Test URL accessibility first
        logger.info("Testing URL accessibility...")
        accessibility_results = []
        for url_config in config.urls_to_scrape:
            test_result = await test_url_accessibility(ctx, str(url_config.url))
            accessibility_results.append(test_result)
            
            if not test_result.get("accessible", False):
                logger.warning(f"URL not accessible: {url_config.url} - {test_result.get('issues', [])}")
        
        # Filter to accessible URLs only
        accessible_urls = [
            url_config for i, url_config in enumerate(config.urls_to_scrape)
            if accessibility_results[i].get("accessible", False)
        ]
        
        if not accessible_urls:
            await increment_failure_count(ctx, site_name)
            raise ModelRetry(f"No accessible URLs found for {site_name}")
        
        # Scrape products from accessible URLs
        logger.info(f"Scraping {len(accessible_urls)} accessible URLs...")
        
        # Convert URLConfig objects to dictionaries for the tool
        url_configs_dict = [
            {
                "url": str(url_config.url),
                "platform": url_config.platform.value,
                "category": url_config.category,
                "expected_count": url_config.expected_count,
                "custom_selectors": url_config.custom_selectors
            }
            for url_config in accessible_urls
        ]
        
        scraped_products = await scrape_multiple_urls(ctx, url_configs_dict)
        
        if not scraped_products:
            # No products scraped - try to use cached data
            await increment_failure_count(ctx, site_name)
            
            use_cache, cached_products = await should_use_cached_data(
                ctx, site_name, max_failures=1, max_age_hours=72  # More lenient for zero results
            )
            
            if use_cache and cached_products:
                logger.info(f"No new products scraped, using cached data for {site_name}")
                await _save_products_to_file(cached_products, config.output_path)
                
                return {
                    "success": True,
                    "site_name": site_name,
                    "total_products": len(cached_products),
                    "source": "cached_data_fallback",
                    "message": "No new products found, used cached data",
                    "output_file": config.output_path
                }
            else:
                raise ModelRetry(f"No products scraped and no cached data available for {site_name}")
        
        # Validate and score products
        logger.info(f"Validating {len(scraped_products)} scraped products...")
        validated_products = await validate_and_score_products(ctx, scraped_products)
        
        if not validated_products:
            logger.warning(f"No products passed validation for {site_name}")
            # Try to merge with cached data
            cached_state = await load_last_good_state(ctx, site_name)
            if cached_state and cached_state.last_products:
                logger.info("Using cached products due to validation failure")
                await _save_products_to_file(cached_state.last_products, config.output_path)
                
                return {
                    "success": True,
                    "site_name": site_name,
                    "total_products": len(cached_state.last_products),
                    "source": "cached_validation_fallback",
                    "message": "No products passed validation, used cached data",
                    "output_file": config.output_path
                }
        
        # Process images
        logger.info(f"Processing images for {len(validated_products)} products...")
        processed_products = await process_product_images(
            ctx, validated_products, config.gcs_bucket, config.image_folder
        )
        
        # Convert to final ProductCard format
        product_cards = await convert_to_product_cards(ctx, processed_products)
        
        if not product_cards:
            raise ModelRetry(f"No products survived final conversion for {site_name}")
        
        # Merge with cached data if needed (supplement strategy)
        final_products = await merge_with_cached_data(
            ctx, site_name, product_cards, merge_strategy="supplement"
        )
        
        # Save products to output file
        await _save_products_to_file(final_products, config.output_path)
        
        # Create scraping result
        processing_time = (datetime.now() - start_time).total_seconds()
        scraping_result = ScrapingResult(
            site_name=site_name,
            total_products_found=len(scraped_products),
            valid_products=len(final_products),
            failed_products=len(scraped_products) - len(validated_products),
            processing_time_seconds=processing_time,
            quality_score=sum(p.validation_score or 0 for p in processed_products) / len(processed_products) if processed_products else 0,
            output_file_path=config.output_path
        )
        
        # Save successful state
        await save_scraping_state(ctx, site_name, final_products, scraping_result)
        
        logger.info(f"Successfully completed scraping for {site_name}: {len(final_products)} products")
        
        return {
            "success": True,
            "site_name": site_name,
            "total_products": len(final_products),
            "scraped_products": len(scraped_products),
            "validated_products": len(validated_products),
            "processing_time_seconds": processing_time,
            "quality_score": scraping_result.quality_score,
            "output_file": config.output_path,
            "source": "fresh_scrape"
        }
        
    except ModelRetry:
        # Re-raise ModelRetry for agent to handle
        raise
    except Exception as e:
        # Handle other errors gracefully
        await increment_failure_count(ctx, site_name)
        error_msg = f"Scraping failed for {site_name}: {str(e)}"
        logger.error(error_msg)
        
        # Try to use cached data as last resort
        use_cache, cached_products = await should_use_cached_data(
            ctx, site_name, max_failures=1, max_age_hours=96  # Very lenient for errors
        )
        
        if use_cache and cached_products:
            logger.info(f"Using cached data due to scraping error for {site_name}")
            await _save_products_to_file(cached_products, config.output_path)
            
            return {
                "success": True,
                "site_name": site_name,
                "total_products": len(cached_products),
                "source": "cached_error_fallback",
                "message": f"Scraping failed, used cached data: {str(e)}",
                "output_file": config.output_path
            }
        
        # No cached data available - return failure
        return {
            "success": False,
            "site_name": site_name,
            "error": error_msg,
            "total_products": 0
        }


@scraper_agent.tool
async def generate_scraping_report(
    ctx: RunContext[AgentDependencies],
    results: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Generate a comprehensive report of scraping operations.
    
    Args:
        ctx: Pydantic AI run context
        results: List of scraping results from different sites
        
    Returns:
        Comprehensive scraping report
    """
    try:
        total_sites = len(results)
        successful_sites = len([r for r in results if r.get("success", False)])
        total_products = sum(r.get("total_products", 0) for r in results)
        
        # Calculate statistics
        avg_processing_time = sum(
            r.get("processing_time_seconds", 0) for r in results
        ) / total_sites if total_sites > 0 else 0
        
        avg_quality_score = sum(
            r.get("quality_score", 0) for r in results if r.get("quality_score")
        ) / len([r for r in results if r.get("quality_score")]) if results else 0
        
        # Source breakdown
        source_breakdown: Dict[str, int] = {}
        for result in results:
            source = result.get("source", "unknown")
            source_breakdown[source] = source_breakdown.get(source, 0) + 1
        
        report = {
            "summary": {
                "total_sites": total_sites,
                "successful_sites": successful_sites,
                "failed_sites": total_sites - successful_sites,
                "success_rate": successful_sites / total_sites if total_sites > 0 else 0,
                "total_products": total_products,
                "avg_processing_time_seconds": round(avg_processing_time, 2),
                "avg_quality_score": round(avg_quality_score, 3)
            },
            "source_breakdown": source_breakdown,
            "site_results": results,
            "generated_at": datetime.now().isoformat()
        }
        
        logger.info(f"Generated scraping report: {successful_sites}/{total_sites} sites successful")
        return report
        
    except Exception as e:
        logger.error(f"Failed to generate scraping report: {e}")
        return {"error": str(e)}


async def _save_products_to_file(products: List[ProductCard], output_path: str) -> None:
    """Save products to JSON file."""
    try:
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Convert products to dictionaries
        products_data = [product.model_dump(mode='json') for product in products]
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(products_data, f, indent=2, ensure_ascii=False, default=str)
        
        logger.info(f"Saved {len(products)} products to {output_path}")
        
    except Exception as e:
        logger.error(f"Failed to save products to {output_path}: {e}")
        raise


async def run_site_scraping(
    site_config_path: str,
    force_refresh: bool = False,
    agent_deps: Optional[AgentDependencies] = None
) -> Dict[str, Any]:
    """
    High-level function to run scraping for a single site.
    
    Args:
        site_config_path: Path to site configuration file
        force_refresh: Whether to force refresh ignoring cache
        agent_deps: Optional AgentDependencies override
        
    Returns:
        Scraping result dictionary
    """
    # Load site configuration
    try:
        with open(site_config_path, 'r', encoding='utf-8') as f:
            site_config = json.load(f)
    except Exception as e:
        return {"success": False, "error": f"Failed to load site config: {e}"}
    
    # Create agent dependencies if not provided
    if not agent_deps:
        agent_deps = AgentDependencies(
            gcs_credentials_path=settings.gcs_credentials_path,
            output_directory=settings.output_directory,
            state_directory=settings.state_directory,
            scraping_delay_seconds=settings.scraping_delay_seconds,
            max_retries=settings.max_retries,
            quality_threshold=settings.quality_threshold
        )
    
    # Run the scraping
    try:
        result = await scraper_agent.run(
            f"Scrape products for site: {site_config.get('site_name', 'unknown')}",
            deps=agent_deps
        )
        
        return result.data if hasattr(result, 'data') and isinstance(result.data, dict) else {"success": False, "error": "No data returned"}
        
    except Exception as e:
        logger.error(f"Agent run failed: {e}")
        return {"success": False, "error": str(e)}