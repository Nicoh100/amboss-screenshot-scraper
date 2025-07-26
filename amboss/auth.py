"""Authentication and browser context management for AMBOSS scraper."""

import json
from pathlib import Path
from typing import Optional

from playwright.async_api import Browser, BrowserContext, Page, async_playwright
from structlog import get_logger
from tenacity import retry, stop_after_attempt, wait_exponential

from .config import settings

logger = get_logger(__name__)


class AuthManager:
    """Manages browser authentication and context creation."""
    
    def __init__(self):
        self.playwright = None
        self.browser = None
    
    async def __aenter__(self):
        """Async context manager entry."""
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-accelerated-2d-canvas",
                "--no-first-run",
                "--no-zygote",
                "--disable-gpu"
            ]
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
    
    def load_cookies(self) -> dict:
        """Load cookies from the saved state file."""
        try:
            with open(settings.cookie_path, 'r', encoding='utf-8') as f:
                state = json.load(f)
            
            # Extract cookies from Playwright state
            if 'cookies' in state:
                return state['cookies']
            elif 'storageState' in state and 'cookies' in state['storageState']:
                return state['storageState']['cookies']
            else:
                logger.warning("No cookies found in state file", path=str(settings.cookie_path))
                return {}
                
        except FileNotFoundError:
            logger.error("Cookie file not found", path=str(settings.cookie_path))
            raise
        except json.JSONDecodeError as e:
            logger.error("Invalid JSON in cookie file", path=str(settings.cookie_path), error=str(e))
            raise
        except Exception as e:
            logger.error("Failed to load cookies", path=str(settings.cookie_path), error=str(e))
            raise
    
    async def create_context(self, **kwargs) -> BrowserContext:
        """Create a new browser context with authentication."""
        cookies = self.load_cookies()
        
        context_kwargs = {
            "viewport": {
                "width": settings.viewport_width,
                "height": settings.viewport_height
            },
            "device_scale_factor": settings.device_scale_factor,
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            **kwargs
        }
        
        context = await self.browser.new_context(**context_kwargs)
        
        if cookies:
            await context.add_cookies(cookies)
            logger.info("Loaded cookies into context", count=len(cookies))
        
        return context
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=2))
    async def verify_auth(self, page: Page) -> bool:
        """Verify that authentication is working by checking for login indicators."""
        try:
            # Navigate to a protected page
            await page.goto(f"{settings.base_url}/de", wait_until="networkidle")
            
            # Check for login indicators
            login_indicators = [
                "text=Anmelden",
                "text=Login",
                "[data-testid='login-button']",
                ".login-button"
            ]
            
            for indicator in login_indicators:
                try:
                    element = page.locator(indicator)
                    if await element.is_visible():
                        logger.warning("Login indicator found - authentication may have failed")
                        return False
                except:
                    continue
            
            # Check for user-specific elements that indicate successful auth
            auth_indicators = [
                "[data-testid='user-menu']",
                ".user-menu",
                "text=Profil",
                "text=Profile"
            ]
            
            for indicator in auth_indicators:
                try:
                    element = page.locator(indicator)
                    if await element.is_visible():
                        logger.info("Authentication verified successfully")
                        return True
                except:
                    continue
            
            # If we can access content without login prompts, assume we're authenticated
            logger.info("No login prompts found - assuming authenticated")
            return True
            
        except Exception as e:
            logger.error("Failed to verify authentication", error=str(e))
            raise
    
    async def refresh_auth(self, credentials_path: Optional[Path] = None) -> bool:
        """Refresh authentication by logging in with credentials."""
        if not credentials_path:
            credentials_path = settings.cookie_path.parent / "credentials.json"
        
        if not credentials_path.exists():
            logger.error("Credentials file not found", path=str(credentials_path))
            return False
        
        try:
            with open(credentials_path, 'r', encoding='utf-8') as f:
                credentials = json.load(f)
            
            context = await self.create_context()
            page = await context.new_page()
            
            # Navigate to login page
            await page.goto(f"{settings.base_url}/de/login", wait_until="networkidle")
            
            # Fill login form
            await page.fill("[name='email']", credentials.get('email', ''))
            await page.fill("[name='password']", credentials.get('password', ''))
            
            # Submit form
            await page.click("[type='submit']")
            
            # Wait for redirect
            await page.wait_for_load_state("networkidle")
            
            # Verify login was successful
            if await self.verify_auth(page):
                # Save new state
                state = await context.storage_state()
                with open(settings.cookie_path, 'w', encoding='utf-8') as f:
                    json.dump(state, f, indent=2)
                
                logger.info("Authentication refreshed successfully")
                await context.close()
                return True
            else:
                logger.error("Failed to refresh authentication")
                await context.close()
                return False
                
        except Exception as e:
            logger.error("Error refreshing authentication", error=str(e))
            return False


async def get_auth_manager() -> AuthManager:
    """Get authentication manager instance."""
    return AuthManager() 