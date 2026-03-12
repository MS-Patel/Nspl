import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        # Go to legacy login to bypass react
        await page.goto("http://localhost:8000/legacy/login/")

        # Fill in credentials
        await page.fill('input[name="username"]', 'admin')
        await page.fill('input[name="password"]', 'adminpass')

        # Submit the form and wait for response
        async with page.expect_response(lambda response: response.url.endswith("/legacy/login/") or "dashboard" in response.url) as response_info:
            await page.click('button[type="submit"]')

        response = await response_info.value
        print(f"Response URL: {response.url}, Status: {response.status}")

        # Just in case, try navigating to the admin dashboard manually
        await page.goto("http://localhost:8000/dashboard/admin/")
        print("Successfully loaded admin dashboard.")

        # Now verify desktop navigation
        await page.set_viewport_size({"width": 1280, "height": 800})
        await page.wait_for_timeout(2000)
        await page.screenshot(path="desktop_nav.png")
        print("Captured desktop navigation.")

        # Check if Investor and Administration links exist in the DOM
        content = await page.content()
        investor_exists = "Investor" in content
        admin_exists = "Administration" in content
        print(f"Investor link exists in DOM: {investor_exists}")
        print(f"Administration link exists in DOM: {admin_exists}")

        # Now verify mobile navigation
        await page.set_viewport_size({"width": 375, "height": 667})
        await page.wait_for_timeout(2000)

        # Try to click the mobile menu button if it exists
        try:
            # Common classes for mobile menu toggles
            await page.click('.navbar-toggler, .menu-toggle, [data-bs-toggle="offcanvas"], .mobile-toggle', timeout=2000)
            await page.wait_for_timeout(1000)
            print("Clicked mobile menu toggle.")
        except Exception as e:
            print("Could not find or click mobile menu toggle:", e)

        await page.screenshot(path="mobile_nav.png")
        print("Captured mobile navigation.")

        await browser.close()

asyncio.run(main())
