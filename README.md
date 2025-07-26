# AMBOSS Screenshot Scraper

A robust, intelligent screenshot scraper for AMBOSS medical articles with automatic content expansion, validation, and high-quality image capture.

## Features

- **Intelligent Content Expansion**: Automatically expands all collapsed sections and handles the AMBOSS "still-hidden" bug
- **High-Quality Screenshots**: Captures retina-quality PNG images with proper DPI tagging
- **Validation**: Ensures no hidden sections remain and validates OCR text density
- **Rate Limiting**: Respects AMBOSS rate limits with configurable throttling
- **Resumable**: SQLite-based persistence with per-slug status tracking
- **Containerized**: Docker support with pre-installed Playwright browsers
- **CLI Interface**: Simple Typer-based command-line interface

## Quick Start

### Prerequisites

- Python 3.9+
- Poetry (for dependency management)
- Valid AMBOSS authentication cookies

### Installation

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd amboss-scraper
   ```

2. **Install dependencies**:
   ```bash
   poetry install
   ```

3. **Install Playwright browsers**:
   ```bash
   poetry run playwright install chromium
   ```

4. **Set up authentication**:
   ```bash
   # Create secrets directory
   mkdir -p secrets
   
   # Copy your auth_state.json to secrets/
   cp /path/to/your/auth_state.json secrets/
   ```

### Basic Usage

1. **Discover articles**:
   ```bash
   poetry run amboss discover
   ```

2. **Process articles**:
   ```bash
   poetry run amboss run --limit 10
   ```

3. **Check statistics**:
   ```bash
   poetry run amboss stats
   ```

4. **Retry failed articles**:
   ```bash
   poetry run amboss retry-failed
   ```

## Configuration

The scraper uses environment variables for configuration. Create a `.env` file:

```env
# Authentication
AMBOSS_COOKIE_PATH=secrets/auth_state.json

# Browser settings
AMBOSS_VIEWPORT_WIDTH=1280
AMBOSS_VIEWPORT_HEIGHT=720
AMBOSS_DEVICE_SCALE_FACTOR=2.0

# Rate limiting
AMBOSS_REQUESTS_PER_MINUTE=30
AMBOSS_MIN_DELAY=2.0
AMBOSS_MAX_DELAY=4.0

# Screenshot settings
AMBOSS_OUTPUT_DIR=captures
AMBOSS_SCREENSHOT_QUALITY=100

# Validation
AMBOSS_MIN_OCR_DENSITY=0.95
AMBOSS_OCR_STDDEV_THRESHOLD=20

# Database
AMBOSS_DATABASE_PATH=amboss_scraper.db
```

## CLI Commands

### `amboss discover`
Discover AMBOSS article URLs and save to database.

```bash
# Discover from default URLs
amboss discover

# Discover from specific URLs
amboss discover --url "https://next.amboss.com/de/article/example" --url "https://next.amboss.com/de/knowledge/example"
```

### `amboss run`
Process pending URLs and capture screenshots.

```bash
# Process all pending URLs
amboss run

# Process limited number
amboss run --limit 50
```

### `amboss retry-failed`
Retry processing of failed URLs.

```bash
amboss retry-failed
```

### `amboss stats`
Show processing statistics.

```bash
# Display in terminal
amboss stats

# Save to file
amboss stats --output stats.json
```

### `amboss auth`
Manage authentication.

```bash
# Verify current auth
amboss auth

# Refresh authentication
amboss auth --refresh
```

### `amboss config`
Show current configuration.

```bash
amboss config
```

### `amboss purge`
Purge all data and reset state.

```bash
# With confirmation
amboss purge

# Skip confirmation
amboss purge --confirm
```

## Docker Usage

### Build the image:
```bash
docker build -t amboss-scraper .
```

### Run with volume mounts:
```bash
docker run -v $(pwd)/secrets:/app/secrets \
           -v $(pwd)/captures:/app/captures \
           -v $(pwd)/data:/app/data \
           amboss-scraper discover
```

### Run specific commands:
```bash
# Discover articles
docker run -v $(pwd)/secrets:/app/secrets \
           -v $(pwd)/captures:/app/captures \
           -v $(pwd)/data:/app/data \
           amboss-scraper run --limit 10

# Check stats
docker run -v $(pwd)/data:/app/data \
           amboss-scraper stats
```

## Project Structure

```
amboss_scraper/
├── amboss/
│   ├── __init__.py
│   ├── config.py          # Pydantic settings
│   ├── db.py              # SQLite database operations
│   ├── auth.py            # Authentication management
│   ├── discover.py        # URL discovery and crawling
│   ├── expander.py        # Content expansion strategies
│   ├── shooter.py         # Screenshot capture
│   ├── validator.py       # Content validation
│   ├── tasks.py           # Task orchestration
│   └── cli.py             # Typer CLI application
├── tests/
│   ├── test_expander.py
│   ├── test_shooter.py
│   └── test_validator.py
├── docs/
│   └── SCREENSHOT_LLM_FEEDBACK.md
├── secrets/               # Authentication files (not versioned)
│   ├── auth_state.json
│   └── credentials.json
├── captures/              # Screenshot output (not versioned)
├── pyproject.toml
├── Dockerfile
└── README.md
```

## Database Schema

### URLs Table
```sql
CREATE TABLE urls (
    slug        TEXT PRIMARY KEY,
    url         TEXT NOT NULL,
    discovered  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status      TEXT CHECK(status IN ('pending','processing','done','failed_expansion','failed_validation')) DEFAULT 'pending',
    last_error  TEXT,
    retry_count INTEGER DEFAULT 0
);
```

### Runs Table
```sql
CREATE TABLE runs (
    run_id      TEXT,
    slug        TEXT,
    started     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    finished    TIMESTAMP,
    ok          BOOLEAN,
    error_msg   TEXT,
    PRIMARY KEY (run_id, slug),
    FOREIGN KEY (slug) REFERENCES urls(slug)
);
```

### Images Table
```sql
CREATE TABLE images (
    run_id      TEXT,
    slug        TEXT,
    filename    TEXT,
    idx         INTEGER,
    section_title TEXT,
    created     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (run_id, slug, idx),
    FOREIGN KEY (run_id, slug) REFERENCES runs(run_id, slug)
);
```

## Content Expansion Strategy

The scraper uses multiple strategies to ensure all content is expanded:

1. **Click-based Expansion**: Clicks all visible expansion buttons
2. **JavaScript Fallback**: Uses JavaScript to click stubborn elements
3. **Dynamic Content Waiting**: Waits for dynamic content to load
4. **Verification**: Checks that no hidden sections remain

### Known AMBOSS "Still-Hidden" Bug

The scraper specifically handles the AMBOSS bug where some sections remain hidden even after clicking expansion buttons. It uses JavaScript fallbacks and multiple verification steps to ensure complete expansion.

## Validation

### Content Density Validation
Uses image analysis to validate that screenshots contain sufficient text content:

- Calculates standard deviation of pixel values
- Normalizes to a 0-1 density score
- Requires minimum density threshold (configurable)

### Hidden Section Detection
Checks for remaining expansion buttons and hidden content indicators.

## Rate Limiting

- **Default**: 30 requests per minute
- **Configurable**: Via environment variables
- **Random Delays**: 2-4 seconds between requests
- **Token Bucket**: Uses asyncio-throttle for precise control

## Error Handling

- **Retry Logic**: Uses tenacity for exponential backoff
- **Graceful Degradation**: Continues processing on individual failures
- **Detailed Logging**: Structured JSON logging with context
- **Status Tracking**: Per-slug status in database

## Security

- **Non-root Docker**: Runs as non-root user
- **Secrets Management**: Authentication files in separate directory
- **Environment Variables**: No hardcoded credentials
- **Input Validation**: Pydantic validation for all configuration

## Development

### Running Tests
```bash
poetry run pytest
```

### Code Formatting
```bash
poetry run black amboss/
poetry run isort amboss/
```

### Type Checking
```bash
poetry run mypy amboss/
```

### Pre-commit Hooks
```bash
poetry run pre-commit install
```

## Troubleshooting

### Authentication Issues
1. Verify `auth_state.json` exists in `secrets/`
2. Check file permissions
3. Use `amboss auth` to verify authentication
4. Use `amboss auth --refresh` to refresh if needed

### Screenshot Quality Issues
1. Check viewport and device scale factor settings
2. Verify screenshot quality setting (1-100)
3. Check available disk space

### Rate Limiting Issues
1. Reduce `AMBOSS_REQUESTS_PER_MINUTE`
2. Increase delay between requests
3. Check AMBOSS terms of service

### Database Issues
1. Check database file permissions
2. Verify SQLite is working
3. Use `amboss stats` to check database state

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Run linting and tests
6. Submit a pull request

## License

[Add your license here]

## Support

For issues and questions:
1. Check the troubleshooting section
2. Review the logs with `--log-level DEBUG`
3. Open an issue with detailed information 