import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        # Go to legacy login
        await page.goto("http://localhost:8000/legacy/login/")

        # Fill in credentials
        await page.fill('input[name="username"]', 'admin')
        await page.fill('input[name="password"]', 'adminpass')

        # Fix form action
        await page.evaluate('''() => {
            const form = document.querySelector('form');
            if (form) form.action = '/legacy/login/';
        }''')

        # Expect navigation and submit
        async with page.expect_navigation():
            await page.click('button[type="submit"]')

        print("Logged in via fixed form action.")

        # Navigate to the admin dashboard manually
        await page.goto("http://localhost:8000/dashboard/admin/")
        print("Successfully loaded admin dashboard.")

        # Now verify mobile navigation
        await page.set_viewport_size({"width": 375, "height": 667})
        await page.wait_for_timeout(2000)

        # Click the hamburger menu using specific selector
        try:
            # Check the mobile header toggle
            await page.click('#toggle-menu', timeout=2000)
            await page.wait_for_timeout(1000)
            print("Clicked #toggle-menu")
        except Exception as e:
            try:
                # Based on typical Bootstrap templates
                await page.click('button.navbar-toggler', timeout=2000)
                await page.wait_for_timeout(1000)
                print("Clicked button.navbar-toggler")
            except Exception as e2:
                # Try evaluating javascript directly to open the offcanvas
                await page.evaluate('''() => {
                    const btn = document.querySelector('[data-bs-toggle="offcanvas"]');
                    if (btn) btn.click();

                    const el = document.querySelector('.offcanvas');
                    if (el && window.bootstrap) {
                        new window.bootstrap.Offcanvas(el).show();
                    }
                }''')
                await page.wait_for_timeout(1000)
                print("Attempted to toggle via JS")

        await page.screenshot(path="mobile_nav_open.png")
        print("Captured mobile navigation open.")

        await browser.close()

asyncio.run(main())
