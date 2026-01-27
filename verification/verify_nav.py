from playwright.sync_api import sync_playwright, expect

def test_navigation_links(page):
    # 1. Login
    print("Navigating to login...")
    page.goto("http://127.0.0.1:8000/login/")
    print(f"Page title: {page.title()}")

    print("Filling credentials...")
    page.fill("input[name='username']", "admin")
    page.fill("input[name='password']", "admin")
    page.click("button[type='submit']")

    # Wait for dashboard
    print("Waiting for dashboard...")
    page.wait_for_url("http://127.0.0.1:8000/dashboard/admin/")

    # 2. Check Payouts Dropdown
    print("Checking Payouts...")
    payouts_btn = page.locator("#payouts-menu-dropdown button")
    expect(payouts_btn).to_be_visible()
    payouts_btn.click()
    page.wait_for_timeout(1000) # Wait for animation
    page.screenshot(path="/app/verification/payouts_open.png")

    # Check links inside
    expect(page.get_by_role("link", name="Payout Reports")).to_be_visible()
    expect(page.get_by_role("link", name="Generate Payouts")).to_be_visible()

    # Close dropdown (click outside or escape)
    page.keyboard.press("Escape")
    page.wait_for_timeout(500)

    # 3. Check Investments Dropdown
    print("Checking Investments...")
    invest_btn = page.locator("#invest-menu-dropdown button")
    expect(invest_btn).to_be_visible()
    invest_btn.click()
    page.wait_for_timeout(1000)
    page.screenshot(path="/app/verification/investments_open.png")

    # Check Holdings link
    holdings_link = page.get_by_role("link", name="Portfolio Holdings")
    expect(holdings_link).to_be_visible()

    # 4. Navigate to Holdings
    print("Navigating to Holdings...")
    holdings_link.click()
    page.wait_for_url("http://127.0.0.1:8000/holdings/")

    # 5. Take Screenshot
    print("Taking final screenshot...")
    page.screenshot(path="/app/verification/navigation_verification.png")

if __name__ == "__main__":
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        try:
            test_navigation_links(page)
            print("Verification script finished successfully.")
        except Exception as e:
            print(f"Verification script failed: {e}")
            page.screenshot(path="/app/verification/failure.png")
        finally:
            browser.close()
