"""Fast AMBOSS article processor using existing URL list."""

import asyncio
import re
from pathlib import Path
from typing import List, Optional, Tuple
from urllib.parse import urlparse

from structlog import get_logger

from .auth import AuthManager
from .config import settings
from .expander import ContentExpander, ExpansionFailure
from .shooter import ScreenshotShooter
from .validator import ContentValidator, ValidationFailure

logger = get_logger(__name__)


class FastAMBOSSProcessor:
    """Fast processor for AMBOSS articles using existing URL list."""
    
    def __init__(self):
        self.article_pattern = re.compile(r'https://next\.amboss\.com/de/article/([a-zA-Z0-9-]+)')
        self.expander = ContentExpander()
        self.shooter = ScreenshotShooter()
        self.validator = ContentValidator()
        self.processed_count = 0
        self.success_count = 0
        self.failed_count = 0
        
    def extract_urls_from_file(self, filename: str = "amboss_all_articles_links.txt") -> List[str]:
        """Extract clean URLs from the existing file."""
        logger.info("Reading URLs from file", filename=filename)
        
        urls = []
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    # Skip header lines and empty lines
                    if not line or line.startswith('AMBOSS All Article URLs') or line.startswith('Generated on:') or line.startswith('Total URLs:'):
                        continue
                    
                    # Extract URL from numbered lines like "1. https://next.amboss.com/de/article/--0D-i - Pränataldiagnostik"
                    if line[0].isdigit() and '. ' in line:
                        url_part = line.split('. ')[1]
                        if ' - ' in url_part:
                            url = url_part.split(' - ')[0]
                        else:
                            url = url_part
                    else:
                        # Direct URL line
                        url = line
                    
                    # Clean and validate URL
                    if self.article_pattern.match(url):
                        # Remove any fragments
                        parsed = urlparse(url)
                        clean_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
                        urls.append(clean_url)
            
            logger.info("Extracted URLs from file", count=len(urls))
            return urls
            
        except FileNotFoundError:
            logger.error("URL file not found", filename=filename)
            return []
        except Exception as e:
            logger.error("Error reading URL file", filename=filename, error=str(e))
            return []
    
    async def process_article(self, url: str, auth_manager: AuthManager) -> Tuple[bool, Optional[str]]:
        """Process a single article URL."""
        try:
            # Extract slug from URL
            match = self.article_pattern.match(url)
            if not match:
                return False, "Invalid URL format"
            
            slug = match.group(1)
            logger.info("Processing article", slug=slug, url=url)
            
            # Create browser context
            context = await auth_manager.create_context()
            page = await context.new_page()
            
            try:
                # Navigate to article
                await page.goto(url, wait_until="networkidle")
                
                # Verify authentication
                if not await auth_manager.verify_auth(page):
                    return False, "Authentication failed"
                
                # Expand all content
                await self.expander.fully_expand(page)
                
                # Validate content
                validation_result = await self.validator.validate_page(page)
                if not validation_result.get('is_valid', False):
                    return False, f"Validation failed: {validation_result.get('issues', [])}"
                
                # Capture screenshots
                output_dir = settings.output_dir / slug / f"run_{self.processed_count}"
                output_dir.mkdir(parents=True, exist_ok=True)
                
                screenshots = await self.shooter.shoot_sections(page, slug, f"run_{self.processed_count}", output_dir)
                
                logger.info("Article processed successfully", slug=slug, screenshots=len(screenshots))
                return True, None
                
            finally:
                await page.close()
                await context.close()
                
        except ExpansionFailure as e:
            logger.warning("Expansion failed", slug=slug, error=str(e))
            return False, f"Expansion failed: {e}"
        except ValidationFailure as e:
            logger.warning("Validation failed", slug=slug, error=str(e))
            return False, f"Validation failed: {e}"
        except Exception as e:
            logger.error("Processing error", slug=slug, error=str(e))
            return False, f"Processing error: {e}"
    
    async def process_all_articles(self, urls: List[str], limit: Optional[int] = None) -> dict:
        """Process all articles with rate limiting."""
        logger.info("Starting article processing", total_urls=len(urls), limit=limit)
        
        if limit:
            urls = urls[:limit]
            logger.info("Limited URLs for processing", limit=limit, actual_count=len(urls))
        
        # Initialize auth manager
        async with AuthManager() as auth_manager:
            # Verify authentication first
            context = await auth_manager.create_context()
            page = await context.new_page()
            try:
                if not await auth_manager.verify_auth(page):
                    raise Exception("Authentication failed - cannot access AMBOSS")
                logger.info("Authentication verified")
            finally:
                await page.close()
                await context.close()
            
            # Process articles with rate limiting
            for i, url in enumerate(urls):
                self.processed_count += 1
                
                success, error = await self.process_article(url, auth_manager)
                
                if success:
                    self.success_count += 1
                else:
                    self.failed_count += 1
                    logger.warning("Article processing failed", url=url, error=error)
                
                # Rate limiting - wait between requests
                if i < len(urls) - 1:  # Don't wait after the last one
                    delay = settings.min_delay + (settings.max_delay - settings.min_delay) * (i % 10) / 10
                    logger.debug("Rate limiting delay", delay=delay)
                    await asyncio.sleep(delay)
                
                # Progress update
                if (i + 1) % 10 == 0:
                    logger.info("Processing progress", processed=i + 1, total=len(urls))
        
        result = {
            'total': len(urls),
            'processed': self.processed_count,
            'successful': self.success_count,
            'failed': self.failed_count,
            'success_rate': self.success_count / len(urls) if urls else 0
        }
        
        logger.info("Processing completed", **result)
        return result 