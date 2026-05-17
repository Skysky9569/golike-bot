"""
Simple demo script for Termux automation
"""

import time
from termux_automation import TermuxLinkOpener, TermuxClicker

def main():
    print("Termux Automation Demo")

    # Demo link opening
    print("\\n1. Testing link opening...")
    opener = TermuxLinkOpener()

    # Test opening a sample link
    test_url = "https://www.tiktok.com"
    print(f"Opening {test_url}")
    success = opener.open_link_in_browser(test_url)

    if success:
        print("✓ Link opened successfully")
    else:
        print("✗ Failed to open link")

    # Demo clicking functionality
    print("\\n2. Testing clicking functionality...")
    clicker = TermuxClicker()

    # Try to find and click a follow button
    print("Looking for Follow button...")
    success = clicker.wait_and_click(
        text="Follow",
        timeout=5.0
    )

    if success:
        print("✓ Clicked 'Follow' button successfully")
    else:
        print("✗ Could not find or click 'Follow' button")

if __name__ == "__main__":
    main()