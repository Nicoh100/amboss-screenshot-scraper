"""URL discovery and crawling for AMBOSS articles."""

import re
import asyncio
from typing import AsyncIterator, List, Set, Optional
from urllib.parse import urljoin, urlparse

import aiohttp
from structlog import get_logger
from tenacity import retry, stop_after_attempt, wait_exponential

from .config import settings
from .db import DatabaseManager

logger = get_logger(__name__)


class URLDiscoverer:
    """Discovers AMBOSS article URLs through crawling."""
    
    def __init__(self):
        self.slug_pattern = re.compile(settings.article_pattern)
        self.discovered_urls: Set[str] = set()
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession(
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=2))
    async def fetch_html(self, url: str) -> str:
        """Fetch HTML content from a URL with retry logic."""
        try:
            async with self.session.get(url, timeout=30) as response:
                response.raise_for_status()
                return await response.text()
        except Exception as e:
            logger.error("Failed to fetch URL", url=url, error=str(e))
            raise
    
    def extract_slugs(self, html: str, base_url: str) -> List[str]:
        """Extract article slugs from HTML content."""
        slugs = []
        for match in self.slug_pattern.finditer(html):
            full_url = match.group(0)
            if full_url not in self.discovered_urls:
                self.discovered_urls.add(full_url)
                slugs.append(full_url)
        return slugs
    
    def extract_links(self, html: str, base_url: str) -> List[str]:
        """Extract all links from HTML content."""
        # Simple regex to find href attributes
        href_pattern = re.compile(r'href=["\']([^"\']+)["\']')
        links = []
        
        for match in href_pattern.finditer(html):
            href = match.group(1)
            
            # Skip external links, anchors, and non-HTTP links
            if href.startswith(('#', 'javascript:', 'mailto:', 'tel:')):
                continue
            
            # Resolve relative URLs
            if href.startswith('/'):
                full_url = urljoin(base_url, href)
            elif href.startswith('http'):
                # Only include AMBOSS URLs
                if settings.base_url in href:
                    full_url = href
                else:
                    continue
            else:
                full_url = urljoin(base_url, href)
            
            # Normalize URL
            parsed = urlparse(full_url)
            normalized = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
            if parsed.query:
                normalized += f"?{parsed.query}"
            
            links.append(normalized)
        
        return list(set(links))  # Remove duplicates
    
    async def discover_from_start_urls(self, start_urls: List[str]) -> AsyncIterator[str]:
        """Discover article URLs starting from given URLs."""
        queue = asyncio.Queue()
        visited = set()
        
        # Add start URLs to queue
        for url in start_urls:
            await queue.put(url)
        
        while not queue.empty():
            url = await queue.get()
            
            if url in visited:
                continue
            
            visited.add(url)
            logger.info("Discovering from URL", url=url)
            
            try:
                html = await self.fetch_html(url)
                
                # Extract article slugs
                slugs = self.extract_slugs(html, url)
                for slug_url in slugs:
                    yield slug_url
                
                # Extract additional links for further crawling
                links = self.extract_links(html, url)
                for link in links:
                    if link not in visited and link not in [item for item in queue._queue]:
                        await queue.put(link)
                
                # Rate limiting
                await asyncio.sleep(1)  # 1 second delay between requests
                
            except Exception as e:
                logger.error("Failed to process URL", url=url, error=str(e))
                continue
    
    async def discover_articles(self, start_urls: Optional[List[str]] = None) -> List[str]:
        """Discover all article URLs and save to database."""
        if start_urls is None:
            start_urls = [
                f"{settings.base_url}/de/article",
                f"{settings.base_url}/de/knowledge",
                f"{settings.base_url}/de/library"
            ]
        
        discovered_urls = []
        
        async with self:
            async with DatabaseManager() as db:
                async for url in self.discover_from_start_urls(start_urls):
                    # Extract slug from URL
                    match = self.slug_pattern.match(url)
                    if match:
                        slug = match.group(1)
                        
                        # Add to database
                        success = await db.add_url(slug, url)
                        if success:
                            discovered_urls.append(url)
                            logger.info("Discovered article", slug=slug, url=url)
        
        logger.info("Discovery completed", total_discovered=len(discovered_urls))
        return discovered_urls


async def discover_articles(start_urls: Optional[List[str]] = None) -> List[str]:
    """Convenience function to discover articles."""
    discoverer = URLDiscoverer()
    return await discoverer.discover_articles(start_urls)


async def get_discovery_stats() -> dict:
    """Get statistics about discovered URLs."""
    async with DatabaseManager() as db:
        stats = await db.get_stats()
        return stats 