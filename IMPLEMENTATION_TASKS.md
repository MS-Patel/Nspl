# Implementation Status & Remaining Tasks

This document serves as a detailed task list for completing the "Production-Ready Mutual Fund Portal" as defined in `ROADMAP2.md`. It highlights the gap between the current codebase and the requirements.

**Current Status Overview:** Core models and basic BSE integration are present, but "Enterprise" features (Resilience, Security, Advanced Workflows, Background Processing) are largely missing.

---

## Phase 1: Enterprise Foundation & Identity Management
**Status: Partial**

### ✅ Implemented
- Basic `User` model with types (Admin, RM, Distributor, Investor).
- `RMProfile`, `DistributorProfile`, `InvestorProfile` with basic hierarchy relationships.
- `LoginRequiredMixin` and basic Dashboard Views.
- Role-based templates (`admin.html`, `rm.html`, etc.).

### 📝 To Be Implemented (Future Tasks)
1.  **Enhance User Models:**
    -   Add `status` (Active/Inactive/Suspended), `created_by`, and `audit_fields` to `User`.
    -   Add `amc_codes`, `sebi_regn_no` to `RMProfile`.
    -   Add `euin`, `hierarchy_path` to `DistributorProfile`.
    -   Add `risk_profile` to `InvestorProfile`.
2.  **Audit Trail:**
    -   Create `AuditLog` model (user, action, timestamp, ip_address, details).
    -   Implement middleware or signals to log sensitive actions.
3.  **Authentication Hardening:**
    -   Implement MFA/OTP for Admin/RM logins.
    -   Implement Login Rate Limiting (prevent brute force).
4.  **Soft Delete:**
    -   Add `is_deleted` field or use a library (e.g., `django-safedelete`) for critical models.

---

## Phase 2: Master Data & Compliance Foundation
**Status: Partial**

### ✅ Implemented
- `AMC`, `SchemeCategory`, `Scheme`, `NAVHistory` models.
- Basic `fetch_navs` management command.

### 📝 To Be Implemented (Future Tasks)
1.  **Missing Models:**
    -   Create `SchemeRiskGrade` model.
    -   Create `SchemeLock` model (for regulatory restrictions).
    -   Add `riskometer_rating`, `exit_load_structure` to `Scheme`.
2.  **Master Data Sync:**
    -   Implement robust BSE StarMF Master Data Sync (Schemes + NAVs).
    -   Add data validation layer (e.g., warn if NAV deviates > 10%).
    -   Implement CSV upload fallback UI for manual updates.

---

## Phase 3: BSE StarMF Enterprise Integration
**Status: Partial**

### ✅ Implemented
- `BSEStarMFClient` using `zeep`.
- Basic methods: `place_order`, `register_sip`, `register_mandate`, `register_client`.
- Token caching (`_get_auth_details`).

### 📝 To Be Implemented (Future Tasks)
1.  **Resilience (Critical):**
    -   Implement **Circuit Breaker** pattern (stop calling API if N failures occur).
    -   Implement **Exponential Backoff** for retries.
2.  **Logging:**
    -   Create `IntegrationLog` database model to persist API requests/responses (currently only file logging).
3.  **UCC Pipeline:**
    -   Implement explicit idempotency checks for `CreateClient`.

---

## Phase 4: Enterprise Investor Onboarding
**Status: Partial**

### ✅ Implemented
- `InvestorCreateView` and `InvestorUpdateView` (Single page forms).
- Basic BSE Client Registration (`PushToBSEView`).
- `Document` model (basic).

### 📝 To Be Implemented (Future Tasks)
1.  **Multi-Step Wizard:**
    -   Refactor Onboarding into a multi-step flow (Personal -> KYC -> Bank -> FATCA -> Nominee -> Risk -> Consent).
    -   Use SessionWizardView or frontend (React/Vue/Alpine) state management.
2.  **KYC & Document Verification:**
    -   Replace mocked `kyc_status = True` with actual KRA integration (CAMS/KARVY/NDML).
    -   Add `verified_status` and `expiry_date` to `Document` model.
    -   Implement Document Encryption (AES-256) at rest.
    -   Implement OCR extraction for PAN/Aadhaar.
3.  **Risk Profiling:**
    -   Implement the 14-questionnaire risk profiling logic.

---

## Phase 5: Mandate & Payment Infrastructure
**Status: Partial**

### ✅ Implemented
- `Mandate` model.
- `MandateCreateView` and `mandate_authorize` redirect.
- Basic BSE Mandate Registration logic.

### 📝 To Be Implemented (Future Tasks)
1.  **Payment Gateway:**
    -   Integrate Razorpay or BillDesk for Netbanking/UPI payments.
    -   Implement Payment Reconciliation logic (Webhook handling).
2.  **Mandate Refinement:**
    -   Align `Mandate` model strictly with BSE UMRN requirements.
    -   Implement logic to track Mandate Utilization (Daily/Monthly limits).

---

## Phase 6: Investment Execution Engine
**Status: Partial**

### ✅ Implemented
- `Order` and `SIP` models.
- `order_create` view (Purchase/SIP/Redeem/Switch).
- Basic `BSEStarMFClient` order placement.

### 📝 To Be Implemented (Future Tasks)
1.  **Risk Controls:**
    -   Implement **Pre-validation** checks (Exposure limits, Concentration checks) before sending to BSE.
2.  **Large Order Handling:**
    -   Implement automatic order splitting for amounts > ₹2 Lakhs (or AMC specific limits).
3.  **SIP Lifecycle:**
    -   Create `SIPInstallment` model to track individual SIP hits.
    -   Implement logic for Pause/Stop/Top-up SIP.
4.  **Allotment Logic:**
    -   Implement logic to process `AllotmentStatement` and update `Order` status to `ALLOTTED`.

---

## Phase 7: Holdings & Portfolio Engine
**Status: Partial**

### ✅ Implemented
- `CAMSParser`, `KarvyParser`, `FranklinParser`.
- `Transaction` and `Holding` models.
- Basic `calculate_portfolio_valuation` utility.

### 📝 To Be Implemented (Future Tasks)
1.  **Automation (Celery):**
    -   Set up **Celery** and **Redis**.
    -   Create background tasks for RTA file processing (don't block web request).
2.  **Advanced Analytics:**
    -   Implement **XIRR** (Extended Internal Rate of Return) calculation algorithm.
    -   Calculate Alpha, Beta, Sharpe Ratio.
    -   Build Historical Performance Charts (NAV vs Time).

---

## Phase 8: Enterprise Compliance & Reporting
**Status: Not Started**

### 📝 To Be Implemented (Future Tasks)
1.  **Commission Engine:**
    -   Implement `Payout` calculation with GST logic (18%).
    -   Implement "Waterfall" payout logic for Distributor Hierarchies (Master Dist -> Sub Dist).
2.  **Reporting:**
    -   Generate AMFI Transfer Reports.
    -   Generate SEBI Transaction Summary Reports.
    -   Generate FATCA/CRS Reports.

---

## Phase 9: Production Test Suite
**Status: Ongoing**

### 📝 To Be Implemented (Future Tasks)
-   Achieve >95% Test Coverage.
-   Add specific tests for:
    -   Concurrency (Race conditions in Order placement).
    -   RTA File Parsing edge cases (Malformed CSVs).
    -   BSE API Failure Scenarios (Mocked).
