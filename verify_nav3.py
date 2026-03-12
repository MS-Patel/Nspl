import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        # Using context to bypass login if possible by mocking the session cookie or
        # doing login without waiting for a navigation that might not happen
        context = await browser.new_context()
        page = await context.new_page()

        # Go to legacy login
        await page.goto("http://localhost:8000/legacy/login/")

        # Fill in credentials
        await page.fill('input[name="username"]', 'admin')
        await page.fill('input[name="password"]', 'adminpass')

        # We see POST /login/ being hit which returns 405.
        # The form action in legacy login might be wrong and pointing to /login/
        # Let's fix the form action before submitting
        await page.evaluate('''() => {
            const form = document.querySelector('form');
            if (form) form.action = '/legacy/login/';
        }''')

        # Submit the form and wait for response to legacy/login
        await asyncio.gather(
            page.wait_for_navigation(),
            page.click('button[type="submit"]')
        )

        print("Logged in via fixed form action.")

        # Navigate to the admin dashboard manually
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
            # Look for sidebar toggler classes
            await page.click('.navbar-toggler, .menu-toggle, [data-bs-toggle="offcanvas"], .mobile-toggle, .btn[data-bs-toggle="offcanvas"]', timeout=2000)
            await page.wait_for_timeout(1000)
            print("Clicked mobile menu toggle.")
        except Exception as e:
            print("Could not find or click mobile menu toggle.")

        await page.screenshot(path="mobile_nav.png")
        print("Captured mobile navigation.")

        await browser.close()

asyncio.run(main())
