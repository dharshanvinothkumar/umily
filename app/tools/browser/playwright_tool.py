"""
Umily — Playwright Browser Tool

Automates web interactions: navigation, clicks, typing, content extraction, and screenshots.
"""

from pathlib import Path
from typing import Any, Dict, Optional
from loguru import logger

try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False


class BrowserTool:
    """Browser interaction controller using Playwright."""

    def __init__(self, headless: bool = True) -> None:
        self.headless = headless
        self._browser = None
        self._page = None
        self._playwright = None

    def _ensure_browser(self) -> bool:
        """Start browser instance if Playwright is installed."""
        if not PLAYWRIGHT_AVAILABLE:
            logger.info("Playwright not installed. BrowserTool operating in simulation/fallback mode.")
            return False

        if self._page is not None:
            return True

        try:
            self._playwright = sync_playwright().start()
            self._browser = self._playwright.chromium.launch(headless=self.headless)
            self._page = self._browser.new_page()
            return True
        except Exception as e:
            logger.warning(f"Failed to start Playwright browser: {e}. Falling back to simulation mode.")
            return False

    def navigate(self, url: str) -> Dict[str, Any]:
        """Navigate browser to a URL."""
        if not url.startswith(("http://", "https://")):
            url = f"https://{url}"

        logger.info(f"Browser navigating to: {url}")
        if self._ensure_browser():
            try:
                self._page.goto(url, timeout=30000)
                title = self._page.title()
                return {
                    "success": True,
                    "message": f"Successfully navigated to {url} (Title: '{title}')",
                    "url": url,
                    "title": title,
                }
            except Exception as e:
                logger.error(f"Playwright navigation failed: {e}")
                return {"success": False, "error": str(e)}
        else:
            return {
                "success": True,
                "message": f"Simulated navigation to {url}",
                "url": url,
                "fallback": True,
            }

    def click(self, selector: str) -> Dict[str, Any]:
        """Click an element matching CSS or XPath selector."""
        logger.info(f"Browser clicking element: {selector}")
        if self._ensure_browser():
            try:
                self._page.click(selector, timeout=10000)
                return {
                    "success": True,
                    "message": f"Successfully clicked element: {selector}",
                }
            except Exception as e:
                logger.error(f"Playwright click failed for '{selector}': {e}")
                return {"success": False, "error": str(e)}
        else:
            return {
                "success": True,
                "message": f"Simulated click on selector '{selector}'",
                "fallback": True,
            }

    def type_text(self, selector: str, text: str) -> Dict[str, Any]:
        """Type text into an input element."""
        logger.info(f"Browser typing text into '{selector}'")
        if self._ensure_browser():
            try:
                self._page.fill(selector, text, timeout=10000)
                return {
                    "success": True,
                    "message": f"Successfully typed text into element: {selector}",
                }
            except Exception as e:
                logger.error(f"Playwright type failed for '{selector}': {e}")
                return {"success": False, "error": str(e)}
        else:
            return {
                "success": True,
                "message": f"Simulated typing into '{selector}'",
                "fallback": True,
            }

    def get_content(self, selector: Optional[str] = None) -> Dict[str, Any]:
        """Extract text or inner HTML from page or specific selector."""
        if self._ensure_browser():
            try:
                if selector:
                    content = self._page.inner_text(selector)
                else:
                    content = self._page.content()
                return {
                    "success": True,
                    "content": content[:5000],  # Return first 5k chars
                }
            except Exception as e:
                logger.error(f"Playwright get_content failed: {e}")
                return {"success": False, "error": str(e)}
        else:
            return {
                "success": True,
                "content": "Simulated browser content payload",
                "fallback": True,
            }

    def take_screenshot(self, path: Optional[str] = None) -> Dict[str, Any]:
        """Capture browser screenshot and save to disk."""
        target_path = path or "logs/screenshot.png"
        Path(target_path).parent.mkdir(parents=True, exist_ok=True)

        if self._ensure_browser():
            try:
                self._page.screenshot(path=target_path)
                return {
                    "success": True,
                    "message": f"Screenshot saved to {target_path}",
                    "path": target_path,
                }
            except Exception as e:
                logger.error(f"Playwright screenshot failed: {e}")
                return {"success": False, "error": str(e)}
        else:
            return {
                "success": True,
                "message": f"Simulated screenshot saved to {target_path}",
                "path": target_path,
                "fallback": True,
            }

    def close(self) -> None:
        """Close browser resources."""
        try:
            if self._page:
                self._page.close()
            if self._browser:
                self._browser.close()
            if self._playwright:
                self._playwright.stop()
        except Exception as e:
            logger.warning(f"Error closing Playwright browser: {e}")
        finally:
            self._page = None
            self._browser = None
            self._playwright = None
