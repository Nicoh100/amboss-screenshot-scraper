# Fast AMBOSS Article Processor

Fast processing of AMBOSS articles using your existing URL list (`amboss_all_articles_links.txt`).

## 🚀 Quick Start

### Option 1: Standalone Script (Recommended)
```bash
python fast_amboss_processor.py
```

### Option 2: Using the CLI
```bash
# Process all articles
poetry run amboss fast-process

# Process only first 10 articles (for testing)
poetry run amboss fast-process --limit 10

# Use a different URL file
poetry run amboss fast-process --file my-urls.txt
```

## ✅ What It Does

- **Reads**: Your existing `amboss_all_articles_links.txt` file
- **Extracts**: Clean URLs from the numbered format
- **Processes**: Each article with intelligent content expansion
- **Validates**: Content completeness and quality
- **Captures**: High-quality screenshots of each section
- **Saves**: Images to `./captures/{slug}/{run-id}/`

## 📊 Your URL List

The script automatically reads from `amboss_all_articles_links.txt` which contains:
```
AMBOSS All Article URLs
Generated on: 2025-07-27 13:51:43
Total URLs: 1521

1. https://next.amboss.com/de/article/--0D-i - Pränataldiagnostik
2. https://next.amboss.com/de/article/-40DNT - Molluscum contagiosum
...
```

## 🎯 Features

✅ **Fast Processing**: Uses your existing URL list (no need to extract from search page)
✅ **Intelligent Expansion**: Handles "Mehr anzeigen" buttons and hidden content
✅ **Content Validation**: Ensures all sections are visible and content is complete
✅ **High-Quality Screenshots**: 2x retina, lossless PNG, proper DPI
✅ **Rate Limiting**: Respectful to AMBOSS servers (2-4s delays)
✅ **Progress Tracking**: Real-time progress updates
✅ **Error Handling**: Continues processing even if some articles fail
✅ **Resumable**: Can be stopped and restarted

## 📁 Output Structure

```
captures/
├── --0D-i/
│   └── run_1/
│       ├── 001_introduction.png
│       ├── 002_main_content.png
│       └── 003_conclusion.png
├── -40DNT/
│   └── run_1/
│       ├── 001_overview.png
│       └── 002_treatment.png
└── ...
```

## ⚙️ Configuration

The script uses the same configuration as the main scraper:

- **Authentication**: `secrets/auth_state.json`
- **Rate Limiting**: 2-4s delays between requests
- **Screenshot Quality**: 2x retina, lossless PNG
- **Output Directory**: `./captures/`

## 🧪 Testing

Start with a small batch to test:

```bash
# Test with first 5 articles
python fast_amboss_processor.py  # Edit the limit in the script
# or
poetry run amboss fast-process --limit 5
```

## 📈 Performance

- **Speed**: ~30 articles per minute (with rate limiting)
- **Memory**: Efficient browser context management
- **Reliability**: Robust error handling and retries
- **Scalability**: Can process all 1,521 articles

## 🔧 Troubleshooting

### Authentication Issues
```bash
# Verify your auth is working
poetry run amboss auth
```

### File Not Found
```bash
# Make sure amboss_all_articles_links.txt exists
ls -la amboss_all_articles_links.txt
```

### Browser Issues
```bash
# Reinstall Playwright browsers
poetry run playwright install chromium
```

## 📋 Example Usage

```bash
# 1. Verify authentication
poetry run amboss auth

# 2. Test with 5 articles
poetry run amboss fast-process --limit 5

# 3. Process all articles
poetry run amboss fast-process

# 4. Check results
ls -la captures/
```

## 🎉 Success!

When complete, you'll have:
- ✅ All 1,521 articles processed
- ✅ High-quality screenshots for each section
- ✅ Organized output structure
- ✅ Detailed processing statistics

The script is optimized for your existing URL list and will process all articles efficiently! 