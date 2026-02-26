import pytest
from playwright.sync_api import Page, expect
from django.contrib.auth import get_user_model
from apps.users.factories import UserFactory, InvestorProfileFactory, BankAccountFactory
from apps.products.factories import SchemeFactory
from apps.reconciliation.models import Holding
from apps.investments.models import Order, Mandate, Folio
from unittest.mock import patch
from decimal import Decimal
import time
import os
import re

os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"

User = get_user_model()

@pytest.fixture(scope="function")
def authenticated_investor_page(page: Page, live_server, db):
    page.on("console", lambda msg: print(f"CONSOLE: {msg.text}"))
    page.on("pageerror", lambda exc: print(f"PAGE ERROR: {exc}"))

    user = UserFactory(user_type='INVESTOR', password='password')
    user.set_password('password')
    user.save()
    investor_profile = InvestorProfileFactory(user=user)

    # Login
    page.goto(f"{live_server.url}/login", wait_until="domcontentloaded")
    page.fill('input#email', user.username)
    page.fill('input#password', 'password')
    page.click('button:has-text("Sign In")')

    # Wait for dashboard
    expect(page).to_have_url(re.compile(r".*/dashboard/investor/?"), timeout=20000)

    return page, investor_profile

@pytest.mark.django_db(transaction=True)
def test_redemption_flow(authenticated_investor_page, live_server):
    page, investor = authenticated_investor_page

    # Setup
    scheme = SchemeFactory(name="Test Growth Fund", scheme_code="TGF001")
    Folio.objects.create(investor=investor, amc=scheme.amc, folio_number="FOLIO123")
    holding = Holding.objects.create(
        investor=investor,
        scheme=scheme,
        folio_number="FOLIO123",
        units=Decimal("100.000"),
        average_cost=Decimal("10.00"),
        current_value=Decimal("1200.00"),
        current_nav=Decimal("12.00")
    )

    # Mock BSE Client
    with patch('apps.integration.bse_client.BSEStarMFClient') as MockClient:
        instance = MockClient.return_value
        instance.place_order.return_value = {'status': 'success', 'bse_order_id': '123456', 'remarks': 'Success'}

        # Navigate
        page.goto(f"{live_server.url}/dashboard/portfolio/holdings")

        # Click Redeem
        page.click(f"tr:has-text('{scheme.name}') button:has-text('Redeem')")

        # Verify Page
        expect(page).to_have_url(f"{live_server.url}/dashboard/investments/redeem/{holding.id}")
        expect(page.locator("text=Redeem Investment")).to_be_visible()

        # Verify Pre-filled (check values in form state via UI)
        # Tab should be 'Redeem'
        expect(page.locator('button[role="tab"][data-state="active"]:has-text("Redeem")')).to_be_visible()

        # Fill Amount
        page.fill('input[name="amount"]', "100")

        # Submit
        page.click('button:has-text("Redeem Funds")')

        # Verify Success
        expect(page.locator("text=Order Placed Successfully")).to_be_visible()

        # Verify DB
        assert Order.objects.filter(investor=investor, transaction_type='R', amount=100).exists()

@pytest.mark.django_db(transaction=True)
def test_mandate_creation_flow(authenticated_investor_page, live_server):
    page, investor = authenticated_investor_page

    # Setup
    bank = BankAccountFactory(investor=investor, bank_name="HDFC Bank", account_number="1234567890")

    # Mock BSE Client
    with patch('apps.integration.bse_client.BSEStarMFClient') as MockClient:
        instance = MockClient.return_value
        instance.register_mandate.return_value = {'status': 'success', 'mandate_id': 'MANDATE123'}
        instance.get_mandate_auth_url.return_value = 'http://example.com/auth'

        # Navigate
        page.goto(f"{live_server.url}/dashboard/investments/mandates")
        page.click('button:has-text("Create Mandate")')

        # Fill Form
        # Wait for bank dropdown to be populated
        page.wait_for_timeout(1000)

        # Select Bank (using specific role/class selectors might be needed for shadcn select)
        # Open dropdown
        page.click('button:has-text("Select Bank Account")')
        # Select option
        page.click('div[role="option"]:has-text("1234567890")')

        page.fill('input[name="amount_limit"]', "50000")
        page.fill('input[name="start_date"]', "2023-01-01")

        # Submit
        page.click('button:has-text("Create & Authorize")')

        # Check for success toast or redirect
        # The frontend redirects to the auth URL returned by backend
        expect(page).to_have_url("http://example.com/auth", timeout=10000)

        # Verify DB
        assert Mandate.objects.filter(investor=investor, amount_limit=50000).exists()
