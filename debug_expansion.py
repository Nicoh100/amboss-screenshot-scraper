"""
Debug script to test section expansion.
"""

import asyncio
from amboss.auth import AuthManager
from amboss.expander import ContentExpander

async def debug_expansion(url: str):
    """Debug section expansion for a specific URL."""
    
    print(f"🔍 Debugging expansion for: {url}")
    
    async with AuthManager() as auth_manager:
        context = await auth_manager.create_context()
        page = await context.new_page()
        
        try:
            # Navigate to the article
            print("📄 Navigating to article...")
            await page.goto(url, wait_until="domcontentloaded", timeout=15000)
            await asyncio.sleep(3)
            
            # Check initial state
            print("\n🔍 Checking initial state...")
            await check_section_states(page, "Initial")
            
            # Try global toggle button
            print("\n🔘 Testing global toggle button...")
            global_toggle = page.locator('button[data-e2e-test-id="toggle-all-sections-button"]')
            if await global_toggle.count() > 0:
                print("✅ Found global toggle button")
                await global_toggle.click()
                await asyncio.sleep(3)
                await check_section_states(page, "After global toggle")
            else:
                print("❌ No global toggle button found")
            
            # Try individual section expansion
            print("\n🔘 Testing individual section expansion...")
            sections = page.locator('section[data-e2e-test-id="section-with-header"] div.cebd2a302a3552c4--headerContainer[role="button"]')
            section_count = await sections.count()
            print(f"Found {section_count} sections")
            
            for i in range(min(3, section_count)):  # Test first 3 sections
                try:
                    section = sections.nth(i)
                    if await section.is_visible():
                        print(f"Clicking section {i}...")
                        await section.click()
                        await asyncio.sleep(1)
                except Exception as e:
                    print(f"Error clicking section {i}: {e}")
            
            await check_section_states(page, "After individual clicks")
            
            # Try ContentExpander
            print("\n🔧 Testing ContentExpander...")
            expander = ContentExpander()
            await expander.fully_expand(page)
            await check_section_states(page, "After ContentExpander")
            
        except Exception as e:
            print(f"❌ Error: {e}")
        finally:
            await page.close()
            await context.close()

async def check_section_states(page, stage_name: str):
    """Check the state of sections at a given stage."""
    try:
        # Check expanded sections
        expanded = page.locator('[data-e2e-test-id="section-content-is-shown"]')
        expanded_count = await expanded.count()
        
        # Check collapsed sections
        collapsed = page.locator('[data-e2e-test-id="section-content-is-hidden"]')
        collapsed_count = await collapsed.count()
        
        # Check section headers
        headers = page.locator('section[data-e2e-test-id="section-with-header"] div.cebd2a302a3552c4--headerContainer[role="button"]')
        header_count = await headers.count()
        
        print(f"📊 {stage_name}:")
        print(f"  - Section headers: {header_count}")
        print(f"  - Expanded sections: {expanded_count}")
        print(f"  - Collapsed sections: {collapsed_count}")
        
        # Check if global toggle button exists and its state
        global_toggle = page.locator('button[data-e2e-test-id="toggle-all-sections-button"]')
        if await global_toggle.count() > 0:
            print(f"  - Global toggle button: Found")
            # Check if it has collapse or expand icon
            try:
                collapse_icon = global_toggle.locator('[data-e2e-test-id="collapse"]')
                expand_icon = global_toggle.locator('[data-e2e-test-id="expand"]')
                
                if await collapse_icon.count() > 0:
                    print(f"  - Global toggle state: Collapse (sections are expanded)")
                elif await expand_icon.count() > 0:
                    print(f"  - Global toggle state: Expand (sections are collapsed)")
                else:
                    print(f"  - Global toggle state: Unknown")
            except:
                print(f"  - Global toggle state: Could not determine")
        else:
            print(f"  - Global toggle button: Not found")
            
    except Exception as e:
        print(f"Error checking section states: {e}")

async def main():
    """Main function."""
    url = "https://next.amboss.com/de/article/--0D-i"
    await debug_expansion(url)

if __name__ == "__main__":
    asyncio.run(main()) 