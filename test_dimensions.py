"""
Test script to demonstrate different screenshot dimensions.
"""

import asyncio
import os
from amboss.auth import AuthManager

async def test_dimensions():
    """Test different viewport dimensions."""
    
    # Test different dimension configurations
    test_configs = [
        {"width": 1280, "height": 720, "scale": 1.0, "name": "HD"},
        {"width": 1920, "height": 1080, "scale": 1.0, "name": "Full HD"},
        {"width": 1920, "height": 1080, "scale": 2.0, "name": "Full HD Retina"},
        {"width": 1366, "height": 768, "scale": 1.0, "name": "Laptop"},
        {"width": 375, "height": 667, "scale": 2.0, "name": "Mobile"}
    ]
    
    test_url = "https://next.amboss.com/de/article/--0D-i"
    
    for config in test_configs:
        print(f"\n--- Testing {config['name']} ({config['width']}x{config['height']}, scale={config['scale']}) ---")
        
        # Set environment variables for this test
        os.environ["AMBOSS_VIEWPORT_WIDTH"] = str(config["width"])
        os.environ["AMBOSS_VIEWPORT_HEIGHT"] = str(config["height"])
        os.environ["AMBOSS_DEVICE_SCALE_FACTOR"] = str(config["scale"])
        
        async with AuthManager() as auth_manager:
            context = await auth_manager.create_context()
            page = await context.new_page()
            
            try:
                # Navigate to the page
                await page.goto(test_url, wait_until="domcontentloaded", timeout=15000)
                await asyncio.sleep(2)
                
                # Take a screenshot
                filename = f"test_{config['name'].lower().replace(' ', '_')}.png"
                await page.screenshot(path=filename, full_page=True)
                
                print(f"✅ Screenshot saved: {filename}")
                
            except Exception as e:
                print(f"❌ Error: {e}")
            finally:
                await page.close()
                await context.close()

if __name__ == "__main__":
    asyncio.run(test_dimensions()) 