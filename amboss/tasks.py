"""Task orchestration for AMBOSS scraping."""

import asyncio
import random
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple

from asyncio_throttle import Throttler
from playwright.async_api import Page
from structlog import get_logger
from tenacity import retry, stop_after_attempt, wait_exponential

from .auth import AuthManager
from .config import settings
from .db import DatabaseManager
from .discover import discover_articles
from .expander import ContentExpander, ExpansionFailure
from .shooter import ScreenshotShooter
from .validator import ContentValidator

logger = get_logger(__name__)


class ScrapingTask:
    """Main task orchestrator for AMBOSS scraping."""
    
    def __init__(self):
        self.throttler = Throttler(rate_limit=settings.requests_per_minute, period=60)
        self.auth_manager = None
        self.db = None
    
    async def __aenter__(self):
        """Async context manager entry."""
        self.auth_manager = AuthManager()
        await self.auth_manager.__aenter__()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.auth_manager:
            await self.auth_manager.__aexit__(exc_type, exc_val, exc_tb)
    
    async def discover_urls(self, start_urls: Optional[List[str]] = None) -> List[str]:
        """Discover article URLs and save to database."""
        logger.info("Starting URL discovery")
        
        discovered_urls = await discover_articles(start_urls)
        
        logger.info("URL discovery completed", count=len(discovered_urls))
        return discovered_urls
    
    async def process_slug(
        self, 
        slug: str, 
        url: str, 
        run_id: str
    ) -> Tuple[bool, Optional[str]]:
        """Process a single article slug."""
        logger.info("Processing slug", slug=slug, url=url, run_id=run_id)
        
        # Rate limiting
        async with self.throttler:
            try:
                # Create browser context
                context = await self.auth_manager.create_context()
                page = await context.new_page()
                
                try:
                    # Navigate to page
                    await self._navigate_to_page(page, url)
                    
                    # Verify authentication
                    if not await self.auth_manager.verify_auth(page):
                        raise Exception("Authentication failed")
                    
                    # Expand content
                    await self._expand_content(page)
                    
                    # Validate expansion
                    validation_result = await self._validate_page(page)
                    if not validation_result["validation_passed"]:
                        raise ExpansionFailure(
                            f"Page validation failed: {validation_result['errors']}"
                        )
                    
                    # Capture screenshots
                    screenshots = await self._capture_screenshots(page, slug, run_id)
                    
                    # Save to database
                    await self._save_results(slug, run_id, screenshots)
                    
                    logger.info("Successfully processed slug", slug=slug, run_id=run_id)
                    return True, None
                    
                finally:
                    await page.close()
                    await context.close()
                    
            except Exception as e:
                error_msg = str(e)
                logger.error("Failed to process slug", slug=slug, error=error_msg)
                return False, error_msg
    
    async def process_pending_urls(
        self, 
        limit: Optional[int] = None,
        run_id: Optional[str] = None
    ) -> dict:
        """Process all pending URLs in the database."""
        if run_id is None:
            run_id = str(uuid.uuid4())
        
        logger.info("Starting batch processing", run_id=run_id, limit=limit)
        
        async with DatabaseManager() as db:
            self.db = db
            
            # Get pending URLs
            pending_urls = await db.get_pending_urls(limit)
            
            if not pending_urls:
                logger.info("No pending URLs to process")
                return {"processed": 0, "successful": 0, "failed": 0}
            
            logger.info(f"Found {len(pending_urls)} pending URLs to process")
            
            # Process each URL
            successful = 0
            failed = 0
            
            for slug, url in pending_urls:
                # Update status to processing
                await db.update_url_status(slug, "processing")
                
                # Start run
                await db.start_run(run_id, slug)
                
                # Process the slug
                success, error = await self.process_slug(slug, url, run_id)
                
                if success:
                    await db.update_url_status(slug, "done")
                    await db.finish_run(run_id, slug, True)
                    successful += 1
                else:
                    await db.update_url_status(slug, "failed_expansion", error)
                    await db.finish_run(run_id, slug, False, error)
                    failed += 1
                
                # Random delay between requests
                delay = random.uniform(settings.min_delay, settings.max_delay)
                await asyncio.sleep(delay)
            
            logger.info("Batch processing completed", 
                       run_id=run_id,
                       total=len(pending_urls),
                       successful=successful,
                       failed=failed)
            
            return {
                "processed": len(pending_urls),
                "successful": successful,
                "failed": failed,
                "run_id": run_id
            }
    
    async def retry_failed_urls(self, run_id: Optional[str] = None) -> dict:
        """Retry processing of failed URLs."""
        if run_id is None:
            run_id = str(uuid.uuid4())
        
        logger.info("Starting retry of failed URLs", run_id=run_id)
        
        async with DatabaseManager() as db:
            self.db = db
            
            # Get failed URLs
            failed_urls = await db.get_failed_urls()
            
            if not failed_urls:
                logger.info("No failed URLs to retry")
                return {"retried": 0, "successful": 0, "failed": 0}
            
            logger.info(f"Found {len(failed_urls)} failed URLs to retry")
            
            # Reset status to pending for retry
            for slug, url, error in failed_urls:
                await db.update_url_status(slug, "pending")
            
            # Process them as pending URLs
            return await self.process_pending_urls(limit=len(failed_urls), run_id=run_id)
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=2))
    async def _navigate_to_page(self, page: Page, url: str) -> None:
        """Navigate to the target page with retry logic."""
        logger.debug("Navigating to page", url=url)
        
        # Use domcontentloaded instead of networkidle to avoid timeouts
        await page.goto(url, wait_until="domcontentloaded", timeout=15000)
        
        # Wait for content to load
        await page.wait_for_load_state("domcontentloaded")
        await asyncio.sleep(3)  # Additional wait for dynamic content
    
    async def _expand_content(self, page: Page) -> None:
        """Expand all collapsed content on the page."""
        expander = ContentExpander()
        await expander.fully_expand(page)
    
    async def _validate_page(self, page: Page) -> dict:
        """Validate the page content."""
        validator = ContentValidator()
        return await validator.validate_page(page)
    
    async def _capture_screenshots(
        self, 
        page: Page, 
        slug: str, 
        run_id: str
    ) -> List[Tuple[str, int, str]]:
        """Capture screenshots of the page."""
        shooter = ScreenshotShooter()
        return await shooter.shoot_sections(page, slug, run_id, settings.output_dir)
    
    async def _save_results(
        self, 
        slug: str, 
        run_id: str, 
        screenshots: List[Tuple[str, int, str]]
    ) -> None:
        """Save screenshot results to database."""
        if not self.db:
            return
        
        for filename, idx, section_title in screenshots:
            await self.db.add_image(run_id, slug, filename, idx, section_title)
    
    async def get_stats(self) -> dict:
        """Get processing statistics."""
        async with DatabaseManager() as db:
            return await db.get_stats()


async def run_discovery(start_urls: Optional[List[str]] = None) -> List[str]:
    """Run URL discovery."""
    async with ScrapingTask() as task:
        return await task.discover_urls(start_urls)


async def run_processing(limit: Optional[int] = None) -> dict:
    """Run processing of pending URLs."""
    async with ScrapingTask() as task:
        return await task.process_pending_urls(limit)


async def run_retry() -> dict:
    """Run retry of failed URLs."""
    async with ScrapingTask() as task:
        return await task.retry_failed_urls()


async def get_processing_stats() -> dict:
    """Get processing statistics."""
    async with ScrapingTask() as task:
        return await task.get_stats() 