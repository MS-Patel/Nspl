# Roadmap Verification Report

This report compares the current codebase against `ROADMAP2.md` ("Production-Ready Mutual Fund Portal").

## 1. Executive Summary
The core infrastructure, including User Management, BSE Integration, Order Execution, and Reconciliation, is **largely implemented**. The system is capable of onboarding investors (with some manual steps), executing orders (Lumpsum/SIP/Switch/Redeem), and reconciling daily RTA files to calculate AUM and Commissions.

However, several "Production Hardening" features (Audit fields, detailed tracking status) and specific functional modules (Risk Profiling, Payment Gateway, eSign) are missing.

## 2. Phase-by-Phase Verification

### Phase 1: Enterprise Foundation & Identity Management
*   **Implemented:**
    *   `User` model with `user_type`.
    *   Profile models: `RMProfile`, `DistributorProfile`, `InvestorProfile` with hierarchy relationships.
    *   `AuditLog` model exists.
    *   Role-based redirects and authentication views.
*   **Missing / Needs Attention:**
    *   **User Fields:** `created_by` is missing. Standard `audit_fields` (created_at/updated_at) are present on most models but not via a shared Mixin as implied for "Production Grade".
    *   **Profile Fields:**
        *   `RMProfile`: Missing `amc_codes`, `sebi_regn_no`.
        *   `DistributorProfile`: Missing `hierarchy_path` (optimization field).
        *   `InvestorProfile`: Missing `risk_profile` (Confirmed Gap), `fatca_status` (explicit status field missing, though data fields exist).

### Phase 2: Master Data & Compliance
*   **Implemented:**
    *   Models: `AMC`, `SchemeCategory`, `Scheme`, `NAVHistory`.
    *   Fields: `riskometer`, `exit_load` present on Scheme.
    *   Sync: Management commands (`import_schemes`, `update_navs`) are implemented.
*   **Missing:**
    *   `SchemeLock` model (for regulatory restrictions) is missing.

### Phase 3: BSE StarMF Enterprise Integration
*   **Implemented:**
    *   `BSEStarMFClient` class with SOAP integration.
    *   **WSDL Verification:** Confirmed that `MFOrder.wsdl` and `StarMFWebService.wsdl` in `docs/wsdl/` match the methods called in `bse_client.py` (e.g., `orderEntryParam`, `MFAPI`, `MandateDetails`).
    *   **Resilience:** Exponential backoff retry logic (`_retry_call`) is implemented.
    *   **UCC:** Client registration logic (`register_client`) exists.
*   **Missing:**
    *   `IntegrationLog` model (referenced in roadmap) is not in `apps/integration/models.py`.

### Phase 4: Investor Onboarding
*   **Implemented:**
    *   Multi-step Wizard logic in Views.
    *   `CVLClient` for KRA integration.
    *   `Document` model exists.
*   **Missing:**
    *   **Risk Profiling:** Logic and Questionnaire missing (Known Gap).
    *   **eSign:** Leegality/Digio integration missing (Known Gap).
    *   **Document Verification:** `verified_status` and `expiry_date` fields are missing on the `Document` model.

### Phase 5: Mandate & Payment Infrastructure
*   **Implemented:**
    *   `Mandate` model with `amount_limit`, `mandate_id`, `status`.
    *   BSE Mandate Registration API wired up (`MandateCreateView`).
*   **Missing:**
    *   **Payment Gateway:** Razorpay/BillDesk integration is missing (Known Gap).

### Phase 6: Investment Execution Engine
*   **Implemented:**
    *   `Order` model supporting Purchase, Redemption, Switch, SIP.
    *   `SIP` model with installment tracking.
    *   Full flow: View -> Form -> Model -> BSE API -> Status Update.
    *   Logic for "New Folio" vs "Existing Folio".

### Phase 7: Holdings & Portfolio Engine
*   **Implemented:**
    *   **Parsers:** Robust parsers for CAMS (`WBR9`, `WBR2`), Karvy (`MFD`, `XLS`), and Franklin.
    *   **Reconciliation:** Logic to match RTA transactions with local orders and create/update `Transaction` records.
    *   **Dashboard:** `FolioDetailView` calculates XIRR, Absolute Returns, and Days Change dynamically.

### Phase 8: Compliance & Reporting
*   **Implemented:**
    *   **Commission Engine:** `apps/payouts/utils.py` implements AUM-based tier calculation and payout generation (`calculate_payouts`).
    *   **Reports:** Standard reports (Investor, Transaction, Allotment) are implemented.

### Phase 9: Production Test Suite
*   **Assessment:** Extensive test files exist across all apps (`users`, `products`, `integration`, `investments`, `payouts`, `reconciliation`).
*   **Coverage:** While exact percentage is not calculated, the breadth covers critical paths (BSE Auth, Order Params, Parsers, Payout Logic).

## 3. Conclusion
The codebase is in a **Late Beta / Pre-Production** state. The "Happy Path" for a Broker/Distributor to onboard an investor (physically/offline payment), place orders, and track commissions is complete.

**Immediate Action Items to reach "Production Ready":**
1.  Add missing fields (`created_by`, `SchemeLock`).
2.  Implement `IntegrationLog` for better debugging.
3.  Add `verified_status` to Documents.
