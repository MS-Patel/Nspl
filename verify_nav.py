import asyncio
from playwright.async_api import async_playwright
import os

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        # Go to legacy login to bypass react
        await page.goto("http://localhost:8000/legacy/login/")

        # Wait for the login form
        await page.wait_for_selector('input[name="username"]')

        # Fill in credentials
        await page.fill('input[name="username"]', 'admin')
        await page.fill('input[name="password"]', 'adminpass')

        # Submit the form
        await page.click('button[type="submit"]')

        # Wait for navigation
        await page.wait_for_url("**/dashboard/**")
        print("Successfully logged in.")

        # Now verify desktop navigation
        await page.set_viewport_size({"width": 1280, "height": 800})
        # Wait for nav items to load
        await page.wait_for_timeout(2000)
        await page.screenshot(path="desktop_nav.png")
        print("Captured desktop navigation.")

        # Now verify mobile navigation
        await page.set_viewport_size({"width": 375, "height": 667})
        # Wait for the layout to adjust
        await page.wait_for_timeout(2000)

        # Mobile menu might be hidden, need to click hamburger if it exists
        # In this template, let's see if we can just take a screenshot
        await page.screenshot(path="mobile_nav.png")
        print("Captured mobile navigation.")

        # Check if we can find the sidebar elements
        html = await page.content()
        with open("rendered_page.html", "w") as f:
            f.write(html)

        await browser.close()

asyncio.run(main())
