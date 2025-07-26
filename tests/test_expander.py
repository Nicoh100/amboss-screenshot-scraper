"""Tests for content expansion module."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from amboss.expander import ContentExpander, ExpansionFailure


@pytest.fixture
def mock_page():
    """Create a mock Playwright page."""
    page = AsyncMock()
    
    # Mock locator methods
    locator = AsyncMock()
    locator.count.return_value = 2
    locator.nth.return_value = AsyncMock()
    locator.nth().is_visible.return_value = True
    locator.nth().click = AsyncMock()
    
    page.locator.return_value = locator
    page.wait_for_timeout = AsyncMock()
    page.evaluate = AsyncMock()
    page.wait_for_load_state = AsyncMock()
    
    return page


@pytest.mark.asyncio
async def test_fully_expand_success(mock_page):
    """Test successful content expansion."""
    expander = ContentExpander()
    
    # Mock successful expansion
    mock_page.locator().count.return_value = 0  # No hidden elements after expansion
    
    await expander.fully_expand(mock_page)
    
    # Verify expansion attempts were made
    assert mock_page.locator().count.called
    assert mock_page.wait_for_timeout.called


@pytest.mark.asyncio
async def test_fully_expand_failure(mock_page):
    """Test expansion failure with remaining hidden elements."""
    expander = ContentExpander()
    
    # Mock remaining hidden elements
    mock_page.locator().count.return_value = 1
    mock_page.locator().nth().is_visible.return_value = True
    
    with pytest.raises(ExpansionFailure):
        await expander.fully_expand(mock_page)


@pytest.mark.asyncio
async def test_is_fully_expanded_true(mock_page):
    """Test is_fully_expanded returns True when no hidden elements."""
    expander = ContentExpander()
    
    # Mock no hidden elements
    mock_page.locator().count.return_value = 0
    
    result = await expander.is_fully_expanded(mock_page)
    assert result is True


@pytest.mark.asyncio
async def test_is_fully_expanded_false(mock_page):
    """Test is_fully_expanded returns False when hidden elements exist."""
    expander = ContentExpander()
    
    # Mock hidden elements
    mock_page.locator().count.return_value = 1
    mock_page.locator().nth().is_visible.return_value = True
    
    result = await expander.is_fully_expanded(mock_page)
    assert result is False


@pytest.mark.asyncio
async def test_get_content_metrics(mock_page):
    """Test content metrics calculation."""
    expander = ContentExpander()
    
    # Mock various content elements
    mock_page.locator.side_effect = lambda selector: AsyncMock(count=AsyncMock(return_value=1))
    mock_page.evaluate.return_value = 1000  # page height
    
    metrics = await expander.get_content_metrics(mock_page)
    
    assert "headings" in metrics
    assert "paragraphs" in metrics
    assert "lists" in metrics
    assert "tables" in metrics
    assert "images" in metrics
    assert "remaining_expand_buttons" in metrics
    assert "page_height" in metrics 