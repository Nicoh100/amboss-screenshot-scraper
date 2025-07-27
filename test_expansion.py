"""
Test script to verify content expansion improvements.
"""

import asyncio
from amboss.auth import AuthManager
from amboss.expander import ContentExpander

async def test_expansion():
    """Test the improved content expansion system."""
    url = "https://next.amboss.com/de/article/--0D-i"
    
    print(f"🧪 Testing content expansion for: {url}")
    
    async with AuthManager() as auth_manager:
        context = await auth_manager.create_context()
        page = await context.new_page()
        
        try:
            # Navigate to article
            print("🔍 Navigating to article...")
            await page.goto(url, wait_until="domcontentloaded", timeout=15000)
            await asyncio.sleep(3)
            
            # Test content expansion
            print("🔧 Testing content expansion...")
            expander = ContentExpander()
            
            # Check initial state
            print("📊 Checking initial content state...")
            initial_expanded = await expander.verify_content_is_expanded(page)
            print(f"Initial expanded state: {initial_expanded}")
            
            # Expand content
            print("🔍 Expanding all sections...")
            await expander.fully_expand(page)
            
            # Check final state
            print("📊 Checking final content state...")
            final_expanded = await expander.verify_content_is_expanded(page)
            print(f"Final expanded state: {final_expanded}")
            
            # Get content metrics
            print("📈 Getting content metrics...")
            metrics = await expander.get_content_metrics(page)
            print(f"Content metrics: {metrics}")
            
            # Check if fully expanded
            is_fully_expanded = await expander.is_fully_expanded(page)
            print(f"Fully expanded: {is_fully_expanded}")
            
            print("✅ Test completed!")
            
        except Exception as e:
            print(f"❌ Error: {e}")
        finally:
            await page.close()
            await context.close()

if __name__ == "__main__":
    asyncio.run(test_expansion()) 