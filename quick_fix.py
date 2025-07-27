"""
Quick fix to scroll and capture the actual medical content.
"""

import asyncio
from amboss.auth import AuthManager
from amboss.expander import ContentExpander

async def quick_fix():
    """Quick test to get the actual medical content."""
    
    test_url = "https://next.amboss.com/de/article/--0D-i"
    
    async with AuthManager() as auth_manager:
        context = await auth_manager.create_context()
        page = await context.new_page()
        
        try:
            print("🔍 Navigating to article...")
            await page.goto(test_url, wait_until="domcontentloaded", timeout=15000)
            await asyncio.sleep(3)
            
            # Handle popups
            expander = ContentExpander()
            await expander._handle_cookie_consent(page)
            await asyncio.sleep(2)
            
            # Scroll down to reveal more content
            print("📜 Scrolling to reveal content...")
            await page.evaluate("window.scrollTo(0, 1000)")
            await asyncio.sleep(2)
            
            # Take screenshot with your exact parameters
            clip = {
                "x": 250,
                "y": 56,
                "width": 848,
                "height": 2000  # Start with smaller height to test
            }
            
            print("📸 Taking screenshot...")
            await page.screenshot(path="test_medical_content.png", clip=clip)
            print("✅ Screenshot saved: test_medical_content.png")
            
        except Exception as e:
            print(f"❌ Error: {e}")
        finally:
            await page.close()
            await context.close()

if __name__ == "__main__":
    asyncio.run(quick_fix()) 