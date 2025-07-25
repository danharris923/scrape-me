"""
State management tools for graceful error recovery and data persistence.

This module provides tools for the Pydantic AI agent to save and restore
scraping state, enabling graceful recovery from failures.
"""

from typing import List, Dict, Any, Optional
import json
import logging
from pathlib import Path
from datetime import datetime, timedelta

from pydantic_ai import RunContext

from agents.models import (
    ProductCard, StateData, ScrapingResult, 
    AgentDependencies
)

logger = logging.getLogger(__name__)


class StateManagementError(Exception):
    """Exception raised when state management operations fail."""
    pass


async def save_scraping_state(
    ctx: RunContext[AgentDependencies],
    site_name: str,
    products: List[ProductCard],
    scraping_result: ScrapingResult
) -> str:
    """
    Save the current scraping state for a site.
    
    This tool saves successful scraping results to enable graceful recovery
    in case of future failures.
    
    Args:
        ctx: Pydantic AI run context
        site_name: Name of the site being scraped
        products: List of successfully scraped products
        scraping_result: Result metadata from scraping operation
        
    Returns:
        Path to saved state file
    """
    try:
        state_dir = Path(ctx.deps.state_directory)
        state_dir.mkdir(parents=True, exist_ok=True)
        
        state_file = state_dir / f"{site_name}_state.json"
        
        # Create state data
        state_data = StateData(
            site_name=site_name,
            last_successful_scrape=datetime.now(),
            last_products=products,
            last_result=scraping_result,
            consecutive_failures=0  # Reset on successful save
        )
        
        # Save to file
        with open(state_file, 'w', encoding='utf-8') as f:
            json.dump(state_data.model_dump(mode='json'), f, indent=2, default=str)
        
        logger.info(f"Saved state for {site_name} with {len(products)} products")
        return str(state_file)
        
    except Exception as e:
        error_msg = f"Failed to save state for {site_name}: {e}"
        logger.error(error_msg)
        raise StateManagementError(error_msg)


async def load_last_good_state(
    ctx: RunContext[AgentDependencies],
    site_name: str
) -> Optional[StateData]:
    """
    Load the last good scraping state for a site.
    
    Args:
        ctx: Pydantic AI run context
        site_name: Name of the site to load state for
        
    Returns:
        StateData object if found, None otherwise
    """
    try:
        state_file = Path(ctx.deps.state_directory) / f"{site_name}_state.json"
        
        if not state_file.exists():
            logger.info(f"No previous state found for {site_name}")
            return None
        
        with open(state_file, 'r', encoding='utf-8') as f:
            state_dict = json.load(f)
        
        # Parse datetime strings back to datetime objects
        if 'last_successful_scrape' in state_dict:
            state_dict['last_successful_scrape'] = datetime.fromisoformat(
                state_dict['last_successful_scrape'].replace('Z', '+00:00')
            )
        
        if 'last_result' in state_dict and 'timestamp' in state_dict['last_result']:
            state_dict['last_result']['timestamp'] = datetime.fromisoformat(
                state_dict['last_result']['timestamp'].replace('Z', '+00:00')
            )
        
        state_data = StateData(**state_dict)
        
        logger.info(f"Loaded state for {site_name} from {state_data.last_successful_scrape}")
        return state_data
        
    except Exception as e:
        logger.warning(f"Failed to load state for {site_name}: {e}")
        return None


async def increment_failure_count(
    ctx: RunContext[AgentDependencies],
    site_name: str
) -> int:
    """
    Increment the consecutive failure count for a site.
    
    Args:
        ctx: Pydantic AI run context
        site_name: Name of the site
        
    Returns:
        New failure count
    """
    try:
        state_data = await load_last_good_state(ctx, site_name)
        
        if state_data:
            state_data.consecutive_failures += 1
        else:
            # Create new state with failure
            state_data = StateData(
                site_name=site_name,
                last_successful_scrape=datetime.now(),
                last_products=[],
                last_result=ScrapingResult(
                    site_name=site_name,
                    total_products_found=0,
                    valid_products=0,
                    failed_products=0,
                    processing_time_seconds=0.0,
                    quality_score=0.0,
                    output_file_path=""
                ),
                consecutive_failures=1
            )
        
        # Save updated state
        state_dir = Path(ctx.deps.state_directory)
        state_dir.mkdir(parents=True, exist_ok=True)
        state_file = state_dir / f"{site_name}_state.json"
        
        with open(state_file, 'w', encoding='utf-8') as f:
            json.dump(state_data.model_dump(mode='json'), f, indent=2, default=str)
        
        logger.warning(f"Incremented failure count for {site_name} to {state_data.consecutive_failures}")
        return state_data.consecutive_failures
        
    except Exception as e:
        logger.error(f"Failed to increment failure count for {site_name}: {e}")
        return 1  # Assume at least one failure


async def should_use_cached_data(
    ctx: RunContext[AgentDependencies],
    site_name: str,
    max_failures: int = 3,
    max_age_hours: int = 48
) -> tuple[bool, Optional[List[ProductCard]]]:
    """
    Determine if cached data should be used due to consecutive failures.
    
    Args:
        ctx: Pydantic AI run context
        site_name: Name of the site
        max_failures: Maximum failures before using cache
        max_age_hours: Maximum age of cached data in hours
        
    Returns:
        Tuple of (should_use_cache, cached_products)
    """
    try:
        state_data = await load_last_good_state(ctx, site_name)
        
        if not state_data:
            return False, None
        
        # Check failure count
        if state_data.consecutive_failures < max_failures:
            return False, None
        
        # Check age of cached data
        age = datetime.now() - state_data.last_successful_scrape
        if age > timedelta(hours=max_age_hours):
            logger.warning(f"Cached data for {site_name} is too old ({age})")
            return False, None
        
        logger.info(
            f"Using cached data for {site_name} due to {state_data.consecutive_failures} "
            f"consecutive failures"
        )
        
        return True, state_data.last_products
        
    except Exception as e:
        logger.error(f"Error checking cached data for {site_name}: {e}")
        return False, None


async def merge_with_cached_data(
    ctx: RunContext[AgentDependencies],
    site_name: str,
    new_products: List[ProductCard],
    merge_strategy: str = "supplement"
) -> List[ProductCard]:
    """
    Merge new products with cached data using specified strategy.
    
    Args:
        ctx: Pydantic AI run context
        site_name: Name of the site
        new_products: Newly scraped products
        merge_strategy: "supplement" (add to cached) or "replace" (prefer new)
        
    Returns:
        Merged list of products
    """
    try:
        state_data = await load_last_good_state(ctx, site_name)
        
        if not state_data or not state_data.last_products:
            return new_products
        
        cached_products = state_data.last_products
        
        if merge_strategy == "replace":
            # Prefer new products, use cached only to fill gaps
            merged = new_products.copy()
            
            # Add cached products that aren't in new products (by title)
            new_titles = {p.title.lower() for p in new_products}
            for cached_product in cached_products:
                if cached_product.title.lower() not in new_titles:
                    merged.append(cached_product)
                    
        elif merge_strategy == "supplement":
            # Use cached products as base, add new ones
            merged = cached_products.copy()
            
            # Add new products that aren't in cached (by title)
            cached_titles = {p.title.lower() for p in cached_products}
            for new_product in new_products:
                if new_product.title.lower() not in cached_titles:
                    merged.append(new_product)
        else:
            raise ValueError(f"Unknown merge strategy: {merge_strategy}")
        
        logger.info(
            f"Merged {len(new_products)} new products with {len(cached_products)} "
            f"cached products for {site_name}, result: {len(merged)} products"
        )
        
        return merged
        
    except Exception as e:
        logger.warning(f"Failed to merge with cached data for {site_name}: {e}")
        return new_products  # Fallback to new products only


async def cleanup_old_state_files(
    ctx: RunContext[AgentDependencies],
    max_age_days: int = 30
) -> Dict[str, Any]:
    """
    Clean up old state files.
    
    Args:
        ctx: Pydantic AI run context
        max_age_days: Maximum age of state files to keep
        
    Returns:
        Dictionary with cleanup statistics
    """
    try:
        state_dir = Path(ctx.deps.state_directory)
        
        if not state_dir.exists():
            return {"total_files": 0, "deleted_files": 0}
        
        cutoff_time = datetime.now() - timedelta(days=max_age_days)
        
        deleted_count = 0
        total_count = 0
        
        for state_file in state_dir.glob("*_state.json"):
            total_count += 1
            
            # Check file modification time
            file_mtime = datetime.fromtimestamp(state_file.stat().st_mtime)
            
            if file_mtime < cutoff_time:
                try:
                    state_file.unlink()
                    deleted_count += 1
                    logger.debug(f"Deleted old state file: {state_file}")
                except Exception as e:
                    logger.warning(f"Failed to delete {state_file}: {e}")
        
        logger.info(f"State cleanup: deleted {deleted_count} out of {total_count} files")
        
        return {
            "total_files": total_count,
            "deleted_files": deleted_count,
            "retained_files": total_count - deleted_count
        }
        
    except Exception as e:
        logger.error(f"State cleanup failed: {e}")
        return {"error": str(e)}


async def get_state_summary(
    ctx: RunContext[AgentDependencies]
) -> Dict[str, Any]:
    """
    Get a summary of all site states.
    
    Args:
        ctx: Pydantic AI run context
        
    Returns:
        Dictionary with state summary for all sites
    """
    try:
        state_dir = Path(ctx.deps.state_directory)
        
        if not state_dir.exists():
            return {"sites": {}, "total_sites": 0}
        
        sites_summary = {}
        
        for state_file in state_dir.glob("*_state.json"):
            site_name = state_file.stem.replace("_state", "")
            
            try:
                with open(state_file, 'r', encoding='utf-8') as f:
                    state_dict = json.load(f)
                
                # Extract key information
                last_scrape = state_dict.get('last_successful_scrape')
                consecutive_failures = state_dict.get('consecutive_failures', 0)
                product_count = len(state_dict.get('last_products', []))
                
                sites_summary[site_name] = {
                    "last_scrape": last_scrape,
                    "consecutive_failures": consecutive_failures,
                    "cached_products": product_count,
                    "health_status": "healthy" if consecutive_failures == 0 else 
                                   "warning" if consecutive_failures < 3 else "critical"
                }
                
            except Exception as e:
                sites_summary[site_name] = {"error": str(e)}
        
        return {
            "sites": sites_summary,
            "total_sites": len(sites_summary),
            "generated_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to generate state summary: {e}")
        return {"error": str(e)}


async def export_state_backup(
    ctx: RunContext[AgentDependencies],
    backup_path: Optional[str] = None
) -> str:
    """
    Export all state data to a backup file.
    
    Args:
        ctx: Pydantic AI run context
        backup_path: Optional custom backup path
        
    Returns:
        Path to backup file
    """
    try:
        state_dir = Path(ctx.deps.state_directory)
        
        if backup_path:
            backup_file = Path(backup_path)
        else:
            backup_file = state_dir / f"state_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        backup_file.parent.mkdir(parents=True, exist_ok=True)
        
        all_states = {}
        
        for state_file in state_dir.glob("*_state.json"):
            site_name = state_file.stem.replace("_state", "")
            
            try:
                with open(state_file, 'r', encoding='utf-8') as f:
                    all_states[site_name] = json.load(f)
            except Exception as e:
                logger.warning(f"Failed to read state for {site_name}: {e}")
                all_states[site_name] = {"error": str(e)}
        
        backup_data = {
            "backup_timestamp": datetime.now().isoformat(),
            "total_sites": len(all_states),
            "states": all_states
        }
        
        with open(backup_file, 'w', encoding='utf-8') as f:
            json.dump(backup_data, f, indent=2, default=str)
        
        logger.info(f"Exported state backup to {backup_file}")
        return str(backup_file)
        
    except Exception as e:
        error_msg = f"Failed to export state backup: {e}"
        logger.error(error_msg)
        raise StateManagementError(error_msg)