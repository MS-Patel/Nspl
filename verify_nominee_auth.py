from playwright.sync_api import sync_playwright, expect

def run(playwright):
    browser = playwright.chromium.launch(headless=True)
    context = browser.new_context()
    page = context.new_page()

    # 1. Login as Distributor
    page.goto("http://127.0.0.1:8000/login/")
    page.fill("input[name='username']", "distributor1")
    page.fill("input[name='password']", "password123")
    page.click("button[type='submit']")

    # 2. Navigate to Investor Detail
    page.goto("http://127.0.0.1:8000/users/investor/1/")

    # Wait for the card to be visible
    # The profile card is the first one in the grid-cols-12
    # We can locate it by the text inside "Investor Details" header or the PAN label
    page.wait_for_selector("text=PAN")

    # 3. Assertions
    expect(page.get_by_text("Nominee Auth", exact=True)).to_be_visible()

    pending_badge = page.get_by_text("Pending", exact=True)
    expect(pending_badge).to_be_visible()

    trigger_btn = page.get_by_role("button", name="Trigger Nominee Auth / Check Status")
    expect(trigger_btn).to_be_visible()

    expect(page.get_by_text("BSE Remarks:")).to_be_visible()
    expect(page.get_by_text("NOMINEE AUTHENTICATION PENDING", exact=False)).to_be_visible()

    # 4. Screenshot the specific card area if possible, or viewport
    # The card has padding p-4 sm:p-5
    # Let's target the card containing "Nominee Auth"
    card = page.locator(".card").filter(has_text="Nominee Auth").first
    card.screenshot(path="/home/jules/verification/nominee_auth_card.png")

    # Also full page for context
    page.screenshot(path="/home/jules/verification/nominee_auth_full.png", full_page=True)

    browser.close()

if __name__ == "__main__":
    with sync_playwright() as playwright:
        run(playwright)
