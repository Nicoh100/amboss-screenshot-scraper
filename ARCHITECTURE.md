# AMBOSS Scraper - Architecture Overview

## 🎯 **Core Purpose**
Fast, intelligent screenshot capture of AMBOSS medical articles with content expansion and validation.

## 🏗️ **Architecture Pattern**
- **Modular Python Package** with clear separation of concerns
- **Async-first** with Playwright for browser automation
- **Configuration-driven** with Pydantic settings
- **CLI-first** with Typer for user interaction

## 📦 **Key Modules**

| Module | Purpose | Key Classes |
|--------|---------|-------------|
| `auth.py` | Browser authentication | `AuthManager` |
| `discover.py` | URL discovery & crawling | `URLDiscoverer` |
| `expander.py` | Content expansion | `ContentExpander` |
| `shooter.py` | Screenshot capture | `ScreenshotShooter` |
| `validator.py` | Content validation | `ContentValidator` |
| `tasks.py` | Orchestration | `ScrapingTask` |
| `fast_processor.py` | Fast processing | `FastAMBOSSProcessor` |

## 🛠️ **Tech Stack**

### Core Dependencies
- **Playwright** - Browser automation
- **Pydantic** - Data validation & config
- **SQLite** - Persistent state (aiosqlite)
- **Typer** - CLI framework
- **Poetry** - Dependency management

### Key Libraries
- **tenacity** - Retry logic
- **structlog** - Structured logging
- **asyncio-throttle** - Rate limiting
- **Pillow** - Image processing

## 🔄 **Data Flow**

```
URL List → Auth → Browser → Expand → Validate → Screenshot → Save
   ↓         ↓       ↓        ↓         ↓          ↓         ↓
amboss_   Cookie  Context  "Mehr     OCR       2x Retina  ./captures/
links.txt  Auth   Page     anzeigen" Density   PNG        {slug}/
```

## 📁 **File Structure**
```
amboss/
├── __init__.py          # Package metadata
├── config.py           # Settings & validation
├── auth.py             # Browser authentication
├── discover.py         # URL discovery
├── expander.py         # Content expansion
├── shooter.py          # Screenshot capture
├── validator.py        # Content validation
├── tasks.py            # Task orchestration
├── fast_processor.py   # Fast processing
└── cli.py              # Command-line interface
```

## 🎛️ **Configuration**
- **Environment variables** (AMBOSS_* prefix)
- **`.env` file** for local settings
- **Pydantic validation** for type safety
- **Default values** for sensible defaults

## 🚀 **Entry Points**

### CLI Commands
```bash
amboss discover      # Find article URLs
amboss run          # Process articles
amboss fast-process # Fast processing
amboss auth         # Manage authentication
amboss stats        # View statistics
```

### Standalone Scripts
```bash
python fast_amboss_processor.py  # Fast processing
python extract_amboss_urls.py    # URL extraction
```

## 🔧 **Key Algorithms**

### Content Expansion
1. Click visible "Mehr anzeigen" buttons
2. JavaScript fallback for stubborn elements
3. Wait for dynamic content
4. Verify no hidden sections remain

### Screenshot Strategy
1. Identify section headers (h1-h6, data-testid)
2. Scroll each into view
3. Calculate clipping area
4. Capture 2x retina PNG
5. Set DPI metadata

### Validation
1. Check for remaining hidden sections
2. Calculate content density (OCR proxy)
3. Validate screenshot quality
4. Ensure completeness

## 📊 **State Management**
- **SQLite database** for URL tracking
- **File system** for screenshots
- **Cookie-based** authentication
- **Rate limiting** for server respect

## 🎯 **Design Principles**
- **Single Responsibility** - Each module has one clear purpose
- **Async-first** - Non-blocking operations
- **Error Resilience** - Graceful failure handling
- **Human-like** - Respectful rate limiting
- **Idempotent** - Safe to restart

## 🔄 **Update Strategy**
1. **Code changes** → Update relevant module
2. **New features** → Add to ARCHITECTURE.md
3. **Dependencies** → Update pyproject.toml
4. **Configuration** → Update config.py & env.example
5. **Documentation** → Update README.md

---
*Last updated: 2024-01-27* 