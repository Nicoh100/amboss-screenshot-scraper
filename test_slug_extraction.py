"""
Test slug extraction for the first article URL.
"""

import re
from amboss.config import settings

def test_slug_extraction():
    """Test if the slug extraction pattern works correctly."""
    
    test_url = "https://next.amboss.com/de/article/--0D-i"
    expected_slug = "--0D-i"
    
    print(f"Testing URL: {test_url}")
    print(f"Expected slug: {expected_slug}")
    print(f"Pattern: {settings.article_pattern}")
    print("-" * 50)
    
    # Test the pattern
    pattern = re.compile(settings.article_pattern)
    match = pattern.match(test_url)
    
    if match:
        extracted_slug = match.group(1)
        print(f"✅ Pattern matched!")
        print(f"Extracted slug: {extracted_slug}")
        print(f"Expected slug: {expected_slug}")
        
        if extracted_slug == expected_slug:
            print("✅ Slug extraction is working correctly!")
            return True
        else:
            print("❌ Slug extraction failed - wrong slug extracted")
            return False
    else:
        print("❌ Pattern did not match the URL")
        return False

if __name__ == "__main__":
    success = test_slug_extraction()
    print(f"\nOverall result: {'SUCCESS' if success else 'FAILED'}") 