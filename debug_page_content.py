"""
Debug script to see what content is actually on the page.
"""

import asyncio
from amboss.auth import AuthManager

async def debug_page_content():
    """Debug what content is actually on the page."""
    
    test_url = "https://next.amboss.com/de/article/--0D-i"
    print(f"Navigating to: {test_url}")
    
    async with AuthManager() as auth_manager:
        context = await auth_manager.create_context()
        page = await context.new_page()
        
        try:
            # Navigate to the page
            print("1. Navigating to page...")
            await page.goto(test_url, wait_until="domcontentloaded", timeout=15000)
            await asyncio.sleep(3)
            
            # Get the page title
            title = await page.title()
            print(f"2. Page title: {title}")
            
            # Get the main heading
            try:
                h1 = await page.locator('h1').first.text_content()
                print(f"3. Main H1: {h1}")
            except:
                print("3. No H1 found")
            
            # Get all headings
            headings = await page.locator('h1, h2, h3').all_text_contents()
            print(f"4. All headings: {headings[:5]}")  # First 5 headings
            
            # Get page URL
            current_url = page.url
            print(f"5. Current URL: {current_url}")
            
            # Check for medical content indicators
            body_text = await page.locator('body').text_content()
            medical_terms = ["Pränataldiagnostik", "Diagnostik", "Therapie", "Epidemiologie", "Ätiologie"]
            
            print("6. Medical content check:")
            for term in medical_terms:
                if term in body_text:
                    print(f"   ✅ Found: {term}")
                else:
                    print(f"   ❌ Missing: {term}")
            
            # Check for UI elements we don't want
            ui_terms = ["Willkommen", "Rabatt", "Fortbildung", "Schlüsselfunktionen", "Cookie", "Datenschutz"]
            print("7. UI content check:")
            for term in ui_terms:
                if term in body_text:
                    print(f"   ⚠️ Found UI: {term}")
            
            # Take a screenshot for inspection
            await page.screenshot(path="debug_page_content.png", full_page=True)
            print("8. Screenshot saved as debug_page_content.png")
            
        except Exception as e:
            print(f"Error: {e}")
        finally:
            await page.close()
            await context.close()

if __name__ == "__main__":
    asyncio.run(debug_page_content()) 