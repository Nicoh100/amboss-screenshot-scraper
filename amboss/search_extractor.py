"""Search results URL extractor for AMBOSS articles."""

import asyncio
import re
from pathlib import Path
from typing import List, Set
from urllib.parse import urlparse

from playwright.async_api import Page
from structlog import get_logger
from tenacity import retry, stop_after_attempt, wait_exponential

from .auth import AuthManager
from .config import settings

logger = get_logger(__name__)


class SearchExtractor:
    """Extracts article URLs from AMBOSS search results page."""

    def __init__(self):
        self.article_pattern = re.compile(r'https://next\.amboss\.com/de/article/([a-zA-Z0-9-]+)')
        self.extracted_urls: Set[str] = set()
        self.auth_manager = None

    async def __aenter__(self):
        """Async context manager entry."""
        self.auth_manager = AuthManager()
        await self.auth_manager.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.auth_manager:
            await self.auth_manager.__aexit__(exc_type, exc_val, exc_tb)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=2))
    async def extract_article_urls(self, search_url: str = "https://next.amboss.com/de/search?q=&v=article") -> List[str]:
        """Extract all article URLs from the search results page."""
        logger.info("Starting article URL extraction", url=search_url)

        # Create browser context
        context = await self.auth_manager.create_context()
        page = await context.new_page()

        try:
            # Navigate to search page
            await page.goto(search_url, wait_until="networkidle")
            logger.info("Loaded search page")

            # Verify authentication
            if not await self.auth_manager.verify_auth(page):
                raise Exception("Authentication failed - cannot access search page")

            # Expand all results by clicking "Mehr anzeigen" until no more
            await self._expand_all_results(page)

            # Extract all article URLs
            urls = await self._extract_urls_from_page(page)

            # Remove duplicates and fragments
            clean_urls = self._clean_urls(urls)

            logger.info("URL extraction completed", 
                       total_found=len(urls), 
                       unique_clean=len(clean_urls))

            return clean_urls

        finally:
            await page.close()
            await context.close()

    async def _expand_all_results(self, page: Page) -> None:
        """Click 'Mehr anzeigen' until all results are visible."""
        logger.info("Expanding all search results")

        max_attempts = 50  # Prevent infinite loops
        attempts = 0
        last_count = 0

        while attempts < max_attempts:
            try:
                # Look for "Mehr anzeigen" button
                mehr_anzeigen_selectors = [
                    "text='Mehr anzeigen'",
                    "text='Show more'",
                    "[data-testid='load-more-button']",
                    ".load-more-button",
                    "button:has-text('Mehr anzeigen')",
                    "button:has-text('Show more')"
                ]

                button_found = False
                for selector in mehr_anzeigen_selectors:
                    try:
                        button = page.locator(selector)
                        if await button.is_visible():
                            # Scroll button into view
                            await button.scroll_into_view_if_needed()
                            await page.wait_for_timeout(500)

                            # Click the button
                            await button.click()
                            logger.info(f"Clicked 'Mehr anzeigen' button (attempt {attempts + 1})")
                            
                            # Wait for new content to load
                            await page.wait_for_load_state("networkidle")
                            await page.wait_for_timeout(1000)  # Additional wait for dynamic content
                            
                            button_found = True
                            break
                    except Exception as e:
                        logger.debug(f"Selector {selector} not found or not clickable", error=str(e))
                        continue

                if not button_found:
                    logger.info("No more 'Mehr anzeigen' buttons found - all results loaded")
                    break

                # Check if we're making progress (optional)
                current_count = await self._count_article_links(page)
                if current_count == last_count:
                    logger.info("No new results loaded, stopping expansion")
                    break
                
                last_count = current_count
                attempts += 1

            except Exception as e:
                logger.warning(f"Error during expansion attempt {attempts + 1}", error=str(e))
                attempts += 1
                await page.wait_for_timeout(2000)  # Wait before retry

        if attempts >= max_attempts:
            logger.warning("Reached maximum expansion attempts")

    async def _count_article_links(self, page: Page) -> int:
        """Count current article links on the page."""
        try:
            # Count links that match our article pattern
            links = page.locator("a[href*='/de/article/']")
            count = await links.count()
            return count
        except Exception as e:
            logger.debug("Error counting article links", error=str(e))
            return 0

    async def _extract_urls_from_page(self, page: Page) -> List[str]:
        """Extract all article URLs from the current page content."""
        try:
            # Get all href attributes from links
            urls = await page.evaluate("""
                () => {
                    const links = document.querySelectorAll('a[href]');
                    const urls = [];
                    for (const link of links) {
                        const href = link.href;
                        if (href && href.includes('/de/article/')) {
                            urls.push(href);
                        }
                    }
                    return urls;
                }
            """)

            logger.info(f"Found {len(urls)} article links on page")
            return urls

        except Exception as e:
            logger.error("Error extracting URLs from page", error=str(e))
            return []

    def _clean_urls(self, urls: List[str]) -> List[str]:
        """Clean URLs by removing fragments and duplicates."""
        clean_urls = set()

        for url in urls:
            # Parse URL to remove fragments
            parsed = urlparse(url)
            clean_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
            
            # Only include URLs that match our exact pattern
            if self.article_pattern.match(url):
                clean_urls.add(clean_url)

        # Convert back to list and sort for consistent output
        return sorted(list(clean_urls))

    async def save_urls_to_file(self, urls: List[str], output_file: str = "amboss-article-urls.md") -> None:
        """Save extracted URLs to a markdown file."""
        output_path = Path(output_file)
        
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                for url in urls:
                    f.write(f"{url}\n")

            logger.info(f"Saved {len(urls)} URLs to {output_path}")

        except Exception as e:
            logger.error(f"Error saving URLs to file", file=str(output_path), error=str(e))
            raise


async def extract_and_save_urls(
    search_url: str = "https://next.amboss.com/de/search?q=&v=article",
    output_file: str = "amboss-article-urls.md"
) -> List[str]:
    """Convenience function to extract and save article URLs."""
    async with SearchExtractor() as extractor:
        urls = await extractor.extract_article_urls(search_url)
        await extractor.save_urls_to_file(urls, output_file)
        return urls


async def main():
    """Main function for standalone execution."""
    try:
        urls = await extract_and_save_urls()
        print(f"Successfully extracted {len(urls)} unique article URLs")
        print(f"Results saved to: amboss-article-urls.md")
        
        # Print first few URLs as preview
        if urls:
            print("\nFirst 5 URLs:")
            for url in urls[:5]:
                print(f"  {url}")
            if len(urls) > 5:
                print(f"  ... and {len(urls) - 5} more")
                
    except Exception as e:
        logger.error("Failed to extract URLs", error=str(e))
        raise


if __name__ == "__main__":
    asyncio.run(main()) 