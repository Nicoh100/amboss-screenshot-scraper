"""Database schema and operations for AMBOSS scraper."""

import asyncio
from datetime import datetime
from pathlib import Path
from typing import AsyncIterator, List, Optional, Tuple

import aiosqlite
from structlog import get_logger

from .config import settings

logger = get_logger(__name__)


class DatabaseManager:
    """Manages SQLite database operations."""
    
    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or settings.database_path
    
    async def __aenter__(self):
        """Async context manager entry."""
        self.conn = await aiosqlite.connect(self.db_path)
        await self.conn.execute("PRAGMA foreign_keys = ON")
        await self._create_tables()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.conn.close()
    
    async def _create_tables(self):
        """Create database tables if they don't exist."""
        await self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS urls (
                slug        TEXT PRIMARY KEY,
                url         TEXT NOT NULL,
                discovered  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status      TEXT CHECK(status IN ('pending','processing','done','failed_expansion','failed_validation')) DEFAULT 'pending',
                last_error  TEXT,
                retry_count INTEGER DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS runs (
                run_id      TEXT,
                slug        TEXT,
                started     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                finished    TIMESTAMP,
                ok          BOOLEAN,
                error_msg   TEXT,
                PRIMARY KEY (run_id, slug),
                FOREIGN KEY (slug) REFERENCES urls(slug)
            );

            CREATE TABLE IF NOT EXISTS images (
                run_id      TEXT,
                slug        TEXT,
                filename    TEXT,
                idx         INTEGER,
                section_title TEXT,
                created     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (run_id, slug, idx),
                FOREIGN KEY (run_id, slug) REFERENCES runs(run_id, slug)
            );

            CREATE INDEX IF NOT EXISTS idx_urls_status ON urls(status);
            CREATE INDEX IF NOT EXISTS idx_runs_started ON runs(started);
            CREATE INDEX IF NOT EXISTS idx_images_created ON images(created);
        """)
        await self.conn.commit()
    
    async def add_url(self, slug: str, url: str) -> bool:
        """Add a new URL to the database if it doesn't exist."""
        try:
            await self.conn.execute(
                "INSERT OR IGNORE INTO urls (slug, url) VALUES (?, ?)",
                (slug, url)
            )
            await self.conn.commit()
            return True
        except Exception as e:
            logger.error("Failed to add URL", slug=slug, url=url, error=str(e))
            return False
    
    async def get_pending_urls(self, limit: Optional[int] = None) -> List[Tuple[str, str]]:
        """Get pending URLs for processing."""
        query = "SELECT slug, url FROM urls WHERE status = 'pending'"
        if limit:
            query += f" LIMIT {limit}"
        
        async with self.conn.execute(query) as cursor:
            return await cursor.fetchall()
    
    async def get_failed_urls(self) -> List[Tuple[str, str, str]]:
        """Get failed URLs for retry."""
        async with self.conn.execute(
            "SELECT slug, url, last_error FROM urls WHERE status LIKE 'failed_%'"
        ) as cursor:
            return await cursor.fetchall()
    
    async def update_url_status(self, slug: str, status: str, error: Optional[str] = None):
        """Update URL status and error message."""
        if error:
            await self.conn.execute(
                "UPDATE urls SET status = ?, last_error = ?, retry_count = retry_count + 1 WHERE slug = ?",
                (status, error, slug)
            )
        else:
            await self.conn.execute(
                "UPDATE urls SET status = ? WHERE slug = ?",
                (status, slug)
            )
        await self.conn.commit()
    
    async def start_run(self, run_id: str, slug: str) -> bool:
        """Start a new run for a slug."""
        try:
            await self.conn.execute(
                "INSERT INTO runs (run_id, slug) VALUES (?, ?)",
                (run_id, slug)
            )
            await self.conn.commit()
            return True
        except Exception as e:
            logger.error("Failed to start run", run_id=run_id, slug=slug, error=str(e))
            return False
    
    async def finish_run(self, run_id: str, slug: str, ok: bool, error_msg: Optional[str] = None):
        """Finish a run with success/failure status."""
        await self.conn.execute(
            "UPDATE runs SET finished = CURRENT_TIMESTAMP, ok = ?, error_msg = ? WHERE run_id = ? AND slug = ?",
            (ok, error_msg, run_id, slug)
        )
        await self.conn.commit()
    
    async def add_image(self, run_id: str, slug: str, filename: str, idx: int, section_title: str):
        """Add an image record to the database."""
        await self.conn.execute(
            "INSERT INTO images (run_id, slug, filename, idx, section_title) VALUES (?, ?, ?, ?, ?)",
            (run_id, slug, filename, idx, section_title)
        )
        await self.conn.commit()
    
    async def get_run_images(self, run_id: str, slug: str) -> List[Tuple[str, int, str]]:
        """Get all images for a specific run."""
        async with self.conn.execute(
            "SELECT filename, idx, section_title FROM images WHERE run_id = ? AND slug = ? ORDER BY idx",
            (run_id, slug)
        ) as cursor:
            return await cursor.fetchall()
    
    async def get_stats(self) -> dict:
        """Get database statistics."""
        stats = {}
        
        # URL counts by status
        async with self.conn.execute(
            "SELECT status, COUNT(*) FROM urls GROUP BY status"
        ) as cursor:
            status_counts = await cursor.fetchall()
            stats["urls_by_status"] = dict(status_counts)
        
        # Total URLs
        async with self.conn.execute("SELECT COUNT(*) FROM urls") as cursor:
            stats["total_urls"] = (await cursor.fetchone())[0]
        
        # Total runs
        async with self.conn.execute("SELECT COUNT(*) FROM runs") as cursor:
            stats["total_runs"] = (await cursor.fetchone())[0]
        
        # Total images
        async with self.conn.execute("SELECT COUNT(*) FROM images") as cursor:
            stats["total_images"] = (await cursor.fetchone())[0]
        
        return stats


async def get_db() -> DatabaseManager:
    """Get database manager instance."""
    return DatabaseManager()


async def init_database():
    """Initialize database with tables."""
    async with DatabaseManager() as db:
        logger.info("Database initialized successfully")
        stats = await db.get_stats()
        logger.info("Database stats", **stats) 