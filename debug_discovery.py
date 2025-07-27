"""
Debug script to see what's happening during discovery.
"""

import asyncio
from amboss.discover import URLDiscoverer
from amboss.db import DatabaseManager

async def debug_discovery():
    """Debug the discovery process."""
    
    print("Testing discovery with direct URL...")
    
    # Test the direct URL approach
    test_url = "https://next.amboss.com/de/article/--0D-i"
    print(f"Input URL: {test_url}")
    
    # Simulate what the discovery process does
    async with DatabaseManager() as db:
        # Extract slug using our simple method
        slug = test_url.split("/")[-1]
        print(f"Extracted slug: {slug}")
        
        # Add to database
        success = await db.add_url(slug, test_url)
        print(f"Database add success: {success}")
        
        # Check what's in the database
        stats = await db.get_stats()
        print(f"Database stats: {stats}")
        
        # Get the actual URL from database
        pending_urls = await db.get_pending_urls()
        if pending_urls:
            db_slug, db_url = pending_urls[0]
            print(f"Database has: slug='{db_slug}', url='{db_url}'")
        else:
            print("No pending URLs found")

if __name__ == "__main__":
    asyncio.run(debug_discovery()) 