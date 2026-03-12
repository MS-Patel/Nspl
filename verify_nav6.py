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

        # Navigate to the admin dashboard manually
        await page.goto("http://localhost:8000/dashboard/admin/")

        # Now verify mobile navigation
        await page.set_viewport_size({"width": 375, "height": 667})
        await page.wait_for_timeout(2000)

        # Just find if the elements are hidden in the DOM for mobile
        html = await page.content()
        investor_exists = "Investor" in html
        admin_exists = "Administration" in html

        with open("mobile_dom.html", "w") as f:
            f.write(html)

        print(f"Investor link in DOM: {investor_exists}")
        print(f"Administration link in DOM: {admin_exists}")

        await browser.close()

asyncio.run(main())
