"""
Termux Automation Module for Link Opening and Clicking

This module provides functionality to open links and perform clicks
directly on the Android device where Termux is running.
"""

import time
import subprocess
import logging
from typing import Optional, Tuple

logger = logging.getLogger("termux_automation")

class TermuxLinkOpener:
    """Handles opening links directly on the Android device"""

    @staticmethod
    def open_link_in_browser(url: str) -> bool:
        """Open a link in the default browser using Termux intent

        Args:
            url: The URL to open

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Use am (Activity Manager) to open URL directly
            result = subprocess.run([
                'am', 'start',
                '--user', '0',
                '-a', 'android.intent.action.VIEW',
                '-d', url
            ], capture_output=True, text=True)

            if result.returncode == 0:
                logger.info(f"Successfully opened link: {url}")
                return True
            else:
                logger.error(f"Failed to open link: {url}, error: {result.stderr}")
                return False
        except Exception as e:
            logger.error(f"Exception while opening link: {e}")
            return False

class TermuxClicker:
    """Handles clicking functionality using uiautomator2"""

    def __init__(self):
        self.device = None
        self._init_uiautomator()

    def _init_uiautomator(self):
        """Initialize uiautomator2 if available"""
        try:
            import uiautomator2 as u2
            self.device = u2.connect()  # Connect to local device
            logger.info("Successfully connected to local device via uiautomator2")
        except ImportError:
            logger.warning("uiautomator2 not installed. Click functionality will be limited.")
            self.device = None
        except Exception as e:
            logger.error(f"Failed to initialize uiautomator2: {e}")
            self.device = None

    def find_and_click_element(self, resource_id: Optional[str] = None,
                              text: Optional[str] = None,
                              content_desc: Optional[str] = None,
                              timeout: float = 10.0) -> bool:
        """Find and click an element on the screen

        Args:
            resource_id: Resource ID of the element
            text: Text content of the element
            content_desc: Content description of the element
            timeout: Maximum time to wait for element

        Returns:
            bool: True if element found and clicked, False otherwise
        """
        if not self.device:
            logger.warning("uiautomator2 not available, cannot click elements")
            return False

        try:
            # Build selector based on provided parameters
            selector = {}
            if resource_id:
                selector['resourceId'] = resource_id
            if text:
                selector['text'] = text
            if content_desc:
                selector['contentDescription'] = content_desc

            if not selector:
                logger.warning("No selector criteria provided")
                return False

            # Wait for element and click
            element = self.device(**selector)
            if element.exists:
                element.click()
                logger.info(f"Successfully clicked element with {selector}")
                return True
            else:
                logger.warning(f"Element not found: {selector}")
                return False

        except Exception as e:
            logger.error(f"Error finding/clicking element: {e}")
            return False

    def wait_and_click(self, resource_id: Optional[str] = None,
                      text: Optional[str] = None,
                      content_desc: Optional[str] = None,
                      timeout: float = 10.0,
                      check_interval: float = 1.0) -> bool:
        """Wait for an element to appear and then click it

        Args:
            resource_id: Resource ID of the element
            text: Text content of the element
            content_desc: Content description of the element
            timeout: Maximum time to wait for element
            check_interval: Interval between checks

        Returns:
            bool: True if element found and clicked, False otherwise
        """
        if not self.device:
            logger.warning("uiautomator2 not available, cannot click elements")
            return False

        start_time = time.time()
        while time.time() - start_time < timeout:
            if self.find_and_click_element(resource_id, text, content_desc):
                return True
            time.sleep(check_interval)

        logger.warning(f"Element not found within {timeout} seconds")
        return False

def demo_link_opening():
    """Demo function to show link opening functionality"""
    opener = TermuxLinkOpener()

    # Example usage
    test_url = "https://www.tiktok.com"
    success = opener.open_link_in_browser(test_url)

    if success:
        print("✓ Link opened successfully")
    else:
        print("✗ Failed to open link")

def demo_clicking():
    """Demo function to show clicking functionality"""
    clicker = TermuxClicker()

    # Example: Try to click a follow button
    # You would need to know the actual resource ID or text
    success = clicker.wait_and_click(
        text="Follow",
        timeout=5.0
    )

    if success:
        print("✓ Clicked successfully")
    else:
        print("✗ Failed to click element")

if __name__ == "__main__":
    print("Termux Automation Demo")
    print("1. Link Opening Demo")
    demo_link_opening()
    print("2. Clicking Demo")
    demo_clicking()