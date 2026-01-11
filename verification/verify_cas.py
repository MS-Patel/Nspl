from playwright.sync_api import sync_playwright, expect
import time
import os

def run(playwright):
    browser = playwright.chromium.launch(headless=True)
    context = browser.new_context()
    page = context.new_page()

    # Login as Admin (since we need to test access first)
    # We assume 'admin_verifier' / 'password123' exists (created earlier).

    page.goto("http://127.0.0.1:8004/cas/list/")

    # Check if we are redirected to login
    if "login" in page.url:
        print("Redirected to login, attempting to login...")
        page.fill("input[name='username']", "admin_verifier")
        page.fill("input[name='password']", "password123")
        page.click("button[type='submit']")
        page.wait_for_load_state('networkidle')

    # Navigate to CAS List
    page.goto("http://127.0.0.1:8004/cas/list/")
    try:
        expect(page.get_by_text("Uploaded CAS Files")).to_be_visible(timeout=10000)
    except Exception as e:
        print(f"Failed to find text: {e}")
        page.screenshot(path="verification/failed_cas_list.png")
        raise e

    # Take screenshot of List View
    page.screenshot(path="verification/cas_list.png")
    print("Captured CAS List screenshot")

    # Click 'Upload New CAS'
    page.click("text=Upload New CAS")
    try:
        expect(page.get_by_text("Upload Consolidated Account Statement")).to_be_visible(timeout=10000)
    except Exception as e:
        print(f"Failed to find upload text: {e}")
        page.screenshot(path="verification/failed_cas_upload.png")
        raise e

    # Take screenshot of Upload Form
    page.screenshot(path="verification/cas_upload_form.png")
    print("Captured CAS Upload Form screenshot")

    browser.close()

with sync_playwright() as playwright:
    run(playwright)
