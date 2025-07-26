"""Tests for validation module."""

import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from amboss.validator import ContentValidator, ValidationFailure


@pytest.fixture
def mock_page():
    """Create a mock Playwright page."""
    page = AsyncMock()
    
    # Mock screenshot
    page.screenshot.return_value = b"fake_image_data"
    
    # Mock locator for hidden sections
    locator = AsyncMock()
    locator.count.return_value = 0
    locator.nth.return_value = AsyncMock()
    locator.nth().is_visible.return_value = False
    
    page.locator.return_value = locator
    
    return page


@pytest.fixture
def temp_image(tmp_path):
    """Create a temporary image file for testing."""
    image_path = tmp_path / "test.png"
    # Create a simple test image (1x1 pixel)
    with open(image_path, "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\tpHYs\x00\x00\x0b\x13\x00\x00\x0b\x13\x01\x00\x9a\x9c\x18\x00\x00\x00\x07tIME\x07\xe5\x07\x1a\x0e\x1c\x0c\xc8\xc8\xc8\xc8\x00\x00\x00\x0cIDATx\x9cc```\x00\x00\x00\x04\x00\x01\xf5\xa7\xe4\xd8\x00\x00\x00\x00IEND\xaeB`\x82")
    return image_path


@pytest.mark.asyncio
async def test_validate_page_success(mock_page):
    """Test successful page validation."""
    validator = ContentValidator()
    
    # Mock successful validation
    with patch('amboss.validator.Image.open') as mock_image:
        mock_img = MagicMock()
        mock_img.convert.return_value = MagicMock()
        mock_image.return_value.__enter__.return_value = mock_img
        
        result = await validator.validate_page(mock_page)
        
        assert result["validation_passed"] is True
        assert result["expansion_valid"] is True
        assert result["content_density_valid"] is True
        assert result["hidden_sections_count"] == 0


@pytest.mark.asyncio
async def test_validate_page_hidden_sections(mock_page):
    """Test page validation with hidden sections."""
    validator = ContentValidator()
    
    # Mock hidden sections
    mock_page.locator().count.return_value = 1
    mock_page.locator().nth().is_visible.return_value = True
    
    with patch('amboss.validator.Image.open') as mock_image:
        mock_img = MagicMock()
        mock_img.convert.return_value = MagicMock()
        mock_image.return_value.__enter__.return_value = mock_img
        
        result = await validator.validate_page(mock_page)
        
        assert result["validation_passed"] is False
        assert result["expansion_valid"] is False
        assert result["hidden_sections_count"] == 1


@pytest.mark.asyncio
async def test_validate_screenshots_success(temp_image):
    """Test successful screenshot validation."""
    validator = ContentValidator()
    
    with patch('amboss.validator.Image.open') as mock_image:
        mock_img = MagicMock()
        mock_img.size = (100, 100)
        mock_img.convert.return_value = MagicMock()
        mock_image.return_value.__enter__.return_value = mock_img
        
        results = await validator.validate_screenshots([temp_image])
        
        assert len(results) == 1
        assert results[0]["valid"] is True
        assert results[0]["file"] == str(temp_image)


@pytest.mark.asyncio
async def test_validate_screenshots_file_not_found():
    """Test screenshot validation with missing file."""
    validator = ContentValidator()
    
    non_existent_path = Path("/non/existent/file.png")
    results = await validator.validate_screenshots([non_existent_path])
    
    assert len(results) == 1
    assert results[0]["valid"] is False
    assert "does not exist" in results[0]["error"]


@pytest.mark.asyncio
async def test_validate_screenshots_small_file(tmp_path):
    """Test screenshot validation with too small file."""
    validator = ContentValidator()
    
    small_file = tmp_path / "small.png"
    small_file.write_bytes(b"small")
    
    results = await validator.validate_screenshots([small_file])
    
    assert len(results) == 1
    assert results[0]["valid"] is False
    assert "too small" in results[0]["error"]


@pytest.mark.asyncio
async def test_check_hidden_sections_none(mock_page):
    """Test checking for hidden sections when none exist."""
    validator = ContentValidator()
    
    count = await validator._check_hidden_sections(mock_page)
    assert count == 0


@pytest.mark.asyncio
async def test_check_hidden_sections_found(mock_page):
    """Test checking for hidden sections when they exist."""
    validator = ContentValidator()
    
    # Mock hidden sections
    mock_page.locator().count.return_value = 2
    mock_page.locator().nth().is_visible.return_value = True
    
    count = await validator._check_hidden_sections(mock_page)
    assert count == 2


@pytest.mark.asyncio
async def test_get_validation_summary():
    """Test validation summary generation."""
    validator = ContentValidator()
    
    results = [
        {"valid": True, "density_score": 0.8, "error": None},
        {"valid": True, "density_score": 0.9, "error": None},
        {"valid": False, "density_score": 0.0, "error": "Test error"}
    ]
    
    summary = await validator.get_validation_summary(results)
    
    assert summary["total_files"] == 3
    assert summary["valid_files"] == 2
    assert summary["failed_files"] == 1
    assert summary["success_rate"] == 2/3
    assert summary["average_density"] == 0.85
    assert len(summary["errors"]) == 1 