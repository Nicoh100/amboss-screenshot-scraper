"""Content expansion module for AMBOSS articles."""

import asyncio
from typing import List, Optional

from playwright.async_api import Page
from structlog import get_logger
from tenacity import retry, stop_after_attempt, wait_exponential

from .config import settings

logger = get_logger(__name__)


class ExpansionFailure(Exception):
    """Raised when content expansion fails."""
    pass


class ContentExpander:
    """Handles expansion of collapsed content in AMBOSS articles."""
    
    def __init__(self):
        self.expand_selectors = [
            "[data-e2e-test-id='section-content-is-hidden']",
            "text='Weiterlesen'",
            "text='Read more'",
            "text='Mehr anzeigen'",
            "text='Show more'",
            "[data-testid='expand-button']",
            ".expand-button",
            ".read-more-button"
        ]
    
    @retry(stop=stop_after_attempt(4), wait=wait_exponential(multiplier=2))
    async def fully_expand(self, page: Page) -> None:
        """Expand all collapsed sections using multiple strategies."""
        logger.info("Starting content expansion")
        
        # Handle cookie consent first
        await self._handle_cookie_consent(page)
        
        # Skip navigation to article content - it's causing modal issues
        # await self._navigate_to_article_content(page)
        
        # Strategy 1: Click-based expansion
        await self._click_expansion_buttons(page)
        
        # Strategy 2: JavaScript fallback for stubborn elements
        await self._js_expansion_fallback(page)
        
        # Strategy 3: Wait for dynamic content
        await self._wait_for_dynamic_content(page)
        
        # Strategy 4: Final verification
        await self._verify_expansion(page)
        
        logger.info("Content expansion completed")
    
    async def _handle_cookie_consent(self, page: Page) -> None:
        """Comprehensive 4-tier modal handling system."""
        try:
            # Tier 1: Quick Escape
            await page.keyboard.press("Escape")
            await page.wait_for_timeout(500)
            
            # Tier 2: Comprehensive modal handling
            await self._tier2_comprehensive_handler(page)
            
            # Tier 3: Aggressive retry for stubborn modals
            await self._tier3_aggressive_retry(page)
            
            # Tier 4: Nuclear option - Remove all modals via JavaScript
            await self._nuclear_modal_removal(page)
            
            # Tier 5: Final escape for any remaining modals
            await page.keyboard.press("Escape")
            await page.wait_for_timeout(300)
                    
        except Exception as e:
            logger.debug(f"Popup handling failed: {e}")
            # Not critical, continue anyway
    
    async def _nuclear_modal_removal(self, page: Page) -> None:
        """Nuclear option: Remove all modals and overlays via JavaScript."""
        try:
            logger.info("🧨 Nuclear modal removal...")
            
            # Remove all modals and overlays
            await page.evaluate("""
                () => {
                    // Remove all modal containers
                    const modals = document.querySelectorAll('#ds-modal, [class*="modal"], [class*="overlay"], [class*="popup"], [role="dialog"]');
                    modals.forEach(modal => {
                        modal.remove();
                    });
                    
                    // Remove backdrop/overlay elements
                    const backdrops = document.querySelectorAll('[class*="backdrop"], [class*="overlay"], [class*="dim"]');
                    backdrops.forEach(backdrop => {
                        backdrop.remove();
                    });
                    
                    // Remove any fixed positioned elements that might be blocking
                    const fixedElements = document.querySelectorAll('[style*="position: fixed"]');
                    fixedElements.forEach(el => {
                        if (el.style.zIndex && parseInt(el.style.zIndex) > 1000) {
                            el.remove();
                        }
                    });
                    
                    // Enable scrolling
                    document.body.style.overflow = 'auto';
                    document.documentElement.style.overflow = 'auto';
                }
            """)
            
            await page.wait_for_timeout(1000)
            logger.info("✅ Nuclear modal removal completed")
            
        except Exception as e:
            logger.warning(f"Nuclear modal removal failed: {e}")
    
    async def _tier1_quick_escape(self, page: Page) -> None:
        """Tier 1: Quick escape using Escape key and basic selectors."""
        try:
            # Try Escape key first (works 70% of the time)
            await page.keyboard.press('Escape')
            await page.wait_for_timeout(1000)
            
            # Quick basic selectors
            quick_selectors = [
                'button:has-text("×")',
                'button:has-text("✕")',
                'button:has-text("Close")',
                'button:has-text("Schließen")',
                'button:has-text("OK")'
            ]
            
            for selector in quick_selectors:
                try:
                    element = await page.query_selector(selector)
                    if element and await element.is_visible():
                        await element.click()
                        logger.info(f"Tier 1: Quick escape with {selector}")
                        await page.wait_for_timeout(1000)
                        break
                except:
                    continue
                    
        except Exception as e:
            logger.debug(f"Tier 1 quick escape failed: {e}")
    
    async def _tier2_comprehensive_handler(self, page: Page) -> None:
        """Tier 2: Comprehensive popup handling targeting AMBOSS's #ds-modal system."""
        try:
            # Handle AMBOSS's main modal system (#ds-modal) - AGGRESSIVE APPROACH
            ds_modal = await page.query_selector('#ds-modal')
            if ds_modal:
                logger.info("Found AMBOSS ds-modal, using aggressive close strategy...")
                
                # Strategy 1: Try to find close button with deep DOM walk
                close_selectors = [
                    'button[aria-label*="Close"]',
                    'button[aria-label*="Schließen"]',
                    'button:has-text("×")',
                    'button:has-text("✕")',
                    'button:has-text("Close")',
                    'button:has-text("Schließen")',
                    '[data-testid*="close"]',
                    '[data-testid*="dismiss"]',
                    '.close-button',
                    '.modal-close',
                    'button[class*="close"]',
                    'div[role="button"][class*="close"]',
                    'svg[class*="close"]',
                    'button svg[class*="close"]'
                ]
                
                close_button = None
                for selector in close_selectors:
                    try:
                        # Search within the modal first
                        close_button = await ds_modal.query_selector(selector)
                        if close_button and await close_button.is_visible():
                            logger.info(f"Found close button with selector: {selector}")
                            break
                        
                        # If not found in modal, search globally
                        close_button = await page.query_selector(selector)
                        if close_button and await close_button.is_visible():
                            logger.info(f"Found global close button with selector: {selector}")
                            break
                    except Exception:
                        continue
                
                if close_button:
                    logger.info("Attempting to close modal...")
                    try:
                        await close_button.click(force=True)
                        await page.wait_for_timeout(2000)
                        logger.info("Modal close successful")
                    except Exception as e:
                        logger.warning(f"Click failed, trying JavaScript: {e}")
                        # JavaScript fallback
                        await page.evaluate("""
                            () => {
                                const modal = document.querySelector('#ds-modal');
                                if (modal) {
                                    const closeBtn = modal.querySelector('button[aria-label*="Close"], button:has-text("×"), button:has-text("✕"), [data-testid*="close"]');
                                    if (closeBtn) closeBtn.click();
                                }
                            }
                        """)
                        await page.wait_for_timeout(1000)
                else:
                    logger.info("No close button found, using JavaScript to remove modal...")
                    # Nuclear option: Remove modal via JavaScript
                    await page.evaluate("""
                        () => {
                            const modal = document.querySelector('#ds-modal');
                            if (modal) {
                                modal.remove();
                                // Also remove any backdrop
                                const backdrop = document.querySelector('[class*="backdrop"], [class*="overlay"]');
                                if (backdrop) backdrop.remove();
                            }
                        }
                    """)
                    await page.wait_for_timeout(1000)
            
            # Comprehensive popup selectors
            popup_selectors = [
                'button[aria-label*="Close"]',
                'button[aria-label*="Schließen"]',
                '.modal button[aria-label*="Close"]',
                '.popup button[aria-label*="Close"]',
                'button:has-text("×")',
                'button:has-text("✕")',
                'button:has-text("Close")',
                'button:has-text("Schließen")',
                'button:has-text("OK")',
                'button:has-text("Accept")',
                'button:has-text("Akzeptieren")',
                'button:has-text("Got it")',
                'button:has-text("Verstanden")',
                'button:has-text("Weiter")',
                'button:has-text("Next")',
                'button:has-text("Überspringen")',
                'button:has-text("Skip")',
                '[data-testid*="close"]',
                '[data-testid*="dismiss"]',
                '.close-button',
                '.modal-close'
            ]
            
            for selector in popup_selectors:
                try:
                    close_button = await page.query_selector(selector)
                    if close_button and await close_button.is_visible():
                        logger.info(f"Tier 2: Closing popup with selector: {selector}")
                        await close_button.click()
                        await page.wait_for_timeout(1000)
                        break
                except:
                    continue
            
            # Handle cookie consent specifically
            cookie_buttons = [
                'button:has-text("Accept all")',
                'button:has-text("Alle akzeptieren")',
                'button:has-text("Accept cookies")',
                'button:has-text("Cookies akzeptieren")',
                'button:has-text("I agree")',
                'button:has-text("Ich stimme zu")'
            ]
            
            for button_text in cookie_buttons:
                try:
                    cookie_button = await page.query_selector(button_text)
                    if cookie_button and await cookie_button.is_visible():
                        logger.info(f"Tier 2: Accepting cookies: {button_text}")
                        await cookie_button.click()
                        await page.wait_for_timeout(1000)
                        break
                except:
                    continue
                    
        except Exception as e:
            logger.debug(f"Tier 2 comprehensive handler failed: {e}")
    
    async def _tier3_aggressive_retry(self, page: Page) -> None:
        """Tier 3: Aggressive retry for stubborn modals."""
        try:
            # Retry multiple times with different strategies
            for attempt in range(3):
                logger.info(f"Tier 3: Aggressive retry attempt {attempt + 1}")
                
                # Try Escape again
                await page.keyboard.press('Escape')
                await page.wait_for_timeout(500)
                
                # Try clicking any visible close buttons
                close_selectors = [
                    'button[aria-label*="Close"]',
                    'button:has-text("×")',
                    'button:has-text("✕")',
                    'button:has-text("Close")',
                    'button:has-text("Schließen")',
                    '[data-testid*="close"]'
                ]
                
                for selector in close_selectors:
                    try:
                        elements = page.locator(selector)
                        count = await elements.count()
                        for i in range(count):
                            element = elements.nth(i)
                            if await element.is_visible():
                                await element.click()
                                logger.info(f"Tier 3: Aggressive close with {selector}")
                                await page.wait_for_timeout(500)
                    except:
                        continue
                
                # Check if modals are still present
                ds_modal = await page.query_selector('#ds-modal')
                if not ds_modal:
                    logger.info("Tier 3: No more ds-modal found, breaking")
                    break
                    
                await page.wait_for_timeout(1000)
                
        except Exception as e:
            logger.debug(f"Tier 3 aggressive retry failed: {e}")
    
    async def _navigate_to_article_content(self, page: Page) -> bool:
        """Navigate from features page to actual article content."""
        try:
            # Check if we're on a features page
            title = await page.locator('h1').first.text_content()
            if "Schlüsselfunktionen" in title or "Key features" in title:
                logger.info("Detected features page, trying to navigate to article content")
                
                # Look for article navigation links
                article_selectors = [
                    'a[href*="/article/"]',
                    'a:has-text("Artikel")',
                    'a:has-text("Article")',
                    'a:has-text("Lesen")',
                    'a:has-text("Read")',
                    'button:has-text("Artikel öffnen")',
                    'button:has-text("Open article")',
                    '[data-testid="article-link"]'
                ]
                
                for selector in article_selectors:
                    try:
                        elements = page.locator(selector)
                        count = await elements.count()
                        if count > 0:
                            logger.info(f"Found {count} article navigation elements: {selector}")
                            
                            # Click the first visible link
                            for i in range(count):
                                try:
                                    element = elements.nth(i)
                                    if await element.is_visible():
                                        await element.click()
                                        await page.wait_for_load_state("domcontentloaded", timeout=10000)
                                        
                                        # Check if we're now on the article
                                        new_title = await page.locator('h1').first.text_content()
                                        if "Schlüsselfunktionen" not in new_title and "Key features" not in new_title:
                                            logger.info(f"Successfully navigated to article: {new_title}")
                                            return True
                                        else:
                                            logger.warning("Still on features page after navigation")
                                            break
                                except Exception as e:
                                    logger.debug(f"Error clicking navigation element {i}: {e}")
                                    continue
                            break
                    except:
                        continue
                
                logger.warning("Could not navigate to article content from features page")
                return False
            
            return True  # Already on article page
            
        except Exception as e:
            logger.error(f"Error navigating to article content: {e}")
            return False
    
    async def _click_expansion_buttons(self, page: Page) -> None:
        """Click all visible expansion buttons."""
        # CRITICAL: Expand all collapsible sections first
        await self._expand_all_sections(page)
        
        # Then handle any remaining expansion buttons
        for selector in self.expand_selectors:
            try:
                elements = page.locator(selector)
                count = await elements.count()
                
                if count > 0:
                    logger.info(f"Found {count} elements with selector: {selector}")
                    
                    # Click each element
                    for i in range(count):
                        try:
                            element = elements.nth(i)
                            if await element.is_visible():
                                await element.click(force=True)
                                await page.wait_for_timeout(settings.expansion_delay)
                                logger.debug(f"Clicked element {i} with selector: {selector}")
                        except Exception as e:
                            logger.warning(f"Failed to click element {i} with selector {selector}", error=str(e))
                            continue
                            
            except Exception as e:
                logger.warning(f"Error processing selector {selector}", error=str(e))
                continue
    
    async def _expand_all_sections(self, page: Page) -> None:
        """CRITICAL: Expand all collapsible sections - this is what makes content visible."""
        try:
            logger.info("🔍 Expanding all collapsible sections...")
            
            # Strategy 1: AMBOSS-specific section headers (primary approach)
            sections = page.locator('section[data-e2e-test-id="section-with-header"] div.cebd2a302a3552c4--headerContainer[role="button"]')
            section_count = await sections.count()
            
            if section_count > 0:
                logger.info(f"Found {section_count} AMBOSS sections to expand")
                for i in range(section_count):
                    try:
                        section = sections.nth(i)
                        if await section.is_visible():
                            # Scroll section into view first
                            await section.scroll_into_view_if_needed()
                            await page.wait_for_timeout(500)
                            
                            # Try to click the section
                            try:
                                await section.click(timeout=5000)
                                await page.wait_for_timeout(500)  # Wait for expansion animation
                                logger.debug(f"Expanded section {i}")
                            except Exception as click_error:
                                logger.warning(f"Click failed for section {i}: {click_error}")
                                # Try JavaScript click as fallback
                                try:
                                    await page.evaluate("(element) => element.click()", section)
                                    await page.wait_for_timeout(500)
                                    logger.debug(f"Expanded section {i} via JavaScript")
                                except Exception as js_error:
                                    logger.warning(f"JavaScript click also failed for section {i}: {js_error}")
                                    continue
                    except Exception as e:
                        logger.warning(f"Failed to expand section {i}: {e}")
                        continue
            
            # Strategy 2: Try global toggle button as secondary approach (if individual clicks failed)
            try:
                global_toggle_button = page.locator('button[data-e2e-test-id="toggle-all-sections-button"]')
                if await global_toggle_button.count() > 0:
                    logger.info("Attempting global toggle button as secondary approach...")
                    
                    # Try JavaScript click on global toggle
                    try:
                        await page.evaluate("(element) => element.click()", global_toggle_button)
                        await page.wait_for_timeout(2000)
                        logger.info("✅ Global toggle completed via JavaScript")
                    except Exception as js_error:
                        logger.warning(f"Global toggle JavaScript click failed: {js_error}")
                else:
                    logger.info("No global toggle button found")
            except Exception as e:
                logger.warning(f"Failed to process global toggle button: {e}")
            
            # Strategy 3: Generic expandable content (final fallback)
            expand_selectors = [
                '[data-e2e-test-id="section-content-is-hidden"]',
                '[data-testid="expand-button"]',
                '.expand-button',
                '.read-more-button',
                'button:has-text("Weiterlesen")',
                'button:has-text("Read more")',
                'button:has-text("Mehr anzeigen")',
                'button:has-text("Show more")'
            ]
            
            for selector in expand_selectors:
                try:
                    elements = page.locator(selector)
                    count = await elements.count()
                    if count > 0:
                        logger.info(f"Found {count} expandable elements with selector: {selector}")
                        for i in range(count):
                            try:
                                element = elements.nth(i)
                                if await element.is_visible():
                                    # Try JavaScript click
                                    await page.evaluate("(element) => element.click()", element)
                                    await page.wait_for_timeout(300)
                            except Exception as e:
                                logger.warning(f"Failed to expand element {i} with {selector}: {e}")
                                continue
                except Exception as e:
                    logger.warning(f"Error processing expand selector {selector}: {e}")
                    continue
            
            # Wait for all content to load after expansion
            await page.wait_for_timeout(2000)
            logger.info("✅ Section expansion completed")
            
        except Exception as e:
            logger.error(f"Error during section expansion: {e}")
    
    async def verify_content_is_expanded(self, page: Page) -> bool:
        """Verify that content is actually expanded before screenshot."""
        try:
            # Check for expanded sections
            expanded_sections = page.locator('[data-e2e-test-id="section-content-is-shown"]')
            collapsed_sections = page.locator('[data-e2e-test-id="section-content-is-hidden"]')
            
            expanded_count = await expanded_sections.count()
            collapsed_count = await collapsed_sections.count()
            
            if collapsed_count > 0:
                logger.warning(f"Found {collapsed_count} collapsed sections - content not fully expanded!")
                return False
            
            if expanded_count == 0:
                logger.warning("No expanded sections found - content may not be loaded!")
                return False
            
            logger.info(f"✅ Content verified: {expanded_count} expanded sections")
            return True
            
        except Exception as e:
            logger.error(f"Error verifying content expansion: {e}")
            return False
    
    async def _js_expansion_fallback(self, page: Page) -> None:
        """Use JavaScript to expand stubborn elements."""
        try:
            # JavaScript to click all hidden content elements
            js_code = """
            () => {
                const selectors = [
                    '[data-e2e-test-id="section-content-is-hidden"]',
                    '[data-testid="expand-button"]',
                    '.expand-button',
                    '.read-more-button'
                ];
                
                let totalClicked = 0;
                
                selectors.forEach(selector => {
                    const elements = document.querySelectorAll(selector);
                    elements.forEach(el => {
                        if (el.offsetParent !== null) { // Check if visible
                            el.click();
                            totalClicked++;
                        }
                    });
                });
                
                return totalClicked;
            }
            """
            
            clicked_count = await page.evaluate(js_code)
            if clicked_count > 0:
                logger.info(f"JavaScript fallback clicked {clicked_count} elements")
                await page.wait_for_timeout(settings.expansion_delay * 2)
                
        except Exception as e:
            logger.warning("JavaScript expansion fallback failed", error=str(e))
    
    async def _wait_for_dynamic_content(self, page: Page) -> None:
        """Wait for dynamic content to load after expansion."""
        try:
            # Wait for network to be idle
            await page.wait_for_load_state("networkidle", timeout=10000)
            
            # Wait for any animations to complete
            await page.wait_for_timeout(1000)
            
            # Check for loading indicators and wait if present
            loading_selectors = [
                "[data-testid='loading']",
                ".loading",
                ".spinner",
                "[aria-busy='true']"
            ]
            
            for selector in loading_selectors:
                try:
                    loading_element = page.locator(selector)
                    if await loading_element.is_visible():
                        logger.info(f"Waiting for loading indicator: {selector}")
                        await loading_element.wait_for(state="hidden", timeout=10000)
                except:
                    continue
                    
        except Exception as e:
            logger.warning("Error waiting for dynamic content", error=str(e))
    
    async def _verify_expansion(self, page: Page) -> None:
        """Verify that all content has been expanded."""
        try:
            # Check for remaining hidden content
            hidden_selectors = [
                "[data-e2e-test-id='section-content-is-hidden']",
                "text='Weiterlesen'",
                "text='Read more'"
            ]
            
            total_hidden = 0
            for selector in hidden_selectors:
                try:
                    elements = page.locator(selector)
                    count = await elements.count()
                    if count > 0:
                        # Check if any are actually visible (might be false positives)
                        visible_count = 0
                        for i in range(count):
                            element = elements.nth(i)
                            if await element.is_visible():
                                visible_count += 1
                        
                        if visible_count > 0:
                            total_hidden += visible_count
                            logger.warning(f"Found {visible_count} still-visible elements with selector: {selector}")
                            
                except Exception as e:
                    logger.warning(f"Error checking selector {selector}", error=str(e))
                    continue
            
            if total_hidden > 0:
                raise ExpansionFailure(f"{total_hidden} sections still hidden after expansion")
            
            logger.info("Expansion verification passed - all content expanded")
            
        except Exception as e:
            if isinstance(e, ExpansionFailure):
                raise
            logger.error("Error during expansion verification", error=str(e))
            raise ExpansionFailure(f"Expansion verification failed: {str(e)}")
    
    async def get_content_metrics(self, page: Page) -> dict:
        """Get metrics about the page content."""
        try:
            # Count various content elements
            metrics = {}
            
            # Count headings
            headings = page.locator("h1, h2, h3, h4, h5, h6")
            metrics["headings"] = await headings.count()
            
            # Count paragraphs
            paragraphs = page.locator("p")
            metrics["paragraphs"] = await paragraphs.count()
            
            # Count lists
            lists = page.locator("ul, ol")
            metrics["lists"] = await lists.count()
            
            # Count tables
            tables = page.locator("table")
            metrics["tables"] = await tables.count()
            
            # Count images
            images = page.locator("img")
            metrics["images"] = await images.count()
            
            # Count expansion buttons (should be 0 if fully expanded)
            expand_buttons = page.locator("[data-e2e-test-id='section-content-is-hidden']")
            metrics["remaining_expand_buttons"] = await expand_buttons.count()
            
            # Get page height
            page_height = await page.evaluate("document.body.scrollHeight")
            metrics["page_height"] = page_height
            
            return metrics
            
        except Exception as e:
            logger.error("Error getting content metrics", error=str(e))
            return {}
    
    async def is_fully_expanded(self, page: Page) -> bool:
        """Check if the page is fully expanded."""
        try:
            # Check for any remaining expansion buttons
            expand_buttons = page.locator("[data-e2e-test-id='section-content-is-hidden']")
            count = await expand_buttons.count()
            
            if count == 0:
                return True
            
            # Check if any remaining buttons are actually visible
            visible_count = 0
            for i in range(count):
                element = expand_buttons.nth(i)
                if await element.is_visible():
                    visible_count += 1
            
            return visible_count == 0
            
        except Exception as e:
            logger.error("Error checking expansion status", error=str(e))
            return False


async def expand_content(page: Page) -> None:
    """Convenience function to expand content on a page."""
    expander = ContentExpander()
    await expander.fully_expand(page) 