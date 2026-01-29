from playwright.sync_api import sync_playwright, expect

def run(playwright):
    browser = playwright.chromium.launch(headless=True)
    context = browser.new_context()
    page = context.new_page()

    page.on("console", lambda msg: print(f"CONSOLE: {msg.text}"))
    page.on("pageerror", lambda err: print(f"PAGE ERROR: {err}"))

    try:
        # 1. Login
        page.goto("http://127.0.0.1:8000/login/")
        page.wait_for_selector(".app-preloader", state="hidden") # Wait for preloader
        page.fill("input[name='username']", "frontend_user")
        page.fill("input[name='password']", "password")
        page.click("button[type='submit']")

        # Wait for dashboard or redirect
        page.wait_for_load_state('domcontentloaded')

        # 2. Go to Order Page
        page.goto("http://127.0.0.1:8000/order/create/")
        page.wait_for_load_state('domcontentloaded')

        # DEBUG: Save content
        with open("verification/page_source.html", "w") as f:
            f.write(page.content())

        # 2.5 Select Source Scheme (Prerequisite for Switch Target)
        page.locator("#id_scheme + .ts-wrapper .ts-control").click()
        page.wait_for_selector("#id_scheme + .ts-wrapper .ts-dropdown .option")
        page.locator("#id_scheme + .ts-wrapper .ts-dropdown .option").first.click()

        # 3. Select Switch
        switch_label = page.locator(".tabs-list label").filter(has_text="Switch")
        switch_label.click()

        # Wait for animation/display change
        page.wait_for_timeout(2000)

        # Verify "Target Scheme" dropdown appeared
        target_scheme_label = page.locator("text=Target Scheme (Switch In)")
        expect(target_scheme_label).to_be_visible()

        # 4. Toggle Switch Mode to Units
        page.locator("label").filter(has_text="By Units").click()

        # Verify Units input is visible and Amount is hidden
        units_input = page.locator("input[name='units']")
        expect(units_input).to_be_visible()

        amount_input = page.locator("#amount-container")
        expect(amount_input).not_to_be_visible()

        # 5. Fill and Submit
        page.fill("input[name='units']", "10")

        # Select Target Scheme (TomSelect interaction)
        # Click the control to open dropdown
        page.locator("#id_target_scheme + .ts-wrapper .ts-control").click()
        # Wait for dropdown
        page.wait_for_selector("#id_target_scheme + .ts-wrapper .ts-dropdown .option")
        # Click first option
        page.locator("#id_target_scheme + .ts-wrapper .ts-dropdown .option").first.click()

        # Submit
        page.click("button[type='submit']")

        # 6. Verify Result
        # We expect a redirect or a message.
        # Since BSE call will likely fail (invalid creds/network/params in test env), we expect an error message or success if mocked.
        # But we just want to ensure we don't get "Please correct errors" form validation error for fields we filled.

        page.wait_for_load_state('domcontentloaded')

        # Check for alert (Success or Error)
        # If form validation failed, we stay on page and see errors.
        if page.locator(".alert.bg-error/10").is_visible():
             print("Form Validation Errors detected!")
             print(page.locator(".alert.bg-error/10").inner_text())
        else:
             print("Form Submitted (Redirected or Processed)")
             # Check for toast/swal
             # We can check URL
             print(f"Current URL: {page.url}")

        # Take Screenshot
        page.screenshot(path="verification/frontend_switch.png")
        print("Screenshot saved to verification/frontend_switch.png")

    except Exception as e:
        print(f"Error: {e}")
        page.screenshot(path="verification/failure.png")
        print("Failure screenshot saved to verification/failure.png")
        # raise e # Don't raise so we can check artifacts
    finally:
        browser.close()

with sync_playwright() as playwright:
    run(playwright)
