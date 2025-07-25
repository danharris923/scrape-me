"""
Image processing tools for downloading and uploading product images to Google Cloud Storage.

This module provides tools for the Pydantic AI agent to process product images,
including downloading from original URLs, generating SEO-friendly names, and
uploading to GCS with public access.
"""

from typing import List, Dict, Any
import asyncio
import hashlib
import re
from io import BytesIO
import logging

import httpx
from google.cloud import storage
from PIL import Image
from pydantic_ai import RunContext
from pydantic_ai import ModelRetry

from agents.models import ScrapedProduct, AgentDependencies
from pydantic import HttpUrl

logger = logging.getLogger(__name__)


class ImageProcessingError(Exception):
    """Exception raised when image processing fails."""
    pass


async def process_product_images(
    ctx: RunContext[AgentDependencies],
    products: List[ScrapedProduct],
    bucket_name: str,
    image_folder: str = "products"
) -> List[ScrapedProduct]:
    """
    Download and process images for a list of products, uploading to GCS.
    
    This tool downloads product images, optimizes them, generates SEO-friendly
    filenames, and uploads them to Google Cloud Storage with public access.
    
    Args:
        ctx: Pydantic AI run context with dependencies
        products: List of ScrapedProduct objects to process
        bucket_name: GCS bucket name for uploads
        image_folder: Folder within bucket for organization
        
    Returns:
        List of products with updated processed_image_url
    """
    if not products:
        return []
    
    logger.info(f"Processing images for {len(products)} products")
    
    # Initialize GCS client
    try:
        gcs_client = storage.Client.from_service_account_json(
            ctx.deps.gcs_credentials_path
        )
        bucket = gcs_client.bucket(bucket_name)
    except Exception as e:
        logger.error(f"Failed to initialize GCS client: {e}")
        raise ModelRetry(f"GCS authentication failed: {e}")
    
    processed_products = []
    successful_uploads = 0
    failed_uploads = 0
    
    # Process images with concurrency limit
    semaphore = asyncio.Semaphore(3)  # Limit concurrent downloads
    
    async def process_single_product(product: ScrapedProduct) -> ScrapedProduct:
        nonlocal successful_uploads, failed_uploads
        
        async with semaphore:
            try:
                processed_product = await _process_single_image(
                    product, bucket, image_folder
                )
                successful_uploads += 1
                return processed_product
                
            except Exception as e:
                logger.warning(f"Failed to process image for product '{product.title}': {e}")
                failed_uploads += 1
                # Return original product with no processed image
                return product
    
    # Process all products concurrently
    tasks = [process_single_product(product) for product in products]
    processed_products = await asyncio.gather(*tasks, return_exceptions=False)
    
    logger.info(
        f"Image processing complete: {successful_uploads} successful, "
        f"{failed_uploads} failed out of {len(products)} total"
    )
    
    return processed_products


async def _process_single_image(
    product: ScrapedProduct,
    bucket: storage.Bucket,
    image_folder: str
) -> ScrapedProduct:
    """Process a single product's image."""
    try:
        # Download the image
        image_data = await _download_image(str(product.original_image_url))
        
        # Optimize the image
        optimized_data = _optimize_image(image_data)
        
        # Generate SEO-friendly filename
        filename = _generate_seo_filename(product.title, product.category)
        
        # Upload to GCS
        public_url = await _upload_to_gcs(
            bucket, optimized_data, f"{image_folder}/{filename}"
        )
        
        # Update product with processed image URL
        product.processed_image_url = HttpUrl(public_url)
        
        logger.debug(f"Successfully processed image for: {product.title}")
        return product
        
    except Exception as e:
        logger.warning(f"Image processing failed for '{product.title}': {e}")
        raise


async def _download_image(image_url: str) -> bytes:
    """Download image from URL with proper headers and error handling."""
    if not image_url or not image_url.startswith(('http://', 'https://')):
        raise ImageProcessingError(f"Invalid image URL: {image_url}")
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'image/webp,image/apng,image/*,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
    }
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(image_url, headers=headers, follow_redirects=True)
            response.raise_for_status()
            
            # Validate content type
            content_type = response.headers.get('content-type', '').lower()
            if not content_type.startswith('image/'):
                raise ImageProcessingError(f"URL does not return an image: {content_type}")
            
            # Validate file size (max 10MB)
            content_length = response.headers.get('content-length')
            if content_length and int(content_length) > 10 * 1024 * 1024:
                raise ImageProcessingError("Image too large (>10MB)")
            
            image_data = response.content
            
            # Validate we got actual image data
            if len(image_data) < 1000:  # Less than 1KB is suspicious
                raise ImageProcessingError("Downloaded image data too small")
            
            return image_data
            
        except httpx.HTTPStatusError as e:
            raise ImageProcessingError(f"HTTP error downloading image: {e.response.status_code}")
        except httpx.TimeoutException:
            raise ImageProcessingError("Timeout downloading image")
        except Exception as e:
            raise ImageProcessingError(f"Error downloading image: {e}")


def _optimize_image(image_data: bytes) -> bytes:
    """Optimize image for web use (resize, compress, convert format)."""
    try:
        # Open image with PIL
        with Image.open(BytesIO(image_data)) as img:
            # Convert to RGB if necessary (handles RGBA, etc.)
            if img.mode in ('RGBA', 'LA', 'P'):
                # Create white background for transparent images
                background = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'P':
                    img = img.convert('RGBA')
                background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                img = background
            elif img.mode != 'RGB':
                img = img.convert('RGB')
            
            # Resize if too large (max 800x800, maintain aspect ratio)
            max_size = (800, 800)
            if img.size[0] > max_size[0] or img.size[1] > max_size[1]:
                img.thumbnail(max_size, Image.Resampling.LANCZOS)
            
            # Save as optimized JPEG
            output = BytesIO()
            img.save(
                output,
                format='JPEG',
                quality=85,  # Good balance of quality vs size
                optimize=True,
                progressive=True
            )
            
            return output.getvalue()
            
    except Exception as e:
        logger.warning(f"Image optimization failed, using original: {e}")
        return image_data  # Return original if optimization fails


def _generate_seo_filename(title: str, category: str) -> str:
    """Generate SEO-friendly filename from product title and category."""
    # Clean and truncate title
    clean_title = re.sub(r'[^\w\s-]', '', title.lower())
    clean_title = re.sub(r'[-\s]+', '-', clean_title)
    clean_title = clean_title.strip('-')[:30]  # Limit length
    
    # Clean category
    clean_category = re.sub(r'[^\w\s-]', '', category.lower())
    clean_category = re.sub(r'[-\s]+', '-', clean_category)
    clean_category = clean_category.strip('-')[:20]
    
    # Create base filename
    if clean_title and clean_category:
        base_filename = f"{clean_title}-{clean_category}"
    elif clean_title:
        base_filename = clean_title
    else:
        # Fallback to generic name with timestamp
        import time
        base_filename = f"product-{int(time.time())}"
    
    # Add unique suffix to avoid collisions
    suffix = hashlib.md5(f"{title}{category}".encode()).hexdigest()[:8]
    
    return f"{base_filename}-{suffix}.jpg"


async def _upload_to_gcs(bucket: storage.Bucket, image_data: bytes, blob_path: str) -> str:
    """Upload image data to Google Cloud Storage and make it public."""
    try:
        # Create blob
        blob = bucket.blob(blob_path)
        
        # Set metadata
        blob.metadata = {
            'uploaded_by': 'affiliate_scraper',
            'content_type': 'image/jpeg',
        }
        blob.content_type = 'image/jpeg'
        
        # Upload the image data
        blob.upload_from_string(image_data, content_type='image/jpeg')
        
        # Make the blob publicly accessible
        blob.make_public()
        
        # Return the public URL
        return blob.public_url
        
    except Exception as e:
        raise ImageProcessingError(f"Failed to upload to GCS: {e}")


async def cleanup_old_images(
    ctx: RunContext[AgentDependencies],
    bucket_name: str,
    image_folder: str = "products",
    days_old: int = 30
) -> Dict[str, Any]:
    """
    Clean up old images from GCS bucket.
    
    Args:
        ctx: Pydantic AI run context
        bucket_name: GCS bucket name
        image_folder: Folder to clean up
        days_old: Delete images older than this many days
        
    Returns:
        Dictionary with cleanup statistics
    """
    try:
        gcs_client = storage.Client.from_service_account_json(
            ctx.deps.gcs_credentials_path
        )
        bucket = gcs_client.bucket(bucket_name)
        
        # List blobs in the folder
        blobs = bucket.list_blobs(prefix=f"{image_folder}/")
        
        import datetime
        cutoff_date = datetime.datetime.now() - datetime.timedelta(days=days_old)
        
        deleted_count = 0
        total_count = 0
        
        for blob in blobs:
            total_count += 1
            
            # Check if blob is old enough to delete
            if blob.time_created and blob.time_created.replace(tzinfo=None) < cutoff_date:
                try:
                    blob.delete()
                    deleted_count += 1
                    logger.debug(f"Deleted old image: {blob.name}")
                except Exception as e:
                    logger.warning(f"Failed to delete {blob.name}: {e}")
        
        logger.info(f"Cleanup complete: deleted {deleted_count} out of {total_count} images")
        
        return {
            "total_images": total_count,
            "deleted_images": deleted_count,
            "retained_images": total_count - deleted_count
        }
        
    except Exception as e:
        logger.error(f"Image cleanup failed: {e}")
        return {"error": str(e)}


async def validate_image_accessibility(image_url: str) -> Dict[str, Any]:
    """
    Validate that an uploaded image is publicly accessible.
    
    Args:
        image_url: URL to validate
        
    Returns:
        Dictionary with validation results
    """
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.head(image_url)
            
            return {
                "accessible": response.status_code == 200,
                "status_code": response.status_code,
                "content_type": response.headers.get("content-type"),
                "content_length": response.headers.get("content-length")
            }
            
    except Exception as e:
        return {
            "accessible": False,
            "error": str(e)
        }