import time
from playwright.sync_api import sync_playwright

def run_cuj(page):
    # We first need to login as an admin
    page.goto("http://localhost:8000/login/")
    page.wait_for_timeout(2000)
    page.fill('input[placeholder="Username or Email"]', 'admin') # Try id instead of name if it's different
    page.fill('input[type="password"]', 'admin')
    page.click('button:has-text("Sign In")')
    page.wait_for_timeout(2000)

    # Go to investor onboarding page
    page.goto("http://localhost:8000/users/investor/onboard/")
    page.wait_for_timeout(2000)

    # We need to take a screenshot and a video interacting with the TomSelect dropdown
    page.click('.ts-control') # Click the tomselect control
    page.wait_for_timeout(1000)

    # Take screenshot at the key moment
    page.screenshot(path="/home/jules/verification/screenshots/verification.png")
    page.wait_for_timeout(1000)  # Hold final state for the video

if __name__ == "__main__":
    import os
    os.makedirs("/home/jules/verification/screenshots", exist_ok=True)
    os.makedirs("/home/jules/verification/videos", exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            record_video_dir="/home/jules/verification/videos"
        )
        page = context.new_page()
        try:
            run_cuj(page)
        except Exception as e:
            print(f"Error: {e}")
            page.screenshot(path="/home/jules/verification/screenshots/error.png")
        finally:
            context.close()  # MUST close context to save the video
            browser.close()