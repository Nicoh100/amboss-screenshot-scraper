"""
Quick test to verify improvements work correctly.
"""

import asyncio
from amboss.auth import AuthManager
from amboss.expander import ContentExpander

async def quick_test():
    """Quick test of the improved system."""
    url = "https://next.amboss.com/de/article/--0D-i"
    
    print(f"🧪 Quick test: {url}")
    
    async with AuthManager() as auth_manager:
        context = await auth_manager.create_context()
        page = await context.new_page()
        
        try:
            # Navigate
            print("🔍 Navigating...")
            await page.goto(url, wait_until="domcontentloaded", timeout=15000)
            await asyncio.sleep(3)
            
            # Test expansion
            print("🔧 Testing expansion...")
            expander = ContentExpander()
            await expander.fully_expand(page)
            
            # Check result
            print("📊 Checking result...")
            is_expanded = await expander.verify_content_is_expanded(page)
            print(f"✅ Expansion successful: {is_expanded}")
            
            # Get metrics
            metrics = await expander.get_content_metrics(page)
            print(f"📈 Content metrics: {metrics}")
            
        except Exception as e:
            print(f"❌ Error: {e}")
        finally:
            await page.close()
            await context.close()

if __name__ == "__main__":
    asyncio.run(quick_test()) 