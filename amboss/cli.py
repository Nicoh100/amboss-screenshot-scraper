"""CLI application for AMBOSS scraper."""

import asyncio
import json
from pathlib import Path
from typing import List, Optional

import typer
from structlog import get_logger

from .config import settings
from .db import init_database
from .tasks import run_discovery, run_processing, run_retry, get_processing_stats
from .search_extractor import extract_and_save_urls
from .fast_processor import FastAMBOSSProcessor

app = typer.Typer(
    name="amboss",
    help="AMBOSS Screenshot Scraper - Intelligent content expansion and validation",
    add_completion=False
)

logger = get_logger(__name__)


def setup_logging(log_level: str = "INFO", log_format: str = "json"):
    """Setup structured logging."""
    import structlog
    
    processors = [
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]
    
    if log_format == "json":
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer())
    
    structlog.configure(
        processors=processors,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )


@app.command()
def discover(
    start_urls: Optional[List[str]] = typer.Option(
        None,
        "--url",
        "-u",
        help="Starting URLs for discovery (can specify multiple)"
    ),
    log_level: str = typer.Option("INFO", "--log-level", "-l"),
    log_format: str = typer.Option("json", "--log-format", "-f")
):
    """Discover AMBOSS article URLs and save to database."""
    setup_logging(log_level, log_format)
    
    async def _discover():
        try:
            # Initialize database
            await init_database()
            
            # Run discovery
            discovered_urls = await run_discovery(start_urls)
            
            typer.echo(f"Discovery completed: {len(discovered_urls)} URLs found")
            
        except Exception as e:
            logger.error("Discovery failed", error=str(e))
            typer.echo(f"Error: {e}")
            raise typer.Exit(1)
    
    asyncio.run(_discover())


@app.command()
def run(
    limit: Optional[int] = typer.Option(
        None,
        "--limit",
        "-l",
        help="Limit number of URLs to process"
    ),
    log_level: str = typer.Option("INFO", "--log-level", "-l"),
    log_format: str = typer.Option("json", "--log-format", "-f")
):
    """Process pending URLs and capture screenshots."""
    setup_logging(log_level, log_format)
    
    async def _run():
        try:
            # Initialize database
            await init_database()
            
            # Run processing
            result = await run_processing(limit)
            
            typer.echo(f"Processing completed:")
            typer.echo(f"  Processed: {result['processed']}")
            typer.echo(f"  Successful: {result['successful']}")
            typer.echo(f"  Failed: {result['failed']}")
            typer.echo(f"  Run ID: {result['run_id']}")
            
        except Exception as e:
            logger.error("Processing failed", error=str(e))
            typer.echo(f"Error: {e}")
            raise typer.Exit(1)
    
    asyncio.run(_run())


@app.command()
def retry_failed(
    log_level: str = typer.Option("INFO", "--log-level", "-l"),
    log_format: str = typer.Option("json", "--log-format", "-f")
):
    """Retry processing of failed URLs."""
    setup_logging(log_level, log_format)
    
    async def _retry():
        try:
            # Initialize database
            await init_database()
            
            # Run retry
            result = await run_retry()
            
            typer.echo(f"Retry completed:")
            typer.echo(f"  Retried: {result['processed']}")
            typer.echo(f"  Successful: {result['successful']}")
            typer.echo(f"  Failed: {result['failed']}")
            typer.echo(f"  Run ID: {result['run_id']}")
            
        except Exception as e:
            logger.error("Retry failed", error=str(e))
            typer.echo(f"Error: {e}")
            raise typer.Exit(1)
    
    asyncio.run(_retry())


@app.command()
def stats(
    output: Optional[Path] = typer.Option(
        None,
        "--output",
        "-o",
        help="Output file for statistics (JSON format)"
    ),
    log_level: str = typer.Option("INFO", "--log-level", "-l"),
    log_format: str = typer.Option("json", "--log-format", "-f")
):
    """Show processing statistics."""
    setup_logging(log_level, log_format)
    
    async def _stats():
        try:
            # Initialize database
            await init_database()
            
            # Get statistics
            stats = await get_processing_stats()
            
            # Format output
            if output:
                with open(output, 'w') as f:
                    json.dump(stats, f, indent=2)
                typer.echo(f"Statistics saved to {output}")
            else:
                typer.echo("Database Statistics:")
                typer.echo(f"  Total URLs: {stats.get('total_urls', 0)}")
                
                urls_by_status = stats.get('urls_by_status', {})
                for status, count in urls_by_status.items():
                    typer.echo(f"  {status}: {count}")
                
                typer.echo(f"  Total Runs: {stats.get('total_runs', 0)}")
                typer.echo(f"  Total Images: {stats.get('total_images', 0)}")
            
        except Exception as e:
            logger.error("Failed to get statistics", error=str(e))
            typer.echo(f"Error: {e}")
            raise typer.Exit(1)
    
    asyncio.run(_stats())


@app.command()
def purge(
    confirm: bool = typer.Option(
        False,
        "--confirm",
        "-y",
        help="Skip confirmation prompt"
    ),
    log_level: str = typer.Option("INFO", "--log-level", "-l"),
    log_format: str = typer.Option("json", "--log-format", "-f")
):
    """Purge all data and reset state."""
    setup_logging(log_level, log_format)
    
    if not confirm:
        typer.echo("This will delete all captured images and reset the database.")
        confirm = typer.confirm("Are you sure?")
    
    if not confirm:
        typer.echo("Operation cancelled.")
        return
    
    async def _purge():
        try:
            # Remove database
            if settings.database_path.exists():
                settings.database_path.unlink()
                typer.echo(f"Database deleted: {settings.database_path}")
            
            # Remove captures directory
            if settings.output_dir.exists():
                import shutil
                shutil.rmtree(settings.output_dir)
                typer.echo(f"Captures directory deleted: {settings.output_dir}")
            
            typer.echo("Purge completed successfully.")
            
        except Exception as e:
            logger.error("Purge failed", error=str(e))
            typer.echo(f"Error: {e}")
            raise typer.Exit(1)
    
    asyncio.run(_purge())


@app.command()
def auth(
    refresh: bool = typer.Option(
        False,
        "--refresh",
        "-r",
        help="Refresh authentication using credentials"
    ),
    log_level: str = typer.Option("INFO", "--log-level", "-l"),
    log_format: str = typer.Option("json", "--log-format", "-f")
):
    """Manage authentication."""
    setup_logging(log_level, log_format)
    
    async def _auth():
        try:
            from .auth import AuthManager
            
            async with AuthManager() as auth_manager:
                if refresh:
                    success = await auth_manager.refresh_auth()
                    if success:
                        typer.echo("Authentication refreshed successfully.")
                    else:
                        typer.echo("Failed to refresh authentication.")
                        raise typer.Exit(1)
                else:
                    # Just verify current auth
                    context = await auth_manager.create_context()
                    page = await context.new_page()
                    
                    try:
                        if await auth_manager.verify_auth(page):
                            typer.echo("Authentication is valid.")
                        else:
                            typer.echo("Authentication is invalid or expired.")
                            raise typer.Exit(1)
                    finally:
                        await page.close()
                        await context.close()
            
        except Exception as e:
            logger.error("Authentication operation failed", error=str(e))
            typer.echo(f"Error: {e}")
            raise typer.Exit(1)
    
    asyncio.run(_auth())


@app.command()
def search_extract(
    search_url: str = typer.Option(
        "https://next.amboss.com/de/search?q=&v=article",
        "--url",
        "-u",
        help="Search URL to extract article URLs from"
    ),
    output_file: str = typer.Option(
        "amboss-article-urls.md",
        "--output",
        "-o",
        help="Output file for extracted URLs"
    ),
    log_level: str = typer.Option("INFO", "--log-level", "-l"),
    log_format: str = typer.Option("json", "--log-format", "-f")
):
    """Extract article URLs from AMBOSS search results page."""
    setup_logging(log_level, log_format)
    
    async def _search_extract():
        try:
            typer.echo(f"Extracting article URLs from: {search_url}")
            typer.echo(f"Output will be saved to: {output_file}")
            
            urls = await extract_and_save_urls(search_url, output_file)
            
            typer.echo(f"✅ Successfully extracted {len(urls)} unique article URLs")
            typer.echo(f"📄 Results saved to: {output_file}")
            
            # Show preview of first few URLs
            if urls:
                typer.echo("\n📋 First 5 URLs:")
                for url in urls[:5]:
                    typer.echo(f"  {url}")
                if len(urls) > 5:
                    typer.echo(f"  ... and {len(urls) - 5} more")
            
        except Exception as e:
            logger.error("Search extraction failed", error=str(e))
            typer.echo(f"❌ Error: {e}")
            raise typer.Exit(1)
    
    asyncio.run(_search_extract())


@app.command()
def fast_process(
    url_file: str = typer.Option(
        "amboss_all_articles_links.txt",
        "--file",
        "-f",
        help="File containing article URLs"
    ),
    limit: Optional[int] = typer.Option(
        None,
        "--limit",
        "-l",
        help="Limit number of articles to process (for testing)"
    ),
    log_level: str = typer.Option("INFO", "--log-level", "-l"),
    log_format: str = typer.Option("json", "--log-format", "-f")
):
    """Fast processing of AMBOSS articles using existing URL list."""
    setup_logging(log_level, log_format)
    
    async def _fast_process():
        try:
            typer.echo(f"🚀 Starting fast processing from: {url_file}")
            if limit:
                typer.echo(f"📊 Limited to first {limit} articles")
            
            processor = FastAMBOSSProcessor()
            urls = processor.extract_urls_from_file(url_file)
            
            if not urls:
                typer.echo("❌ No URLs found. Exiting.")
                raise typer.Exit(1)
            
            result = await processor.process_all_articles(urls, limit)
            
            typer.echo("\n🎉 Processing completed!")
            typer.echo(f"📊 Results:")
            typer.echo(f"  Total URLs: {result['total']}")
            typer.echo(f"  Processed: {result['processed']}")
            typer.echo(f"  Successful: {result['successful']}")
            typer.echo(f"  Failed: {result['failed']}")
            typer.echo(f"  Success Rate: {result['success_rate']:.1%}")
            
        except Exception as e:
            logger.error("Fast processing failed", error=str(e))
            typer.echo(f"❌ Error: {e}")
            raise typer.Exit(1)
    
    asyncio.run(_fast_process())


@app.command()
def config(
    log_level: str = typer.Option("INFO", "--log-level", "-l"),
    log_format: str = typer.Option("json", "--log-format", "-f")
):
    """Show current configuration."""
    setup_logging(log_level, log_format)
    
    typer.echo("Current Configuration:")
    typer.echo(f"  Cookie Path: {settings.cookie_path}")
    typer.echo(f"  Database Path: {settings.database_path}")
    typer.echo(f"  Output Directory: {settings.output_dir}")
    typer.echo(f"  Base URL: {settings.base_url}")
    typer.echo(f"  Viewport: {settings.viewport_width}x{settings.viewport_height}")
    typer.echo(f"  Device Scale Factor: {settings.device_scale_factor}")
    typer.echo(f"  Rate Limit: {settings.requests_per_minute} requests/minute")
    typer.echo(f"  Min Delay: {settings.min_delay}s")
    typer.echo(f"  Max Delay: {settings.max_delay}s")
    typer.echo(f"  Screenshot Quality: {settings.screenshot_quality}")
    typer.echo(f"  Min OCR Density: {settings.min_ocr_density}")


if __name__ == "__main__":
    app() 