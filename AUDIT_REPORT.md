# Mutual Fund Portal Audit Report

## Executive Summary
The project has implemented core functionalities for User Management, Product Master Data, and Basic BSE Integration. However, critical "Enterprise" features required for a production-ready system (as defined in `ROADMAP2.md`) are missing or incomplete. Specifically, **Security** (SSL verification disabled), **Unused Audit Logs**, **Circuit Breakers**, **Risk Controls**, **Large Order Handling**, **SIP Lifecycle Management**, and **Commission Logic** are absent or broken.

## Detailed Findings

### Phase 1: Enterprise Foundation & Identity Management
**Status: Partial**
-   **Missing**: `AuditLog` model exists in `apps/users/models.py` but is **completely unused** in the application logic. No centralized logging for sensitive actions (User edits, Order placement) is occurring.
-   **Missing**: Soft Delete mechanism (`is_deleted`) for critical models.
-   **Missing**: MFA/OTP for Admin/RM logins.
-   **Partial**: `User` model lacks `status`, `created_by`, `audit_fields`.

### Phase 2: Master Data & Compliance Foundation
**Status: Partial**
-   **Missing**: `SchemeRiskGrade` and `SchemeLock` models are not implemented.
-   **Missing**: Automated Master Sync with validation. Currently relies on manual CSV upload or simple fetch commands without robust validation.
-   **Missing**: `riskometer_rating`, `exit_load_structure` fields in `Scheme`.

### Phase 3: BSE StarMF Enterprise Integration
**Status: Partial / Security Risk**
-   **Critical Security**: `BSEStarMFClient` disables SSL verification (`verify=False`) in `requests.post` calls, exposing the system to MITM attacks.
-   **Critical**: `BSEStarMFClient` lacks **Circuit Breaker**. API failures will propagate immediately or hang. Simple retry logic exists but is insufficient for high load.
-   **Missing**: `IntegrationLog` database model is missing. Logging is file-based only (`bse_api.log`), making audit trails difficult and unsearchable.
-   **Code Quality**: Significant code duplication in SOAP client initialization methods.

### Phase 4: Enterprise Investor Onboarding
**Status: Partial**
-   **Missing**: Full Multi-Step Wizard logic is not implemented (currently single form).
-   **Missing**: Real KYC Integration (CAMS/Karvy/NDML API). Currently mocked or basic.
-   **Missing**: Document Verification status and Expiry Date logic.
-   **Missing**: Risk Profiling (14-questionnaire) logic.

### Phase 5: Mandate & Payment Infrastructure
**Status: Partial**
-   **Missing**: Payment Gateway Integration (Razorpay/BillDesk) logic.
-   **Missing**: Mandate Utilization tracking (Daily/Monthly limits).
-   **Code Quality**: `get_bse_mandate_param_string` logic in `utils.py` is fragile.

### Phase 6: Investment Execution Engine
**Status: Critical Gaps**
-   **Critical**: **Risk Controls** (Pre-validation) are completely missing in `order_create`. Orders are sent to BSE without checking exposure limits or concentration.
-   **Critical**: **Large Order Handling** (splitting > 2 Lakhs) is missing. Large orders will fail at BSE.
-   **Missing**: `SIPInstallment` model for tracking individual SIP hits.
-   **Missing**: Logic to process `AllotmentStatement` and update Order status to `ALLOTTED`. Orders remain in `SENT_TO_BSE` indefinitely.

### Phase 7: Holdings & Portfolio Engine
**Status: Partial**
-   **Missing**: Automated Daily Sync Job (Celery) for RTA files. Only manual import command exists.
-   **Missing**: XIRR Calculation logic (stubbed or basic).
-   **Logic Note**: `recalculate_holding` loop logic seems sound for WAC but needs robust testing with edge cases (transfers, reversals).

### Phase 8: Enterprise Compliance & Reporting
**Status: Not Started**
-   **Missing**: **Commission Engine**. `Payout` model exists but "Waterfall" logic for sub-distributors is missing.
-   **Missing**: Regulatory Reports (AMFI Transfer, SEBI Transaction Summary).

## Recommendations

1.  **Immediate Priority**:
    *   **Fix Security**: Enable SSL verification in `BSEStarMFClient`.
    *   **Implement Logging**: Wire up `AuditLog` and create `IntegrationLog`.
    *   **Circuit Breaker**: Add resilience to BSE Client.
2.  **High Priority**: Implement **Risk Controls** and **Large Order Handling** (Phase 6) to prevent failed or non-compliant orders.
3.  **Medium Priority**: Implement **SIP Lifecycle** and **Allotment Sync** to ensure accurate order status tracking.
4.  **Low Priority**: Advanced Reporting and Goal Planning can be deferred.

## Conclusion
The system is functional for basic "Happy Path" scenarios but lacks the resilience, security, and compliance checks required for a production financial application. Immediate attention should be given to the critical gaps in Phase 3 (Security/Integration) and Phase 6 (Execution).
