"""
Debug script to find the actual content area using Playwright's bounding_box().
"""

import asyncio
from amboss.auth import AuthManager
from amboss.expander import ContentExpander

async def debug_content_area():
    """Find the actual content area of the article page."""
    
    test_url = "https://next.amboss.com/de/article/--0D-i"
    
    async with AuthManager() as auth_manager:
        context = await auth_manager.create_context()
        page = await context.new_page()
        
        try:
            print(f"🔍 Navigating to: {test_url}")
            await page.goto(test_url, wait_until="domcontentloaded", timeout=15000)
            await asyncio.sleep(3)
            
            # Handle popups first
            expander = ContentExpander()
            await expander._handle_cookie_consent(page)
            await asyncio.sleep(2)
            
            print("\n📐 Viewport size:")
            viewport = page.viewport_size
            print(f"  Width: {viewport['width']}px")
            print(f"  Height: {viewport['height']}px")
            
            print("\n🔍 Testing different content selectors:")
            
            # Test various content selectors
            content_selectors = [
                "main",
                "article",
                "[data-testid='article-body']",
                ".article-body",
                ".article-content",
                ".content",
                "[role='main']",
                ".main-content",
                "#content",
                ".article-container",
                ".article-wrapper",
                ".article-main",
                ".article-text",
                ".article-section",
                ".content-area",
                ".content-wrapper",
                ".content-main",
                ".content-body",
                ".content-text",
                ".content-section"
            ]
            
            found_content = False
            
            for selector in content_selectors:
                try:
                    element = page.locator(selector)
                    count = await element.count()
                    
                    if count > 0:
                        print(f"\n✅ Found {count} element(s) with selector: '{selector}'")
                        
                        for i in range(min(count, 3)):  # Check first 3 elements
                            element_instance = element.nth(i)
                            
                            if await element_instance.is_visible():
                                bbox = await element_instance.bounding_box()
                                if bbox:
                                    print(f"  Element {i}:")
                                    print(f"    x: {bbox['x']}")
                                    print(f"    y: {bbox['y']}")
                                    print(f"    width: {bbox['width']}")
                                    print(f"    height: {bbox['height']}")
                                    print(f"    Area: {bbox['width']} x {bbox['height']} = {bbox['width'] * bbox['height']}px²")
                                    
                                    # Get the full scroll height of the element
                                    full_height = await element_instance.evaluate("el => el.scrollHeight")
                                    print(f"    Full scroll height: {full_height}px")
                                    
                                    # Get some text content to verify it's the right area
                                    text_content = await element_instance.text_content()
                                    if text_content:
                                        preview = text_content[:200].replace('\n', ' ').strip()
                                        print(f"    Preview: {preview}...")
                                    
                                    found_content = True
                                else:
                                    print(f"  Element {i}: No bounding box")
                            else:
                                print(f"  Element {i}: Not visible")
                    else:
                        print(f"❌ No elements found with selector: '{selector}'")
                        
                except Exception as e:
                    print(f"❌ Error with selector '{selector}': {e}")
            
            if not found_content:
                print("\n⚠️ No content areas found with standard selectors.")
                print("Let's try to find any large text containers:")
                
                # Try to find any large text containers
                large_elements = await page.query_selector_all("div, section, article, main")
                
                for i, element in enumerate(large_elements[:10]):  # Check first 10
                    try:
                        if await element.is_visible():
                            bbox = await element.bounding_box()
                            if bbox and bbox['width'] > 200 and bbox['height'] > 300:
                                text_content = await element.text_content()
                                if text_content and len(text_content) > 100:
                                    print(f"\n📄 Large text element {i}:")
                                    print(f"  x: {bbox['x']}, y: {bbox['y']}")
                                    print(f"  width: {bbox['width']}, height: {bbox['height']}")
                                    print(f"  text length: {len(text_content)}")
                                    preview = text_content[:150].replace('\n', ' ').strip()
                                    print(f"  preview: {preview}...")
                    except:
                        continue
            
            print("\n🎯 Recommended screenshot approach:")
            print("1. Find the main content area using bounding_box()")
            print("2. Use content area's x, y, width for horizontal cropping")
            print("3. Use scrollHeight for full content height")
            print("4. Slice vertically in chunks of ~1000px height")
            print("5. Skip UI elements (navigation, sidebars, etc.)")
            
        except Exception as e:
            print(f"❌ Error: {e}")
        finally:
            await page.close()
            await context.close()

if __name__ == "__main__":
    asyncio.run(debug_content_area()) 