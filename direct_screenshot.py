"""
Direct screenshot tool - no discovery, just screenshot specific URLs.
"""

import asyncio
import sys
from pathlib import Path
from amboss.auth import AuthManager
from amboss.shooter import ScreenshotShooter
from amboss.config import settings

async def screenshot_article(url: str, slug: str = None):
    """Screenshot a specific article URL."""
    
    if slug is None:
        # Extract slug from URL
        slug = url.split("/")[-1]
    
    print(f"🎯 Screenshotting: {slug}")
    print(f"📄 URL: {url}")
    
    async with AuthManager() as auth_manager:
        context = await auth_manager.create_context()
        page = await context.new_page()
        
        try:
            # Navigate to the article
            print("🔍 Navigating to article...")
            await page.goto(url, wait_until="domcontentloaded", timeout=15000)
            await asyncio.sleep(3)
            
            # Comprehensive popup handling and content expansion
            print("🔧 Handling popups and expanding content...")
            from amboss.expander import ContentExpander
            expander = ContentExpander()
            
            # Handle popups and expand all sections
            await expander.fully_expand(page)
            
            # Verify content is expanded
            if not await expander.verify_content_is_expanded(page):
                print("⚠️  Warning: Content may not be fully expanded")
            
            # Scroll to reveal any remaining content
            print("📜 Scrolling to reveal content...")
            await page.evaluate("window.scrollTo(0, 1000)")
            await asyncio.sleep(2)
            
            # Create output directory with unique run ID
            import datetime
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            run_id = f"direct_screenshot_{timestamp}"
            outdir = settings.output_dir
            slug_dir = outdir / slug / run_id
            slug_dir.mkdir(parents=True, exist_ok=True)
            
            # Take screenshot using the shooter
            print("📸 Taking screenshot...")
            shooter = ScreenshotShooter()
            screenshots = await shooter.shoot_sections(page, slug, run_id, outdir)
            
            print(f"✅ Screenshots saved: {len(screenshots)} files")
            for filename, idx, title in screenshots:
                print(f"  📄 {filename} - {title}")
            
            return screenshots
            
        except Exception as e:
            print(f"❌ Error: {e}")
            return []
        finally:
            await page.close()
            await context.close()

async def main():
    """Main function."""
    if len(sys.argv) < 2:
        print("Usage: python direct_screenshot.py <URL> [slug]")
        print("Example: python direct_screenshot.py https://next.amboss.com/de/article/--0D-i")
        return
    
    url = sys.argv[1]
    slug = sys.argv[2] if len(sys.argv) > 2 else None
    
    await screenshot_article(url, slug)

if __name__ == "__main__":
    asyncio.run(main()) 