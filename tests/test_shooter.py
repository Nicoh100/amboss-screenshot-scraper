"""Tests for screenshot capture module."""

import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

from amboss.shooter import ScreenshotShooter


@pytest.fixture
def mock_page():
    """Create a mock Playwright page."""
    page = AsyncMock()
    
    # Mock viewport
    page.viewport_size = {"width": 1280, "height": 720}
    
    # Mock header elements
    header = AsyncMock()
    header.text_content.return_value = "Test Section"
    header.bounding_box.return_value = {"x": 0, "y": 100, "width": 1280, "height": 50}
    header.scroll_into_view_if_needed = AsyncMock()
    
    # Mock locator for headers
    locator = AsyncMock()
    locator.count.return_value = 1
    locator.nth.return_value = header
    
    page.locator.return_value = locator
    page.screenshot = AsyncMock()
    
    return page


@pytest.fixture
def temp_dir(tmp_path):
    """Create a temporary directory for test files."""
    return tmp_path


@pytest.mark.asyncio
async def test_shoot_sections_with_headers(mock_page, temp_dir):
    """Test screenshot capture with section headers."""
    shooter = ScreenshotShooter()
    
    # Mock successful screenshot
    mock_page.screenshot.return_value = None
    
    result = await shooter.shoot_sections(mock_page, "test-slug", "test-run", temp_dir)
    
    assert len(result) == 1
    assert result[0][0].endswith(".png")  # filename
    assert result[0][1] == 0  # index
    assert result[0][2] == "Test_Section"  # section title


@pytest.mark.asyncio
async def test_shoot_sections_no_headers(mock_page, temp_dir):
    """Test screenshot capture when no headers are found."""
    shooter = ScreenshotShooter()
    
    # Mock no headers
    mock_page.locator().count.return_value = 0
    mock_page.screenshot.return_value = None
    
    result = await shooter.shoot_sections(mock_page, "test-slug", "test-run", temp_dir)
    
    assert len(result) == 1
    assert result[0][0] == "full_page_test-slug.png"
    assert result[0][1] == 0
    assert result[0][2] == "full_page"


@pytest.mark.asyncio
async def test_sanitize_filename():
    """Test filename sanitization."""
    shooter = ScreenshotShooter()
    
    # Test normal text
    assert shooter._sanitize_filename("Normal Text") == "Normal Text"
    
    # Test with invalid characters
    assert shooter._sanitize_filename("Text with <invalid> chars") == "Text with _invalid_ chars"
    
    # Test with dots
    assert shooter._sanitize_filename("Text with dots...") == "Text with dots"
    
    # Test empty text
    assert shooter._sanitize_filename("") == "section"


@pytest.mark.asyncio
async def test_calculate_section_clip():
    """Test section clip calculation."""
    shooter = ScreenshotShooter()
    
    header_bbox = {"x": 0, "y": 100, "width": 1280, "height": 50}
    viewport = {"width": 1280, "height": 720}
    
    # Test first section
    clip = shooter._calculate_section_clip(header_bbox, viewport, 0)
    assert clip["x"] == 0
    assert clip["y"] == 50  # header_bbox["y"] - 50
    assert clip["width"] == 1280
    assert clip["height"] == 720  # min(1200, viewport["height"])
    
    # Test subsequent section
    clip = shooter._calculate_section_clip(header_bbox, viewport, 1)
    assert clip["height"] == 720  # min(1000, viewport["height"])


@pytest.mark.asyncio
async def test_get_screenshot_metrics(mock_page):
    """Test screenshot metrics calculation."""
    shooter = ScreenshotShooter()
    
    # Mock various content elements
    mock_page.locator.side_effect = lambda selector: AsyncMock(count=AsyncMock(return_value=1))
    mock_page.evaluate.return_value = 1000  # page height
    
    metrics = await shooter.get_screenshot_metrics(mock_page)
    
    assert "viewport_width" in metrics
    assert "viewport_height" in metrics
    assert "page_height" in metrics
    assert "section_count" in metrics
    assert "estimated_screenshots" in metrics 