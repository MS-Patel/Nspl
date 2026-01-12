# Production-Ready Mutual Fund Portal - Implementation Roadmap

**Enterprise B2B Broker Portal for RM/Distributor Investor Onboarding & Transactions**

Follow phases sequentially. Each phase includes **production hardening**, **security**, **validation**, and **test coverage requirements**.

## Phase 1: Enterprise Foundation & Identity Management
**Goal:** Bulletproof authentication, hierarchical RBAC, and audit trails.

1. **Custom User & Profile Models (Production Grade)**
   - `User`: `AbstractUser` + `user_type` (Admin/RM/Distributor/Investor), `status` (Active/Inactive/Suspended), `created_by`, `audit_fields`
   - `RMProfile`: `amc_codes`, `branch_code`, `sebi_regn_no`
   - `DistributorProfile`: `arn_code`, `euin`, `parent_rm` (FK), `hierarchy_path`
   - `InvestorProfile`: `client_code`, `ucc`, `pan`, `kyc_status`, `risk_profile`, `pe_type` (Resident/NRI), `fatca_status`
   - **Add**: Soft delete, full audit trail (`AuditLog` model)

2. **Enterprise Authentication & Authorization**
   - JWT + Session hybrid auth
   - Role-based + Hierarchy-based permissions (RM sees only their distributors)
   - MFA for Admin/RM, OTP for Distributors
   - Login analytics + failed attempt lockout

3. **Dashboard Infrastructure**
   - Role-specific dashboards with real-time metrics
   - LimeOne theme integration with `Grid.js`, `TomSelect`, `JustValidate`

**Tests Required**: 95% coverage - user CRUD, hierarchy traversal, permission matrix

## Phase 2: Master Data & Compliance Foundation
**Goal:** Regulatory-compliant scheme catalog with real-time NAV.

4. **Enterprise Product Models**
   - `AMC`, `SchemeCategory`, `SchemeRiskGrade`, `Scheme`
   - NAV history (`daily_nav`), `riskometer_rating`, `exit_load_structure`
   - `SchemeLock` for regulatory restrictions

5. **Automated Master Sync**
   - BSE StarMF daily scheme master + NAV sync (management command)
   - Data validation + integrity checks
   - Fallback to manual CSV upload

**Tests Required**: Scheme CRUD, NAV sync validation, data integrity

## Phase 3: BSE StarMF Enterprise Integration
**Goal:** Production-grade, fault-tolerant BSE connectivity.

6. **BSE Client with Circuit Breakers**
   - SOAP client with connection pooling, retry logic (exponential backoff)
   - Session management with auto-refresh
   - Circuit breaker pattern for API failures
   - Request/response logging (`IntegrationLog`)

7. **UCC Generation Pipeline**
   - Client master validation (PAN uniqueness, KYC status)
   - BSE `CreateClient` API with retry + idempotency
   - UCC response parsing + status tracking

**Tests Required**: Mock BSE responses, edge cases (duplicate PAN, API failures)

## Phase 4: ENTERPRISE INVESTOR ONBOARDING (INTENSIFIED)
**Goal:** SEBI-compliant, paperless investor lifecycle management.

8. **Investor Onboarding Wizard (Multi-Step)**
    Step 1: Personal Info (PAN auto-fetch from KRA)Step 2: KYC Status (CAMS/KARVY API integration)Step 3: Bank Details (IFSC validation + account verification)Step 4: FATCA/PE (NRI compliance)Step 5: Nominee (2 levels allowed)Step 6: Risk Profiling (14-questionnaire)Step 7: E-Sign Consent


9. **KYC & Document Management**
- KRA API integration (CAMS/KARVY/BSE)
- Document upload with OCR validation (PAN/Aadhaar)
- `Document` model with `doc_type`, `verified_status`, `expiry_date`
- AES-256 document encryption at rest

10. **UCC + Client Master Automation**
 - Auto-trigger BSE UCC on KYC Approved
 - Client master sync with BSE daily
 - `InvestorStatus` workflow (Pending/KYC-Approved/UCC-Created/Active)

**Tests Required**: Full onboarding flow, KYC edge cases, document validation

## Phase 5: MANDATE & PAYMENT INFRASTRUCTURE (INTENSIFIED)
**Goal:** Production-ready mandate registration and payment orchestration.

11. **e-NACH Mandate System**
 ```
 Features:
 - Multi-bank mandate creation (Axis/HDFC/ICICI/SBI)
 - BSE e-Mandate API integration
 - Mandate limit management (₹2L/single, ₹10L/monthly)
 - `Mandate` model: bank_ifsc, ac_no_hash, max_amount, frequency
 ```

12. **Payment Gateway Orchestration**
 - Razorpay/BillDesk integration
 - UPI auto-detection
 - Payment reconciliation with BSE order status

**Tests Required**: Mandate lifecycle, payment failures, bank rejections

## Phase 6: INVESTMENT EXECUTION ENGINE (INTENSIFIED)
**Goal:** High-volume order management with risk controls.

13. **Order Management System**
 ```
 Order Types:
 • Lumpsum Purchase (Fresh/Switch-in)
 • SIP (New/Topup/Pause/Stop)
 • Redemption (Partial/Full)
 • Switch (Same/Fund House/Different)
 ```

14. **Production Order Flow**
 ```
 1. Pre-validation (scheme lock, investor KYC, sufficient mandate)
 2. Risk checks (exposure limits, concentration)
 3. BSE OrderEntry API (with order splitting for large amounts)
 4. Payment initiation (Netbanking/UPI/Auto-debit)
 5. BSE OrderStatus polling (24hrs)
 6. NAV-based allotment calculation
 ```

15. **SIP Lifecycle Management**
 - Installment calendar generation
 - Auto-debit failure handling (retry 3x)
 - Grace period management (T+3 days)
 - `SIPInstallment` tracking model

**Tests Required**: 100% order scenarios, payment failures, SIP lifecycle

## Phase 7: HOLDINGS & PORTFOLIO ENGINE (INTENSIFIED)
**Goal:** Real-time portfolio valuation and performance analytics.

16. **Multi-RTA Reconciliation Engine**
 ```
 Parsers Required:
 • CAMS WBR9 (Units/Ledger)
 • Karvy/KFintech (legacy formats)
 • Franklin Templeton (mailback)
 ```

17. **Daily Reconciliation Pipeline**
 ```
 Celery workflow:
 1. File upload → OCR → Parser
 2. Transaction matching (BSE Order ID)
 3. Holding valuation (latest NAV)
 4. XIRR calculation (daily)
 5. P&L computation
 ```

18. **Investor Portfolio Dashboard**
 ```
 Metrics:
 • Real-time AUM (Holdings + Pending Orders)
 • Portfolio XIRR (absolute/annualized)
 • Risk metrics (Sharpe, Sortino, Beta)
 • Category allocation pie chart
 • Transaction history (filterable)
 ```

**Tests Required**: RTA parsing accuracy, reconciliation mismatches, performance calcs

## Phase 8: ENTERPRISE COMPLIANCE & REPORTING
**Goal:** Regulatory reporting and audit readiness.

19. **Trail Commission Engine**
 - AUM-based commission slabs (trailing 12 months)
 - Distributor hierarchy payout waterfall
 - GST invoicing (18% on commission)

20. **Regulatory Reports**
 - ARN-wise AUM report (AMFI)
 - Investor transaction summary (SEBI)
 - FATCA/CRS reporting (NRI)

## Phase 9: PRODUCTION TEST SUITE (MANDATORY)
**Goal:** Zero-defect production deployment.

---

**JULES INSTRUCTIONS:**
1. Implement phases sequentially with test-first development
2. No deployment without 95% test coverage
3. Daily standups required for Phase 4-7 (critical path)
4. Production parity environments mandatory
5. Zero critical bugs before Phase 6 completion
