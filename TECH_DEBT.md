# Technical Debt & Codebase Analysis

## Executive Summary
This document outlines the technical debt identified in the project as of the current audit. While the core functionality for User Management and basic BSE integration exists, several critical areas require immediate attention before a production release, particularly regarding security, compliance, and robustness.

## 1. Security Vulnerabilities (CRITICAL)

### 1.1 SSL Verification Disabled
*   **File:** `apps/integration/bse_client.py`
*   **Issue:** The `BSEStarMFClient` uses `verify=False` in `requests.post` calls (e.g., in `register_client` and `bulk_update_nominee_flags`).
*   **Risk:** This disables SSL certificate verification, making the application vulnerable to Man-in-the-Middle (MITM) attacks. Sensitive data (PAN, Bank Details) could be intercepted.
*   **Recommendation:** Enable SSL verification (`verify=True`) and ensure the server has the correct CA bundle installed.

### 1.2 Logged Sensitive Data (PII)
*   **File:** `apps/integration/bse_client.py`
*   **Issue:** Password masking is implemented for `register_client` and `bulk_update_nominee_flags`. However, `bulk_update_nominee_flags` and other functions still log the entire payload array which contains PII (e.g., PAN, client codes).
*   **Risk:** Leakage of sensitive investor data in application logs.
*   **Recommendation:** Implement a robust `SensitiveDataFilter` for all logging, or use a dedicated `IntegrationLog` model with encrypted storage for payloads.

## 2. Architecture & Design Flaws (HIGH)

### 2.1 Unused Audit Log
*   **File:** `apps/users/models.py` (Model exists), `apps/users/views.py` (Unused)
*   **Issue:** An `AuditLog` model is defined but is not utilized in any views or signals. No user actions (login, edits, orders) are being recorded.
*   **Risk:** Complete lack of audit trail for compliance and security forensics.
*   **Recommendation:** Implement Django Signals or Middleware to automatically create `AuditLog` entries for critical actions (Create/Update/Delete).

### 2.2 Missing Integration Log
*   **File:** `apps/integration/models.py`
*   **Issue:** The `IntegrationLog` model (referenced in `ROADMAP2.md`) does not exist. API logs are written to a file (`bse_api.log`), which is not scalable or searchable.
*   **Risk:** Difficult debugging in production; inability to reconcile API failures with database state.
*   **Recommendation:** Create `IntegrationLog` model to store request/response payloads, status codes, and timestamps for all BSE interactions.

### 2.3 Circuit Breaker Missing
*   **File:** `apps/integration/bse_client.py`
*   **Issue:** The client implements simple retry logic but lacks a true Circuit Breaker pattern. If BSE is down, the application will continue to hammer the API until timeouts occur, potentially causing resource exhaustion.
*   **Recommendation:** Implement a Circuit Breaker (e.g., using `pybreaker` or custom logic) to fail fast when the external service is unhealthy.

## 3. Code Quality & Maintainability (MEDIUM)

### 3.1 Code Duplication in SOAP Client Initialization
*   **File:** `apps/integration/bse_client.py`
*   **Issue:** Methods `_get_soap_client`, `_get_upload_soap_client`, and `_get_query_soap_client` share 90% of their logic (initialization, logging plugin, error handling).
*   **Recommendation:** Refactor into a single private method `_get_client(wsdl, service_name, port_name)` to reduce duplication and maintenance overhead.

## 4. Missing Features (HIGH)

### 4.1 Risk Controls & Limits
*   **File:** `apps/investments/views.py` (`order_create`)
*   **Issue:** Orders are sent to BSE without any pre-validation of exposure limits, per-transaction limits, or user-specific risk profiles.
*   **Risk:** Potential for financial loss or regulatory non-compliance.
*   **Recommendation:** Implement a `RiskEngine` service that validates orders against defined rules before allowing submission.

### 4.2 Large Order Handling
*   **Issue:** No logic exists to split large orders (e.g., > Rs 2 Lakhs for certain schemes) into multiple sub-orders as required by some exchanges/AMCs.
*   **Recommendation:** Implement an order splitting utility in `OrderForm` processing.

### 4.3 SIP Lifecycle Management
*   **Issue:** `SIP` model exists, but there is no automated job (Celery/Cron) to process installments, track end dates, or mark SIPs as expired.
*   **Recommendation:** Implement background tasks for SIP lifecycle management.

## 5. Testing & Environment (MEDIUM)

*   **Status:** Test environment (`pytest`) dependencies and mock unit tests for `BSEStarMFClient` have been implemented.
