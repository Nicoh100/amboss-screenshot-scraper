"""Screenshot capture module for AMBOSS articles."""

import asyncio
from pathlib import Path
from typing import List, Optional, Tuple

from PIL import Image
from playwright.async_api import Page
from structlog import get_logger

from .config import settings

logger = get_logger(__name__)


class ScreenshotShooter:
    """Handles intelligent screenshot capture of article sections."""
    
    def __init__(self):
        self.section_selectors = [
            "h1", "h2", "h3", "h4", "h5", "h6",
            "[data-testid='section-header']",
            ".section-header",
            ".article-section"
        ]
    
    async def shoot_sections(
        self, 
        page: Page, 
        slug: str, 
        run_id: str, 
        outdir: Path
    ) -> List[Tuple[str, int, str]]:
        """Capture screenshots of all logical sections in the article."""
        logger.info("Starting section screenshot capture", slug=slug, run_id=run_id)
        
        # Create output directory
        slug_dir = outdir / slug / run_id
        slug_dir.mkdir(parents=True, exist_ok=True)
        
        # Find the main content area first
        content_area = await self._find_content_area(page)
        if not content_area:
            logger.warning("No content area found, capturing full page", slug=slug)
            return await self._capture_full_page(page, slug, run_id, slug_dir)
        
        logger.info("Found content area", 
                   x=content_area["x"], 
                   y=content_area["y"], 
                   width=content_area["width"], 
                   height=content_area["height"])
        
        # Get all section headers within the content area
        headers = await self._get_section_headers(page, content_area)
        
        if not headers:
            logger.warning("No section headers found, capturing content area", slug=slug)
            return await self._capture_content_area(page, slug, run_id, slug_dir, content_area)
        
        # Capture each section
        captured_sections = []
        for i, header in enumerate(headers):
            try:
                filename, section_title = await self._capture_section(
                    page, header, i, slug_dir, content_area
                )
                captured_sections.append((filename, i, section_title))
                logger.debug(f"Captured section {i}", title=section_title, filename=filename)
                
            except Exception as e:
                logger.error(f"Failed to capture section {i}", error=str(e))
                continue
        
        logger.info("Section capture completed", 
                   slug=slug, 
                   total_sections=len(captured_sections))
        
        return captured_sections
    
    async def _find_content_area(self, page: Page) -> Optional[dict]:
        """Use fixed hardcoded content area parameters for AMBOSS articles."""
        # Fixed hardcoded parameters for AMBOSS article content area
        article_clip = {
            "x": 380,          # Skip left sidebar (updated from 390)
            "y": 56,           # Skip the sticky nav bar
            "width": 848,      # Measured article column width
            "height": 1200     # Fixed height per screenshot (updated from 17848)
        }
        
        logger.info("Using fixed hardcoded content area parameters", 
                   x=article_clip["x"], 
                   y=article_clip["y"], 
                   width=article_clip["width"], 
                   height=article_clip["height"])
        
        return article_clip
    
    async def _get_section_headers(self, page: Page, content_area: dict) -> List:
        """Get all section headers from the content area."""
        headers = []
        
        for selector in self.section_selectors:
            try:
                elements = page.locator(selector)
                count = await elements.count()
                
                for i in range(count):
                    element = elements.nth(i)
                    if await element.is_visible():
                        bbox = await element.bounding_box()
                        if bbox:
                            # Check if header is within content area
                            if (bbox["x"] >= content_area["x"] and 
                                bbox["x"] + bbox["width"] <= content_area["x"] + content_area["width"]):
                                headers.append(element)
                        
            except Exception as e:
                logger.warning(f"Error getting headers with selector {selector}", error=str(e))
                continue
        
        # Sort headers by their position on the page
        sorted_headers = []
        for header in headers:
            try:
                bbox = await header.bounding_box()
                if bbox:
                    sorted_headers.append((bbox["y"], header))
            except:
                continue
        
        sorted_headers.sort(key=lambda x: x[0])
        return [header for _, header in sorted_headers]
    
    async def _capture_section(
        self, 
        page: Page, 
        header, 
        index: int, 
        outdir: Path,
        content_area: dict
    ) -> Tuple[str, str]:
        """Capture a single section starting from a header."""
        try:
            # Scroll down to reveal the full article content first
            if index == 0:
                logger.info("Scrolling to reveal full article content")
                await page.evaluate("window.scrollTo(0, 1000)")
                await asyncio.sleep(2)
            
            # Get header text for filename
            header_text = await header.text_content()
            if header_text:
                header_text = self._sanitize_filename(header_text.strip())
            else:
                header_text = f"section_{index:03d}"
            
            # Scroll header into view
            await header.scroll_into_view_if_needed()
            await page.wait_for_timeout(500)  # Wait for scroll to complete
            
            # Get header bounding box
            header_bbox = await header.bounding_box()
            if not header_bbox:
                raise ValueError("Could not get header bounding box")
            
            # Calculate capture area using content area bounds
            clip = self._calculate_section_clip_with_content_area(
                header_bbox, content_area, index
            )
            
            # Capture screenshot
            filename = f"sec_{index:03d}_{header_text}.png"
            filepath = outdir / filename
            
            await page.screenshot(
                path=str(filepath),
                clip=clip,
                type="png"
            )
            
            # Post-process image
            await self._post_process_image(filepath)
            
            return filename, header_text
            
        except Exception as e:
            logger.error(f"Error capturing section {index}", error=str(e))
            raise
    
    async def _capture_content_area(
        self, 
        page: Page, 
        slug: str, 
        run_id: str, 
        outdir: Path,
        content_area: dict
    ) -> List[Tuple[str, int, str]]:
        """Capture the content area in chunks when no sections are found."""
        try:
            # Scroll down to reveal the full article content
            logger.info("Scrolling to reveal full article content")
            await page.evaluate("window.scrollTo(0, 1000)")
            await asyncio.sleep(2)
            
            # Calculate chunks based on content area height
            chunk_height = 1000  # Target chunk height
            total_height = content_area["height"]
            chunks = []
            
            y_start = content_area["y"]
            chunk_index = 0
            
            while y_start < content_area["y"] + total_height:
                chunk_end = min(y_start + chunk_height, content_area["y"] + total_height)
                chunk_height_actual = chunk_end - y_start
                
                clip = {
                    "x": content_area["x"],
                    "y": y_start,
                    "width": content_area["width"],
                    "height": chunk_height_actual
                }
                
                filename = f"content_chunk_{chunk_index:03d}_{slug}.png"
                filepath = outdir / filename
                
                await page.screenshot(
                    path=str(filepath),
                    clip=clip,
                    type="png"
                )
                
                await self._post_process_image(filepath)
                chunks.append((filename, chunk_index, f"content_chunk_{chunk_index}"))
                
                y_start = chunk_end
                chunk_index += 1
            
            return chunks
            
        except Exception as e:
            logger.error("Error capturing content area", error=str(e))
            raise
    
    async def _capture_full_page(
        self, 
        page: Page, 
        slug: str, 
        run_id: str, 
        outdir: Path
    ) -> List[Tuple[str, int, str]]:
        """Capture the full page when no content area is found."""
        try:
            filename = f"full_page_{slug}.png"
            filepath = outdir / filename
            
            await page.screenshot(
                path=str(filepath),
                type="png",
                full_page=True
            )
            
            # Post-process image
            await self._post_process_image(filepath)
            
            return [(filename, 0, "full_page")]
            
        except Exception as e:
            logger.error("Error capturing full page", error=str(e))
            raise
    
    def _calculate_section_clip_with_content_area(
        self, 
        header_bbox: dict, 
        content_area: dict, 
        index: int
    ) -> dict:
        """Calculate the clip area for a section screenshot using content area bounds."""
        # Start capture slightly above the header for context
        y_start = max(content_area["y"], header_bbox["y"] - 50)
        
        # Calculate height - try to capture reasonable amount of content
        # For first section, capture more content
        if index == 0:
            height = min(1200, content_area["height"])
        else:
            height = min(1000, content_area["height"])
        
        # Ensure we don't go beyond content area bounds
        max_y = content_area["y"] + content_area["height"]
        y_end = min(y_start + height, max_y)
        actual_height = y_end - y_start
        
        return {
            "x": content_area["x"],
            "y": y_start,
            "width": content_area["width"],
            "height": actual_height
        }
    
    def _calculate_section_clip(
        self, 
        header_bbox: dict, 
        viewport: dict, 
        index: int
    ) -> dict:
        """Calculate the clip area for a section screenshot."""
        # Start capture slightly above the header for context
        y_start = max(0, header_bbox["y"] - 50)
        
        # Calculate height - try to capture reasonable amount of content
        # For first section, capture more content
        if index == 0:
            height = min(1200, viewport["height"])
        else:
            height = min(1000, viewport["height"])
        
        return {
            "x": 0,
            "y": y_start,
            "width": viewport["width"],
            "height": height
        }
    
    def _sanitize_filename(self, text: str) -> str:
        """Sanitize text for use in filename."""
        import re
        
        # Remove or replace invalid characters
        sanitized = re.sub(r'[<>:"/\\|?*]', '_', text)
        
        # Limit length
        if len(sanitized) > 50:
            sanitized = sanitized[:50]
        
        # Remove leading/trailing spaces and dots
        sanitized = sanitized.strip(' .')
        
        return sanitized or "section"
    
    async def _post_process_image(self, filepath: Path) -> None:
        """Post-process captured image (DPI tagging, validation)."""
        try:
            # Open image with Pillow
            with Image.open(filepath) as img:
                # Set DPI for proper scaling
                dpi = int(96 * settings.device_scale_factor)
                img.info['dpi'] = (dpi, dpi)
                
                # Save with metadata
                img.save(filepath, 'PNG', dpi=(dpi, dpi))
                
            # Verify file was created and has reasonable size
            if filepath.exists():
                file_size = filepath.stat().st_size
                if file_size < 1024:  # Less than 1KB
                    logger.warning("Screenshot file seems too small", 
                                 filepath=str(filepath), 
                                 size=file_size)
                    
        except Exception as e:
            logger.error("Error post-processing image", filepath=str(filepath), error=str(e))
    
    async def get_screenshot_metrics(self, page: Page) -> dict:
        """Get metrics about the page for screenshot planning."""
        try:
            metrics = {}
            
            # Get page dimensions
            viewport = page.viewport_size
            metrics["viewport_width"] = viewport["width"]
            metrics["viewport_height"] = viewport["height"]
            
            # Get full page height
            page_height = await page.evaluate("document.body.scrollHeight")
            metrics["page_height"] = page_height
            
            # Find content area
            content_area = await self._find_content_area(page)
            if content_area:
                metrics["content_area_x"] = content_area["x"]
                metrics["content_area_y"] = content_area["y"]
                metrics["content_area_width"] = content_area["width"]
                metrics["content_area_height"] = content_area["height"]
            
            # Count section headers
            headers = await self._get_section_headers(page, content_area) if content_area else []
            metrics["section_count"] = len(headers)
            
            # Estimate screenshots needed
            if metrics["section_count"] > 0:
                metrics["estimated_screenshots"] = metrics["section_count"]
            else:
                metrics["estimated_screenshots"] = 1  # Full page or content area
            
            return metrics
            
        except Exception as e:
            logger.error("Error getting screenshot metrics", error=str(e))
            return {}


async def capture_sections(
    page: Page, 
    slug: str, 
    run_id: str, 
    outdir: Path
) -> List[Tuple[str, int, str]]:
    """Convenience function to capture section screenshots."""
    shooter = ScreenshotShooter()
    return await shooter.shoot_sections(page, slug, run_id, outdir) 