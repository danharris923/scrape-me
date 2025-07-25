#!/usr/bin/env python3
"""
Main CLI interface for the affiliate scraper system.

This script provides command-line access to the intelligent affiliate scraper,
supporting single-site scraping, batch operations, and maintenance tasks.
"""

import argparse
import asyncio
import json
import logging
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

from config.settings import settings, reload_settings
from agents.models import AgentDependencies
from agents.scraper_agent import run_site_scraping, scraper_agent
from tools.state_manager import get_state_summary, cleanup_old_state_files, export_state_backup
from tools.image_processor import cleanup_old_images

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(settings.log_file) if settings.log_file else logging.NullHandler()
    ]
)

logger = logging.getLogger(__name__)


class ScraperCLI:
    """Command-line interface for the affiliate scraper."""
    
    def __init__(self):
        self.agent_deps = self._create_agent_dependencies()
    
    def _create_agent_dependencies(self) -> AgentDependencies:
        """Create AgentDependencies from settings."""
        return AgentDependencies(
            gcs_credentials_path=settings.gcs_credentials_path,
            output_directory=settings.output_directory,
            state_directory=settings.state_directory,
            scraping_delay_seconds=settings.scraping_delay_seconds,
            max_retries=settings.max_retries,
            quality_threshold=settings.quality_threshold
        )
    
    async def scrape_site(self, site_name: str, force_refresh: bool = False) -> Dict[str, Any]:
        """Scrape a single site by name."""
        site_config_path = Path(settings.config_directory) / f"{site_name}.json"
        
        if not site_config_path.exists():
            return {
                "success": False,
                "error": f"Site configuration not found: {site_config_path}"
            }
        
        logger.info(f"Starting scrape for site: {site_name}")
        
        try:
            result = await run_site_scraping(
                str(site_config_path),
                force_refresh=force_refresh,
                agent_deps=self.agent_deps
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Scraping failed for {site_name}: {e}")
            return {"success": False, "error": str(e)}
    
    async def scrape_all_sites(self, force_refresh: bool = False) -> List[Dict[str, Any]]:
        """Scrape all configured sites."""
        config_dir = Path(settings.config_directory)
        
        if not config_dir.exists():
            logger.error(f"Config directory not found: {config_dir}")
            return [{"success": False, "error": "Config directory not found"}]
        
        # Find all site configuration files
        site_configs = list(config_dir.glob("*.json"))
        
        if not site_configs:
            logger.warning(f"No site configurations found in {config_dir}")
            return [{"success": False, "error": "No site configurations found"}]
        
        logger.info(f"Found {len(site_configs)} site configurations")
        
        results = []
        
        for config_file in site_configs:
            site_name = config_file.stem
            logger.info(f"Processing site: {site_name}")
            
            try:
                result = await self.scrape_site(site_name, force_refresh)
                results.append(result)
                
                # Add delay between sites to be respectful
                await asyncio.sleep(settings.scraping_delay_seconds * 2)
                
            except Exception as e:
                logger.error(f"Failed to process site {site_name}: {e}")
                results.append({
                    "success": False,
                    "site_name": site_name,
                    "error": str(e)
                })
        
        return results
    
    async def generate_report(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate a comprehensive scraping report."""
        try:
            report_result = await scraper_agent.run(
                "Generate a comprehensive scraping report",
                deps=self.agent_deps
            )
            
            return report_result.data if hasattr(report_result, 'data') and isinstance(report_result.data, dict) else {}
            
        except Exception as e:
            logger.error(f"Failed to generate report: {e}")
            return {"error": str(e)}
    
    async def show_status(self) -> Dict[str, Any]:
        """Show current status of all sites."""
        try:
            state_summary = await get_state_summary(
                type('MockContext', (), {'deps': self.agent_deps})()
            )
            
            return state_summary
            
        except Exception as e:
            logger.error(f"Failed to get status: {e}")
            return {"error": str(e)}
    
    async def cleanup_old_data(self, days: int = 30) -> Dict[str, Any]:
        """Clean up old state files and images."""
        try:
            # Clean up state files
            state_cleanup = await cleanup_old_state_files(
                type('MockContext', (), {'deps': self.agent_deps})(),
                max_age_days=days
            )
            
            # Clean up images (if bucket configured)
            image_cleanup = {}
            if hasattr(settings, 'gcs_bucket_name') and settings.gcs_bucket_name:
                image_cleanup = await cleanup_old_images(
                    type('MockContext', (), {'deps': self.agent_deps})(),
                    bucket_name=settings.gcs_bucket_name,
                    days_old=days
                )
            
            return {
                "state_cleanup": state_cleanup,
                "image_cleanup": image_cleanup
            }
            
        except Exception as e:
            logger.error(f"Cleanup failed: {e}")
            return {"error": str(e)}
    
    async def backup_state(self, backup_path: Optional[str] = None) -> str:
        """Create a backup of all state data."""
        try:
            backup_file = await export_state_backup(
                type('MockContext', (), {'deps': self.agent_deps})(),
                backup_path=backup_path
            )
            
            return backup_file
            
        except Exception as e:
            logger.error(f"Backup failed: {e}")
            raise


def print_results(results: List[Dict[str, Any]], detailed: bool = False):
    """Print scraping results in a readable format."""
    if not results:
        print("No results to display")
        return
    
    total_sites = len(results)
    successful_sites = len([r for r in results if r.get("success", False)])
    total_products = sum(r.get("total_products", 0) for r in results)
    
    print(f"\n{'='*60}")
    print("SCRAPING SUMMARY")
    print(f"{'='*60}")
    print(f"Sites processed: {total_sites}")
    print(f"Successful: {successful_sites}")
    print(f"Failed: {total_sites - successful_sites}")
    print(f"Total products: {total_products}")
    print(f"Success rate: {successful_sites/total_sites*100:.1f}%")
    
    if detailed:
        print(f"\n{'='*60}")
        print("DETAILED RESULTS")
        print(f"{'='*60}")
        
        for result in results:
            site_name = result.get("site_name", "Unknown")
            success = result.get("success", False)
            products = result.get("total_products", 0)
            
            status = "✅ SUCCESS" if success else "❌ FAILED"
            print(f"\n{site_name}: {status}")
            
            if success:
                source = result.get("source", "unknown")
                print(f"  Products: {products}")
                print(f"  Source: {source}")
                print(f"  Output: {result.get('output_file', 'N/A')}")
                
                if "processing_time_seconds" in result:
                    print(f"  Time: {result['processing_time_seconds']:.1f}s")
                
                if "quality_score" in result:
                    print(f"  Quality: {result['quality_score']:.3f}")
            else:
                print(f"  Error: {result.get('error', 'Unknown error')}")


async def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Intelligent Affiliate Product Scraper",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py --site outdoor-gear-site
  python main.py --all-sites --force-refresh
  python main.py --status
  python main.py --cleanup --days 14
        """
    )
    
    # Main commands
    parser.add_argument("--site", type=str, help="Scrape a specific site by name")
    parser.add_argument("--all-sites", action="store_true", help="Scrape all configured sites")
    parser.add_argument("--status", action="store_true", help="Show status of all sites")
    parser.add_argument("--cleanup", action="store_true", help="Clean up old data")
    parser.add_argument("--backup", action="store_true", help="Create state backup")
    
    # Options
    parser.add_argument("--force-refresh", action="store_true", help="Force refresh ignoring cached data")
    parser.add_argument("--detailed", action="store_true", help="Show detailed results")
    parser.add_argument("--days", type=int, default=30, help="Days for cleanup operations")
    parser.add_argument("--test-mode", action="store_true", help="Run in test mode")
    parser.add_argument("--config", type=str, help="Custom config file path")
    
    args = parser.parse_args()
    
    # Reload settings if custom config provided
    if args.config:
        # This would require modifying settings to accept custom config
        logger.info(f"Using custom config: {args.config}")
    
    if args.test_mode:
        reload_settings(test_mode=True)
        logger.info("Running in test mode")
    
    cli = ScraperCLI()
    
    try:
        if args.site:
            # Scrape specific site
            result = await cli.scrape_site(args.site, args.force_refresh)
            print_results([result], args.detailed)
            
            if not result.get("success", False):
                sys.exit(1)
                
        elif args.all_sites:
            # Scrape all sites
            results = await cli.scrape_all_sites(args.force_refresh)
            print_results(results, args.detailed)
            
            # Generate comprehensive report
            report = await cli.generate_report(results)
            
            # Save report to file
            report_file = Path(settings.output_directory) / f"scraping_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, default=str)
            
            print(f"\nDetailed report saved to: {report_file}")
            
            # Exit with error if any sites failed
            if any(not r.get("success", False) for r in results):
                sys.exit(1)
                
        elif args.status:
            # Show status
            status = await cli.show_status()
            print(f"\n{'='*60}")
            print("SYSTEM STATUS")
            print(f"{'='*60}")
            print(json.dumps(status, indent=2, default=str))
            
        elif args.cleanup:
            # Clean up old data
            cleanup_results = await cli.cleanup_old_data(args.days)
            print(f"\n{'='*60}")
            print("CLEANUP RESULTS")
            print(f"{'='*60}")
            print(json.dumps(cleanup_results, indent=2, default=str))
            
        elif args.backup:
            # Create backup
            backup_file = await cli.backup_state()
            print(f"\nState backup created: {backup_file}")
            
        else:
            # No command specified
            parser.print_help()
            print("\nNo command specified. Use --help for usage information.")
            sys.exit(1)
            
    except KeyboardInterrupt:
        logger.info("Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        if args.detailed:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())