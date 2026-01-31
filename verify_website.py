import os
from playwright.sync_api import sync_playwright

def verify(page):
    # Home
    page.goto("http://localhost:8000/")
    page.screenshot(path="verification/home.png")
    print("Home screenshot taken")

    # About
    page.goto("http://localhost:8000/about-us/")
    page.screenshot(path="verification/about.png")
    print("About screenshot taken")

    # Mutual Funds
    page.goto("http://localhost:8000/mutual-funds/")
    page.screenshot(path="verification/mutual_funds.png")
    print("Mutual Funds screenshot taken")

    # Contact
    page.goto("http://localhost:8000/contact-us/")
    page.screenshot(path="verification/contact.png")
    print("Contact screenshot taken")

if __name__ == "__main__":
    if not os.path.exists("verification"):
        os.makedirs("verification")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        try:
            verify(page)
        except Exception as e:
            print(f"Error: {e}")
        finally:
            browser.close()
