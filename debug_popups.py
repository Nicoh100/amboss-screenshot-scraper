#!/usr/bin/env python3
"""
Debug script to identify and handle popups on AMBOSS articles.
"""

import asyncio
import sys
from pathlib import Path

# Add the amboss package to the path
sys.path.insert(0, str(Path(__file__).parent))

from amboss.auth import AuthManager
from amboss.config import settings

async def debug_popups():
    """Debug popups and navigation issues."""
    print("🔍 Debugging AMBOSS popups and navigation...")
    
    # Test URL - this should be a medical article
    test_url = "https://next.amboss.com/de/article/-40DNT"  # Molluscum contagiosum
    
    async with AuthManager() as auth_manager:
        context = await auth_manager.create_context()
        page = await context.new_page()
        
        try:
            print(f"📄 Navigating to: {test_url}")
            await page.goto(test_url, wait_until="domcontentloaded", timeout=30000)
            
            print(f"📍 Current URL: {page.url}")
            
            # Take initial screenshot
            await page.screenshot(path="debug_initial.png")
            print("📸 Initial screenshot saved as debug_initial.png")
            
            # Check for popups and close them
            await handle_popups(page)
            
            # Check if we're on the right page
            title = await page.locator('h1').first.text_content()
            print(f"📝 Page title: {title}")
            
            # Look for article content
            await find_article_content(page)
            
            # Try to navigate to actual article
            await navigate_to_article(page)
            
            # Take final screenshot
            await page.screenshot(path="debug_final.png")
            print("📸 Final screenshot saved as debug_final.png")
            
            return True
            
        except Exception as e:
            print(f"❌ Error: {e}")
            return False
        finally:
            await page.close()
            await context.close()

async def handle_popups(page):
    """Handle various types of popups."""
    print("🔧 Handling popups...")
    
    # Common popup selectors
    popup_selectors = [
        # Cookie consent
        '[data-testid="cookie-banner"] button',
        '.cookie-banner button',
        'button:has-text("Accept")',
        'button:has-text("Akzeptieren")',
        'button:has-text("Accept All")',
        'button:has-text("Alle akzeptieren")',
        
        # Welcome/onboarding popups
        '[data-testid="welcome-modal"] button',
        '.welcome-modal button',
        'button:has-text("Schließen")',
        'button:has-text("Close")',
        'button:has-text("Verstanden")',
        'button:has-text("Got it")',
        
        # Feature announcements
        '[data-testid="announcement"] button',
        '.announcement button',
        'button:has-text("×")',
        'button:has-text("✕")',
        
        # Generic close buttons
        '[aria-label="Close"]',
        '[aria-label="Schließen"]',
        '.close-button',
        '.modal-close'
    ]
    
    for selector in popup_selectors:
        try:
            element = await page.wait_for_selector(selector, timeout=2000)
            if element and await element.is_visible():
                await element.click()
                print(f"✅ Clicked popup: {selector}")
                await page.wait_for_timeout(1000)
                break
        except:
            continue
    
    # Check for modals/overlays
    modal_selectors = [
        '[role="dialog"]',
        '.modal',
        '.overlay',
        '[data-testid="modal"]'
    ]
    
    for selector in modal_selectors:
        try:
            elements = page.locator(selector)
            count = await elements.count()
            if count > 0:
                print(f"⚠️  Found {count} modal/overlay elements: {selector}")
                # Try to close them
                for i in range(count):
                    try:
                        element = elements.nth(i)
                        if await element.is_visible():
                            # Look for close button within modal
                            close_btn = element.locator('button:has-text("×"), button:has-text("✕"), button:has-text("Close"), button:has-text("Schließen")')
                            if await close_btn.count() > 0:
                                await close_btn.first.click()
                                print(f"✅ Closed modal {i}")
                                await page.wait_for_timeout(500)
                    except:
                        continue
        except:
            continue

async def find_article_content(page):
    """Find and verify article content."""
    print("🔍 Looking for article content...")
    
    # Check for article body
    article_selectors = [
        '[data-testid="article-body"]',
        '[data-testid="article-content"]',
        '.article-body',
        '.article-content',
        'article',
        'main'
    ]
    
    for selector in article_selectors:
        try:
            elements = page.locator(selector)
            count = await elements.count()
            if count > 0:
                print(f"✅ Found article content: {selector} ({count} elements)")
                
                # Get some text content
                for i in range(min(count, 3)):
                    try:
                        element = elements.nth(i)
                        text = await element.text_content()
                        if text:
                            preview = text[:200].replace('\n', ' ').strip()
                            print(f"📄 Content preview {i}: {preview}...")
                    except:
                        continue
                return True
        except:
            continue
    
    print("❌ No article content found")
    return False

async def navigate_to_article(page):
    """Try to navigate to the actual article content."""
    print("🔍 Trying to navigate to actual article...")
    
    # Look for article links or navigation
    article_link_selectors = [
        'a[href*="/article/"]',
        'a:has-text("Artikel")',
        'a:has-text("Article")',
        'a:has-text("Lesen")',
        'a:has-text("Read")',
        'button:has-text("Artikel öffnen")',
        'button:has-text("Open article")'
    ]
    
    for selector in article_link_selectors:
        try:
            elements = page.locator(selector)
            count = await elements.count()
            if count > 0:
                print(f"✅ Found {count} article links: {selector}")
                for i in range(count):
                    try:
                        element = elements.nth(i)
                        if await element.is_visible():
                            href = await element.get_attribute('href')
                            text = await element.text_content()
                            print(f"📄 Link {i}: {text} -> {href}")
                            
                            # Click the link
                            await element.click()
                            await page.wait_for_load_state("domcontentloaded", timeout=10000)
                            
                            # Check new title
                            new_title = await page.locator('h1').first.text_content()
                            print(f"📝 New page title: {new_title}")
                            
                            # Take screenshot
                            await page.screenshot(path=f"debug_after_nav_{i}.png")
                            print(f"📸 Screenshot after navigation: debug_after_nav_{i}.png")
                            
                            return True
                    except Exception as e:
                        print(f"⚠️  Error clicking link {i}: {e}")
                        continue
        except:
            continue
    
    # Look for breadcrumbs or navigation
    try:
        breadcrumbs = page.locator('[data-testid="breadcrumb"], .breadcrumb, nav')
        count = await breadcrumbs.count()
        if count > 0:
            print(f"✅ Found {count} navigation elements")
            for i in range(count):
                try:
                    breadcrumb = breadcrumbs.nth(i)
                    text = await breadcrumb.text_content()
                    print(f"🧭 Navigation {i}: {text}")
                except:
                    continue
    except:
        pass
    
    print("❌ Could not navigate to actual article")
    return False

async def main():
    """Main function."""
    success = await debug_popups()
    if success:
        print("✅ Popup debugging completed!")
    else:
        print("❌ Popup debugging failed!")
    return 0 if success else 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code) 