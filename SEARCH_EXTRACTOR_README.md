# AMBOSS Search URL Extractor

Fast extraction of article URLs from AMBOSS search results page.

## Quick Start

### Option 1: Standalone Script (Recommended)
```bash
python extract_amboss_urls.py
```

This will:
- Go to `https://next.amboss.com/de/search?q=&v=article`
- Click "Mehr anzeigen" until all results are visible
- Extract all unique article URLs of format: `https://next.amboss.com/de/article/XXXXXX`
- Save results to `amboss-article-urls.md` (one URL per line)

### Option 2: Using the CLI
```bash
# Using the amboss CLI
poetry run amboss search-extract

# Or with custom options
poetry run amboss search-extract --url "https://next.amboss.com/de/search?q=&v=article" --output "my-urls.md"
```

## What It Does

✅ **Extracts**: Only article URLs matching `https://next.amboss.com/de/article/XXXXXX`
✅ **Expands**: Clicks "Mehr anzeigen" until all results are loaded
✅ **Cleans**: Removes URL fragments (like `#E-W8_L0`) and duplicates
✅ **Outputs**: Clean list to `amboss-article-urls.md`

❌ **Does NOT**: Extract article content
❌ **Does NOT**: Follow internal anchor links
❌ **Does NOT**: Run parallel requests (human-like behavior)
❌ **Does NOT**: Go beyond the search result page

## Output Format

The script creates `amboss-article-urls.md` with content like:
```
https://next.amboss.com/de/article/CL0q-g
https://next.amboss.com/de/article/yp0dHS
https://next.amboss.com/de/article/abcd12
...
```

## Requirements

- Python 3.9+
- Playwright browsers installed
- Valid AMBOSS authentication (cookie file in `secrets/auth_state.json`)

## Installation

If you haven't set up the project yet:

```bash
# Install dependencies
poetry install

# Install Playwright browsers
poetry run playwright install chromium

# Set up authentication (you need valid AMBOSS credentials)
# Place your auth_state.json in secrets/ directory
```

## Troubleshooting

### Authentication Issues
- Ensure `secrets/auth_state.json` exists and is valid
- Run `poetry run amboss auth` to verify authentication

### No URLs Found
- Check if the search page structure has changed
- Verify you can access the search page manually in a browser

### Browser Issues
- Run `poetry run playwright install chromium` to reinstall browsers
- Check if your system has the required dependencies

## Technical Details

The extractor uses:
- **Playwright** for browser automation
- **Retry logic** for robust expansion
- **Multiple selectors** to find "Mehr anzeigen" buttons
- **URL parsing** to remove fragments and validate format
- **Rate limiting** to be respectful to the server

## Files Created

- `amboss/search_extractor.py` - Core extraction logic
- `extract_amboss_urls.py` - Standalone script
- `amboss-article-urls.md` - Output file (created when run)

## Integration with Main Scraper

The extracted URLs can be used with the main AMBOSS scraper:

```bash
# Extract URLs first
python extract_amboss_urls.py

# Then use them for screenshot capture
poetry run amboss run --limit 10
```

The main scraper will discover and process the URLs from the database. 