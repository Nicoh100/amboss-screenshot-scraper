#!/usr/bin/env python3
"""
Fast AMBOSS Article URL Extractor

Extracts all unique article URLs from https://next.amboss.com/de/search?q=&v=article
by clicking "Mehr anzeigen" until all results are visible, then extracting URLs
of the format: https://next.amboss.com/de/article/XXXXXX

Output: amboss-article-urls.md (one URL per line, no metadata)
"""

import asyncio
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

# Add the amboss package to the path
sys.path.insert(0, str(Path(__file__).parent))

from amboss.auth import AuthManager
from amboss.config import settings


class FastURLExtractor:
    """Fast URL extractor for AMBOSS search results."""
    
    def __init__(self):
        self.article_pattern = re.compile(r'https://next\.amboss\.com/de/article/([a-zA-Z0-9-]+)')
        self.extracted_urls = set()
    
    async def extract_urls(self) -> list:
        """Extract all article URLs from the search page."""
        print("🚀 Starting fast URL extraction...")
        print("📍 Target: https://next.amboss.com/de/search?q=&v=article")
        
        async with AuthManager() as auth_manager:
            context = await auth_manager.create_context()
            page = await context.new_page()
            
            try:
                # Navigate to search page
                print("📄 Loading search page...")
                await page.goto("https://next.amboss.com/de/search?q=&v=article", wait_until="networkidle")
                
                # Verify authentication
                if not await auth_manager.verify_auth(page):
                    raise Exception("❌ Authentication failed - cannot access search page")
                
                print("✅ Authentication verified")
                
                # Expand all results
                print("🔄 Expanding all results (clicking 'Mehr anzeigen')...")
                await self._expand_all_results(page)
                
                # Extract URLs
                print("🔍 Extracting article URLs...")
                urls = await self._extract_urls_from_page(page)
                
                # Clean and deduplicate
                clean_urls = self._clean_urls(urls)
                
                print(f"✅ Found {len(clean_urls)} unique article URLs")
                return clean_urls
                
            finally:
                await page.close()
                await context.close()
    
    async def _expand_all_results(self, page):
        """Click 'Mehr anzeigen' until all results are visible."""
        max_attempts = 50
        attempts = 0
        
        while attempts < max_attempts:
            try:
                # Look for "Mehr anzeigen" button
                button_selectors = [
                    "text='Mehr anzeigen'",
                    "text='Show more'",
                    "[data-testid='load-more-button']",
                    ".load-more-button",
                    "button:has-text('Mehr anzeigen')"
                ]
                
                button_found = False
                for selector in button_selectors:
                    try:
                        button = page.locator(selector)
                        if await button.is_visible():
                            await button.scroll_into_view_if_needed()
                            await page.wait_for_timeout(300)
                            await button.click()
                            print(f"  📍 Clicked 'Mehr anzeigen' (attempt {attempts + 1})")
                            await page.wait_for_load_state("networkidle")
                            await page.wait_for_timeout(800)
                            button_found = True
                            break
                    except:
                        continue
                
                if not button_found:
                    print("  ✅ No more 'Mehr anzeigen' buttons found")
                    break
                
                attempts += 1
                
            except Exception as e:
                print(f"  ⚠️  Error during expansion: {e}")
                attempts += 1
                await page.wait_for_timeout(1000)
        
        if attempts >= max_attempts:
            print("  ⚠️  Reached maximum expansion attempts")
    
    async def _extract_urls_from_page(self, page):
        """Extract all article URLs from the page."""
        try:
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
            return urls
        except Exception as e:
            print(f"❌ Error extracting URLs: {e}")
            return []
    
    def _clean_urls(self, urls):
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
    
    def save_to_file(self, urls, filename="amboss-article-urls.md"):
        """Save URLs to file, one per line."""
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                for url in urls:
                    f.write(f"{url}\n")
            
            print(f"💾 Saved {len(urls)} URLs to {filename}")
            return True
            
        except Exception as e:
            print(f"❌ Error saving to file: {e}")
            return False


async def main():
    """Main function."""
    try:
        extractor = FastURLExtractor()
        urls = await extractor.extract_urls()
        
        if urls:
            success = extractor.save_to_file(urls)
            if success:
                print("\n🎉 Extraction completed successfully!")
                print(f"📊 Total URLs: {len(urls)}")
                
                # Show preview
                print("\n📋 First 5 URLs:")
                for url in urls[:5]:
                    print(f"  {url}")
                if len(urls) > 5:
                    print(f"  ... and {len(urls) - 5} more")
                
                print(f"\n📄 Full results saved to: amboss-article-urls.md")
            else:
                print("❌ Failed to save results")
                return 1
        else:
            print("❌ No URLs found")
            return 1
            
    except Exception as e:
        print(f"❌ Extraction failed: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code) 