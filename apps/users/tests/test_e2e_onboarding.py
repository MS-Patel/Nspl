import pytest
from playwright.sync_api import Page, expect
from django.contrib.auth import get_user_model
import time

User = get_user_model()

@pytest.fixture(scope="function")
def authenticated_page(page: Page, live_server, db):
    # Setup Admin
    admin = User.objects.create_superuser(username='admin', email='admin@example.com', password='password', user_type='ADMIN')

    # Go to Login
    page.goto(f"{live_server.url}/login")

    # Fill Login Form
    # Using specific selectors based on Login.tsx
    page.fill('input#email', 'admin')
    page.fill('input#password', 'password')
    page.click('button:has-text("Sign In")')

    # Wait for dashboard redirect
    # Need to wait for URL change or element
    try:
        page.wait_for_url(f"{live_server.url}/dashboard/admin", timeout=10000)
    except:
        # Fallback check
        expect(page).to_have_url(f"{live_server.url}/dashboard/admin")

    return page

@pytest.mark.django_db(transaction=True)
def test_investor_onboarding_flow(authenticated_page: Page, live_server):
    page = authenticated_page

    # Navigate to Onboarding Wizard
    # Ideally via menu, but direct URL is safer for test stability
    page.goto(f"{live_server.url}/dashboard/investors/new")

    # Step 1: Personal Details
    expect(page.locator("text=Personal Details")).to_be_visible()

    page.fill('input[name="firstname"]', "John")
    page.fill('input[name="lastname"]', "Doe")
    page.fill('input[name="email"]', "john.doe@test.com")
    page.fill('input[name="mobile"]', "9876543210")
    page.fill('input[name="pan"]', "ABCDE1234F")

    # Submit Step 1
    page.click('button:has-text("Create & Next")')

    # Verify Step 2: KYC
    expect(page.locator("text=Perform KYC Check")).to_be_visible(timeout=5000)

    # Skip KYC check (or simulate)
    page.click('button:has-text("Skip / Next")')

    # Verify Step 3: Bank Details
    expect(page.locator("text=Account Number")).to_be_visible()

    page.fill('input[name="account_number"]', "123456789012")
    page.fill('input[name="ifsc_code"]', "HDFC0001234")
    page.fill('input[name="bank_name"]', "HDFC Bank")

    # Submit Step 3
    page.click('button:has-text("Save & Next")')

    # Verify Step 4: FATCA
    expect(page.locator("text=Place of Birth")).to_be_visible()

    page.fill('input[name="place_of_birth"]', "Mumbai")
    page.fill('input[name="country_of_birth"]', "India")

    # Submit Step 4
    page.click('button:has-text("Save & Next")')

    # Verify Step 5: Nominee
    expect(page.locator("text=Nominee Name")).to_be_visible()

    page.fill('input[name="name"]', "Jane Doe")
    page.fill('input[name="relationship"]', "Spouse")
    # Date/Percentage have defaults or are optional/prefilled in our implementation?
    # Percentage default is 100.

    # Submit Step 5
    page.click('button:has-text("Save & Next")')

    # Verify Step 6: Documents
    expect(page.locator("text=Upload Documents")).to_be_visible()

    # Complete
    page.click('button:has-text("Complete & Go to Dashboard")')

    # Should redirect to investor list
    expect(page).to_have_url(f"{live_server.url}/dashboard/investors")
