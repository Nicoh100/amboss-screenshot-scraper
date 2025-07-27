"""
Test: Popup handling and content extraction
Hypothesis: The scraper needs to handle popups (privacy, welcome, etc.) before it can access 
and screenshot the actual medical article content.

Purpose: Test popup handling strategies and verify we can get to the actual article content
before taking screenshots.

Expected Outcome: Should successfully handle all popups and capture screenshots of the 
actual medical article content, not UI elements.
"""

import asyncio
from pathlib import Path
from amboss.auth import AuthManager
from amboss.config import settings
from amboss.expander import ContentExpander
from amboss.shooter import ScreenshotShooter

async def test_popup_handling():
    """Test popup handling and content extraction."""
    test_url = "https://next.amboss.com/de/article/--0D-i"
    
    print(f"Testing popup handling for: {test_url}")
    print("-" * 60)
    
    async with AuthManager() as auth_manager:
        context = await auth_manager.create_context()
        page = await context.new_page()
        
        try:
            # Step 1: Navigate to the article
            print("1. Navigating to article...")
            await page.goto(test_url, wait_until="domcontentloaded", timeout=15000)
            await asyncio.sleep(3)
            
            # Step 2: Handle popups systematically
            print("2. Handling popups...")
            await handle_all_popups(page)
            
            # Step 3: Verify we're on actual content
            print("3. Verifying content...")
            content_verified = await verify_medical_content(page)
            
            if not content_verified:
                print("   ❌ Still not on medical content after popup handling")
                return False
            
            # Step 4: Test screenshot capture
            print("4. Testing screenshot capture...")
            test_dir = Path("test_captures")
            test_dir.mkdir(exist_ok=True)
            
            shooter = ScreenshotShooter()
            screenshots = await shooter.shoot_sections(page, "--0D-i", "test_run", test_dir)
            
            print(f"   ✅ Captured {len(screenshots)} screenshots")
            for filename, idx, title in screenshots:
                print(f"      {filename}: {title}")
            
            return True
            
        except Exception as e:
            print(f"   ❌ ERROR: {e}")
            return False
        finally:
            await page.close()
            await context.close()

async def handle_all_popups(page):
    """Handle all common popups that might appear."""
    
    # Common popup selectors
    popup_selectors = [
        # Privacy/cookie consent
        '[data-testid="cookie-banner"] button',
        '.cookie-banner button',
        'button:has-text("Akzeptieren")',
        'button:has-text("Accept")',
        'button:has-text("Accept All")',
        'button:has-text("Alle akzeptieren")',
        
        # Welcome/onboarding popups
        'button:has-text("Schließen")',
        'button:has-text("Close")',
        '[data-testid="close-button"]',
        '.close-button',
        '.modal-close',
        
        # Feature tour popups
        'button:has-text("Überspringen")',
        'button:has-text("Skip")',
        'button:has-text("Weiter")',
        'button:has-text("Next")',
        
        # Any button that might close something
        'button[aria-label*="close"]',
        'button[aria-label*="Close"]',
        '[role="button"]:has-text("×")',
        '[role="button"]:has-text("✕")'
    ]
    
    for selector in popup_selectors:
        try:
            elements = page.locator(selector)
            count = await elements.count()
            if count > 0:
                for i in range(count):
                    element = elements.nth(i)
                    if await element.is_visible():
                        print(f"   Clicking popup: {selector}")
                        await element.click()
                        await asyncio.sleep(1)
        except Exception as e:
            continue
    
    # Wait a bit for any animations to complete
    await asyncio.sleep(2)

async def verify_medical_content(page):
    """Verify we're on actual medical content, not UI elements."""
    
    # Check for medical content indicators
    medical_indicators = [
        "Diagnostik",
        "Therapie",
        "Epidemiologie", 
        "Ätiologie",
        "Symptome",
        "Behandlung",
        "Pränataldiagnostik"
    ]
    
    # Get page text
    body_text = await page.locator('body').text_content()
    
    # Check if any medical terms are present
    for term in medical_indicators:
        if term in body_text:
            print(f"   ✅ Found medical content: {term}")
            return True
    
    # Check for UI elements we don't want
    ui_indicators = [
        "Schlüsselfunktionen",
        "Willkommen",
        "Datenschutz",
        "Cookie",
        "Privacy"
    ]
    
    for term in ui_indicators:
        if term in body_text:
            print(f"   ❌ Still showing UI: {term}")
            return False
    
    print("   ⚠️ No clear medical content found")
    return False

if __name__ == "__main__":
    success = asyncio.run(test_popup_handling())
    print(f"\nOverall result: {'SUCCESS' if success else 'FAILED'}") 