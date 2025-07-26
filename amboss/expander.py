"""Content expansion module for AMBOSS articles."""

import asyncio
from typing import List, Optional

from playwright.async_api import Page
from structlog import get_logger
from tenacity import retry, stop_after_attempt, wait_exponential

from .config import settings

logger = get_logger(__name__)


class ExpansionFailure(Exception):
    """Raised when content expansion fails."""
    pass


class ContentExpander:
    """Handles expansion of collapsed content in AMBOSS articles."""
    
    def __init__(self):
        self.expand_selectors = [
            "[data-e2e-test-id='section-content-is-hidden']",
            "text='Weiterlesen'",
            "text='Read more'",
            "text='Mehr anzeigen'",
            "text='Show more'",
            "[data-testid='expand-button']",
            ".expand-button",
            ".read-more-button"
        ]
    
    @retry(stop=stop_after_attempt(4), wait=wait_exponential(multiplier=2))
    async def fully_expand(self, page: Page) -> None:
        """Expand all collapsed sections using multiple strategies."""
        logger.info("Starting content expansion")
        
        # Strategy 1: Click-based expansion
        await self._click_expansion_buttons(page)
        
        # Strategy 2: JavaScript fallback for stubborn elements
        await self._js_expansion_fallback(page)
        
        # Strategy 3: Wait for dynamic content
        await self._wait_for_dynamic_content(page)
        
        # Strategy 4: Final verification
        await self._verify_expansion(page)
        
        logger.info("Content expansion completed")
    
    async def _click_expansion_buttons(self, page: Page) -> None:
        """Click all visible expansion buttons."""
        for selector in self.expand_selectors:
            try:
                elements = page.locator(selector)
                count = await elements.count()
                
                if count > 0:
                    logger.info(f"Found {count} elements with selector: {selector}")
                    
                    # Click each element
                    for i in range(count):
                        try:
                            element = elements.nth(i)
                            if await element.is_visible():
                                await element.click(force=True)
                                await page.wait_for_timeout(settings.expansion_delay)
                                logger.debug(f"Clicked element {i} with selector: {selector}")
                        except Exception as e:
                            logger.warning(f"Failed to click element {i} with selector {selector}", error=str(e))
                            continue
                            
            except Exception as e:
                logger.warning(f"Error processing selector {selector}", error=str(e))
                continue
    
    async def _js_expansion_fallback(self, page: Page) -> None:
        """Use JavaScript to expand stubborn elements."""
        try:
            # JavaScript to click all hidden content elements
            js_code = """
            () => {
                const selectors = [
                    '[data-e2e-test-id="section-content-is-hidden"]',
                    '[data-testid="expand-button"]',
                    '.expand-button',
                    '.read-more-button'
                ];
                
                let totalClicked = 0;
                
                selectors.forEach(selector => {
                    const elements = document.querySelectorAll(selector);
                    elements.forEach(el => {
                        if (el.offsetParent !== null) { // Check if visible
                            el.click();
                            totalClicked++;
                        }
                    });
                });
                
                return totalClicked;
            }
            """
            
            clicked_count = await page.evaluate(js_code)
            if clicked_count > 0:
                logger.info(f"JavaScript fallback clicked {clicked_count} elements")
                await page.wait_for_timeout(settings.expansion_delay * 2)
                
        except Exception as e:
            logger.warning("JavaScript expansion fallback failed", error=str(e))
    
    async def _wait_for_dynamic_content(self, page: Page) -> None:
        """Wait for dynamic content to load after expansion."""
        try:
            # Wait for network to be idle
            await page.wait_for_load_state("networkidle", timeout=10000)
            
            # Wait for any animations to complete
            await page.wait_for_timeout(1000)
            
            # Check for loading indicators and wait if present
            loading_selectors = [
                "[data-testid='loading']",
                ".loading",
                ".spinner",
                "[aria-busy='true']"
            ]
            
            for selector in loading_selectors:
                try:
                    loading_element = page.locator(selector)
                    if await loading_element.is_visible():
                        logger.info(f"Waiting for loading indicator: {selector}")
                        await loading_element.wait_for(state="hidden", timeout=10000)
                except:
                    continue
                    
        except Exception as e:
            logger.warning("Error waiting for dynamic content", error=str(e))
    
    async def _verify_expansion(self, page: Page) -> None:
        """Verify that all content has been expanded."""
        try:
            # Check for remaining hidden content
            hidden_selectors = [
                "[data-e2e-test-id='section-content-is-hidden']",
                "text='Weiterlesen'",
                "text='Read more'"
            ]
            
            total_hidden = 0
            for selector in hidden_selectors:
                try:
                    elements = page.locator(selector)
                    count = await elements.count()
                    if count > 0:
                        # Check if any are actually visible (might be false positives)
                        visible_count = 0
                        for i in range(count):
                            element = elements.nth(i)
                            if await element.is_visible():
                                visible_count += 1
                        
                        if visible_count > 0:
                            total_hidden += visible_count
                            logger.warning(f"Found {visible_count} still-visible elements with selector: {selector}")
                            
                except Exception as e:
                    logger.warning(f"Error checking selector {selector}", error=str(e))
                    continue
            
            if total_hidden > 0:
                raise ExpansionFailure(f"{total_hidden} sections still hidden after expansion")
            
            logger.info("Expansion verification passed - all content expanded")
            
        except Exception as e:
            if isinstance(e, ExpansionFailure):
                raise
            logger.error("Error during expansion verification", error=str(e))
            raise ExpansionFailure(f"Expansion verification failed: {str(e)}")
    
    async def get_content_metrics(self, page: Page) -> dict:
        """Get metrics about the page content."""
        try:
            # Count various content elements
            metrics = {}
            
            # Count headings
            headings = page.locator("h1, h2, h3, h4, h5, h6")
            metrics["headings"] = await headings.count()
            
            # Count paragraphs
            paragraphs = page.locator("p")
            metrics["paragraphs"] = await paragraphs.count()
            
            # Count lists
            lists = page.locator("ul, ol")
            metrics["lists"] = await lists.count()
            
            # Count tables
            tables = page.locator("table")
            metrics["tables"] = await tables.count()
            
            # Count images
            images = page.locator("img")
            metrics["images"] = await images.count()
            
            # Count expansion buttons (should be 0 if fully expanded)
            expand_buttons = page.locator("[data-e2e-test-id='section-content-is-hidden']")
            metrics["remaining_expand_buttons"] = await expand_buttons.count()
            
            # Get page height
            page_height = await page.evaluate("document.body.scrollHeight")
            metrics["page_height"] = page_height
            
            return metrics
            
        except Exception as e:
            logger.error("Error getting content metrics", error=str(e))
            return {}
    
    async def is_fully_expanded(self, page: Page) -> bool:
        """Check if the page is fully expanded."""
        try:
            # Check for any remaining expansion buttons
            expand_buttons = page.locator("[data-e2e-test-id='section-content-is-hidden']")
            count = await expand_buttons.count()
            
            if count == 0:
                return True
            
            # Check if any remaining buttons are actually visible
            visible_count = 0
            for i in range(count):
                element = expand_buttons.nth(i)
                if await element.is_visible():
                    visible_count += 1
            
            return visible_count == 0
            
        except Exception as e:
            logger.error("Error checking expansion status", error=str(e))
            return False


async def expand_content(page: Page) -> None:
    """Convenience function to expand content on a page."""
    expander = ContentExpander()
    await expander.fully_expand(page) 