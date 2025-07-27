#!/usr/bin/env python3
"""
Fast AMBOSS Article Processor

Reads article URLs from amboss_all_articles_links.txt and processes them
for screenshot capture with intelligent content expansion and validation.

This script is optimized for speed and efficiency using the existing URL list.
"""

import asyncio
import re
import sys
from pathlib import Path
from typing import List, Optional, Tuple
from urllib.parse import urlparse

# Add the amboss package to the path
sys.path.insert(0, str(Path(__file__).parent))

from amboss.auth import AuthManager
from amboss.config import settings
from amboss.expander import ContentExpander, ExpansionFailure
from amboss.shooter import ScreenshotShooter
from amboss.validator import ContentValidator, ValidationFailure


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
        print(f"📖 Reading URLs from {filename}...")
        
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
            
            print(f"✅ Extracted {len(urls)} valid article URLs")
            return urls
            
        except FileNotFoundError:
            print(f"❌ File {filename} not found!")
            return []
        except Exception as e:
            print(f"❌ Error reading file: {e}")
            return []
    
    async def process_article(self, url: str, auth_manager: AuthManager) -> Tuple[bool, Optional[str]]:
        """Process a single article URL."""
        context = None
        page = None
        try:
            # Extract slug from URL
            match = self.article_pattern.match(url)
            if not match:
                return False, "Invalid URL format"
            
            slug = match.group(1)
            print(f"🔄 Processing: {slug}")
            
            # Create browser context
            context = await auth_manager.create_context()
            page = await context.new_page()
            
            # Navigate to article with shorter timeout
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            
            # Verify authentication on the article page
            if not await auth_manager.verify_auth(page):
                return False, "Authentication failed"
            
            # Expand all content
            await self.expander.fully_expand(page)
            
            # Validate content (only expansion, no density check)
            validation_result = await self.validator.validate_page(page)
            if not validation_result.get('validation_passed', False):
                return False, f"Validation failed: {validation_result.get('errors', [])}"
            
            # Capture screenshots
            output_dir = settings.output_dir
            output_dir.mkdir(parents=True, exist_ok=True)
            
            screenshots = await self.shooter.shoot_sections(page, slug, f"run_{self.processed_count}", output_dir)
            
            print(f"✅ Success: {slug} - {len(screenshots)} screenshots captured")
            return True, None
                
        except ExpansionFailure as e:
            return False, f"Expansion failed: {e}"
        except ValidationFailure as e:
            return False, f"Validation failed: {e}"
        except Exception as e:
            return False, f"Processing error: {e}"
        finally:
            # Always close page and context
            if page:
                try:
                    await page.close()
                except:
                    pass
            if context:
                try:
                    await context.close()
                except:
                    pass
    
    async def process_all_articles(self, urls: List[str], limit: Optional[int] = None) -> dict:
        """Process all articles with rate limiting."""
        print(f"🚀 Starting processing of {len(urls)} articles...")
        if limit:
            urls = urls[:limit]
            print(f"📊 Limited to first {limit} articles")
        
        # Initialize auth manager
        async with AuthManager() as auth_manager:
            # Skip initial auth verification - we'll check on each article
            print("✅ Authentication manager initialized")
            
            # Process articles with rate limiting
            for i, url in enumerate(urls):
                self.processed_count += 1
                
                success, error = await self.process_article(url, auth_manager)
                
                if success:
                    self.success_count += 1
                else:
                    self.failed_count += 1
                    print(f"❌ Failed: {error}")
                
                # Rate limiting - wait between requests
                if i < len(urls) - 1:  # Don't wait after the last one
                    delay = settings.min_delay + (settings.max_delay - settings.min_delay) * (i % 10) / 10
                    print(f"⏳ Waiting {delay:.1f}s before next request...")
                    await asyncio.sleep(delay)
                
                # Progress update
                if (i + 1) % 10 == 0:
                    print(f"📊 Progress: {i + 1}/{len(urls)} processed")
        
        return {
            'total': len(urls),
            'processed': self.processed_count,
            'successful': self.success_count,
            'failed': self.failed_count,
            'success_rate': self.success_count / len(urls) if urls else 0
        }


async def main():
    """Main function."""
    try:
        processor = FastAMBOSSProcessor()
        
        # Extract URLs from existing file
        urls = processor.extract_urls_from_file()
        
        if not urls:
            print("❌ No URLs found. Exiting.")
            return 1
        
        # Process articles (you can set a limit for testing)
        result = await processor.process_all_articles(urls, limit=3)  # Test with first 3
        # result = await processor.process_all_articles(urls)  # Process all
        
        # Print results
        print("\n🎉 Processing completed!")
        print(f"📊 Results:")
        print(f"  Total URLs: {result['total']}")
        print(f"  Processed: {result['processed']}")
        print(f"  Successful: {result['successful']}")
        print(f"  Failed: {result['failed']}")
        print(f"  Success Rate: {result['success_rate']:.1%}")
        
        return 0
        
    except Exception as e:
        print(f"❌ Processing failed: {e}")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code) 