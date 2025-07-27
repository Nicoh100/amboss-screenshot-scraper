"""
Simple test that bypasses complex popup handling.
"""

import asyncio
from amboss.auth import AuthManager

async def simple_test():
    """Simple test without complex popup handling."""
    
    test_url = "https://next.amboss.com/de/article/--0D-i"
    
    async with AuthManager() as auth_manager:
        context = await auth_manager.create_context()
        page = await context.new_page()
        
        try:
            print("🔍 Navigating to article...")
            await page.goto(test_url, wait_until="domcontentloaded", timeout=15000)
            await asyncio.sleep(3)
            
            # Simple popup handling - just press Escape
            print("🔧 Simple popup handling...")
            await page.keyboard.press("Escape")
            await asyncio.sleep(1)
            
            # Scroll down to reveal content
            print("📜 Scrolling to reveal content...")
            await page.evaluate("window.scrollTo(0, 1000)")
            await asyncio.sleep(2)
            
            # Take screenshot with your exact parameters
            clip = {
                "x": 250,
                "y": 56,
                "width": 848,
                "height": 2000
            }
            
            print("📸 Taking screenshot...")
            await page.screenshot(path="simple_test.png", clip=clip)
            print("✅ Screenshot saved: simple_test.png")
            
        except Exception as e:
            print(f"❌ Error: {e}")
        finally:
            await page.close()
            await context.close()

if __name__ == "__main__":
    asyncio.run(simple_test()) 