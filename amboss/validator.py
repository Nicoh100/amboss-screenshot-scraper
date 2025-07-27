"""Validation module for screenshot quality and content completeness."""

import asyncio
import io
from pathlib import Path
from typing import List, Optional, Tuple

from PIL import Image, ImageStat
from playwright.async_api import Page
from structlog import get_logger

from .config import settings

logger = get_logger(__name__)


class ValidationFailure(Exception):
    """Raised when validation fails."""
    pass


class ContentValidator:
    """Validates screenshot quality and content completeness."""
    
    def __init__(self):
        self.min_ocr_density = settings.min_ocr_density
        self.ocr_stddev_threshold = settings.ocr_stddev_threshold
    
    async def validate_page(self, page: Page) -> dict:
        """Validate the entire page for completeness and quality."""
        logger.info("Starting page validation")
        
        validation_results = {
            "expansion_valid": False,
            "hidden_sections_count": 0,
            "validation_passed": False,
            "errors": []
        }
        
        try:
            # Check for hidden sections only
            hidden_count = await self._check_hidden_sections(page)
            validation_results["hidden_sections_count"] = hidden_count
            validation_results["expansion_valid"] = hidden_count == 0
            
            if hidden_count > 0:
                error_msg = f"Found {hidden_count} hidden sections"
                validation_results["errors"].append(error_msg)
                logger.warning(error_msg)
            
            # Overall validation result - only check expansion
            validation_results["validation_passed"] = validation_results["expansion_valid"]
            
            if validation_results["validation_passed"]:
                logger.info("Page validation passed")
            else:
                logger.warning("Page validation failed", errors=validation_results["errors"])
            
            return validation_results
            
        except Exception as e:
            error_msg = f"Validation error: {str(e)}"
            validation_results["errors"].append(error_msg)
            logger.error(error_msg)
            return validation_results
    
    async def validate_screenshots(
        self, 
        screenshot_paths: List[Path]
    ) -> List[dict]:
        """Validate individual screenshot files."""
        validation_results = []
        
        for screenshot_path in screenshot_paths:
            try:
                result = await self._validate_single_screenshot(screenshot_path)
                validation_results.append(result)
                
            except Exception as e:
                logger.error(f"Error validating screenshot {screenshot_path}", error=str(e))
                validation_results.append({
                    "file": str(screenshot_path),
                    "valid": False,
                    "error": str(e)
                })
        
        return validation_results
    
    async def _check_hidden_sections(self, page: Page) -> int:
        """Check for any remaining hidden sections."""
        hidden_selectors = [
            "[data-e2e-test-id='section-content-is-hidden']",
            "text='Weiterlesen'",
            "text='Read more'",
            "text='Mehr anzeigen'",
            "text='Show more'"
        ]
        
        total_hidden = 0
        
        for selector in hidden_selectors:
            try:
                elements = page.locator(selector)
                count = await elements.count()
                
                if count > 0:
                    # Check if any are actually visible
                    visible_count = 0
                    for i in range(count):
                        element = elements.nth(i)
                        if await element.is_visible():
                            visible_count += 1
                    
                    total_hidden += visible_count
                    
            except Exception as e:
                logger.warning(f"Error checking hidden sections with selector {selector}", error=str(e))
                continue
        
        return total_hidden
    
    async def _check_content_density(self, page: Page) -> float:
        """Check content density using a simple heuristic."""
        try:
            # Take a screenshot for analysis
            screenshot_bytes = await page.screenshot(type="png")
            
            # Analyze image using Pillow
            with Image.open(io.BytesIO(screenshot_bytes)) as img:
                # Convert to grayscale for analysis
                gray_img = img.convert('L')
                
                # Calculate statistics
                stat = ImageStat.Stat(gray_img)
                
                # Use standard deviation as a proxy for content density
                # Higher stddev = more variation = more content
                stddev = stat.stddev[0]
                
                # Normalize to a 0-1 scale (empirical threshold)
                density_score = min(1.0, stddev / 100.0)
                
                logger.debug(f"Content density analysis", 
                           stddev=stddev, 
                           density_score=density_score)
                
                return density_score
                
        except Exception as e:
            logger.error("Error checking content density", error=str(e))
            return 0.0
    
    async def _validate_single_screenshot(self, screenshot_path: Path) -> dict:
        """Validate a single screenshot file."""
        result = {
            "file": str(screenshot_path),
            "valid": True,
            "file_size": 0,
            "dimensions": None,
            "density_score": 0.0,
            "error": None
        }
        
        try:
            # Check file exists and has reasonable size
            if not screenshot_path.exists():
                raise ValidationFailure("Screenshot file does not exist")
            
            file_size = screenshot_path.stat().st_size
            result["file_size"] = file_size
            
            if file_size < 1024:  # Less than 1KB
                raise ValidationFailure(f"Screenshot file too small: {file_size} bytes")
            
            # Open and analyze image
            with Image.open(screenshot_path) as img:
                result["dimensions"] = img.size
                
                # Check dimensions
                if img.size[0] < 100 or img.size[1] < 100:
                    raise ValidationFailure(f"Screenshot dimensions too small: {img.size}")
                
                # Calculate content density
                gray_img = img.convert('L')
                stat = ImageStat.Stat(gray_img)
                stddev = stat.stddev[0]
                
                # Normalize density score
                density_score = min(1.0, stddev / 100.0)
                result["density_score"] = density_score
                
                if density_score < self.min_ocr_density:
                    raise ValidationFailure(
                        f"Content density too low: {density_score:.2f} < {self.min_ocr_density}"
                    )
            
            logger.debug(f"Screenshot validation passed", 
                       file=str(screenshot_path),
                       size=file_size,
                       dimensions=result["dimensions"],
                       density=density_score)
            
        except Exception as e:
            result["valid"] = False
            result["error"] = str(e)
            logger.warning(f"Screenshot validation failed", 
                         file=str(screenshot_path),
                         error=str(e))
        
        return result
    
    async def get_validation_summary(self, validation_results: List[dict]) -> dict:
        """Get a summary of validation results."""
        total_files = len(validation_results)
        valid_files = sum(1 for r in validation_results if r.get("valid", False))
        failed_files = total_files - valid_files
        
        # Calculate average density score
        density_scores = [r.get("density_score", 0) for r in validation_results if r.get("valid", False)]
        avg_density = sum(density_scores) / len(density_scores) if density_scores else 0
        
        # Collect errors
        errors = []
        for result in validation_results:
            if not result.get("valid", False) and result.get("error"):
                errors.append(result["error"])
        
        return {
            "total_files": total_files,
            "valid_files": valid_files,
            "failed_files": failed_files,
            "success_rate": valid_files / total_files if total_files > 0 else 0,
            "average_density": avg_density,
            "errors": errors
        }


async def validate_page(page: Page) -> dict:
    """Convenience function to validate a page."""
    validator = ContentValidator()
    return await validator.validate_page(page)


async def validate_screenshots(screenshot_paths: List[Path]) -> List[dict]:
    """Convenience function to validate screenshots."""
    validator = ContentValidator()
    return await validator.validate_screenshots(screenshot_paths) 