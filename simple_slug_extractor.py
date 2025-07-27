"""
Simple slug extraction using the known slug list.
No regex complexity needed!
"""

def extract_slug_from_url(url):
    """Extract slug from URL using simple string splitting."""
    # Simple approach: take the last part after the last slash
    return url.split("/")[-1]

def validate_slug_against_list(slug, known_slugs):
    """Check if a slug is in our known list."""
    return slug in known_slugs

def load_known_slugs(filename="slug_list.txt"):
    """Load the known slugs from file."""
    with open(filename, 'r') as f:
        return [line.strip() for line in f if line.strip()]

def test_slug_extraction():
    """Test our simple approach."""
    
    # Load known slugs
    known_slugs = load_known_slugs()
    print(f"Loaded {len(known_slugs)} known slugs")
    
    # Test URLs
    test_urls = [
        "https://next.amboss.com/de/article/--0D-i",
        "https://next.amboss.com/de/article/-40DNT", 
        "https://next.amboss.com/de/article/030eSf",
        "https://next.amboss.com/de/article/1302hf"
    ]
    
    print("\nTesting simple slug extraction:")
    print("-" * 50)
    
    for url in test_urls:
        slug = extract_slug_from_url(url)
        is_valid = validate_slug_against_list(slug, known_slugs)
        
        print(f"URL: {url}")
        print(f"Extracted slug: {slug}")
        print(f"Valid slug: {'✅' if is_valid else '❌'}")
        print()

if __name__ == "__main__":
    test_slug_extraction() 