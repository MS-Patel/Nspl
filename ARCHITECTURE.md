# Mutual Fund Portal Architecture & Development Guidelines

## 1. Project Overview
This project is a B2B Mutual Fund Investment Portal designed for a Broker. The platform allows the Broker (Company) to manage a network of Distributors, who in turn onboard Investors. The platform facilitates investment execution via the **BSE StarMF API** and calculates payouts/commissions based on AUM using **RTA Mailback** data.

## 2. User Roles & Hierarchy

The system follows a strict hierarchical model:

1.  **Company (Super Admin/Broker)**
    *   **Role**: Root node. Full access to all data, configuration of global settings, commission structures, and user management.
    *   **Features**: Master Dashboard, Payout Distribution, Employee (RM) Management.

2.  **Relationship Manager (RM)**
    *   **Role**: Employee of the Company.
    *   **Responsibility**: Manages a specific set of Distributors.
    *   **Access**: View/Edit rights for Distributors and Investors under their assigned hierarchy.

3.  **Distributor (Sub-broker/Partner)**
    *   **Role**: Business partner who brings in Investors.
    *   **Responsibility**: Onboarding Investors, creating Transactions (SIP/Lumpsum), Risk Profiling.
    *   **Payout**: Earns commission based on the AUM of their investors.
    *   **Hierarchy**: Can have sub-distributors (Multi-level).

4.  **Investor (Client)**
    *   **Role**: End client.
    *   **Access**: **View-Only** Dashboard. Can view Holdings, Portfolio Valuation, Goal Progress, and approve orders if required (via external link/OTP, but no direct transaction entry on portal).

## 3. Application Structure (Django Apps)

The project is modularized into the following Django apps (located in `apps/`):

### `apps/users`
*   **Purpose**: Authentication, Authorization, and Profile Management.
*   **Models**:
    *   `User`: Extended AbstractUser.
    *   `Profile`: Base profile linking to User.
    *   `DistributorProfile`: Links to RM, holds ARN info, Payout Tier details.
    *   `InvestorProfile`: Links to Distributor, holds KYC status, PAN, Date of Birth.
    *   `RMProfile`: Employee details.
    *   `Document`: KYC documents (Aadhaar, PAN, Cancelled Cheque).

### `apps/products`
*   **Purpose**: Mutual Fund Master Data.
*   **Models**:
    *   `AMC`: Asset Management Company details.
    *   `Scheme`: Scheme Master (ISIN, Scheme Code, Name, Type).
    *   `NAVHistory`: Daily NAV records.
    *   `SchemeCategory`: Equity, Debt, Hybrid, etc.

### `apps/investments`
*   **Purpose**: Transaction Management and Portfolio Tracking.
*   **Models**:
    *   `Folio`: Investor's folio number with an AMC.
    *   `Order`: Temporary transaction request (Lumpsum/SIP).
    *   `Transaction`: Confirmed unit allotment/redemption.
    *   `SIP`: Systematic Investment Plan registration details (URN, Start Date, End Date).
    *   `Mandate`: Bank Mandate (UMRN) status for SIPs.
    *   `Holding`: Current unit balance (Derived or Cached).

### `apps/payouts`
*   **Purpose**: Brokerage Calculation and Commission Distribution.
*   **Models**:
    *   `CommissionStructure`: Rules for payout (e.g., "0-1Cr AUM = 0.5%", ">1Cr = 0.6%").
    *   `BrokerageReport`: Parsed data from RTA/BSE.
    *   `PayoutLedger`: Calculated earnings for Distributors.

### `apps/integration`
*   **Purpose**: External API and File interfaces.
*   **Components**:
    *   **BSE StarMF Client**: SOAP/REST wrapper for:
        *   Client Creation (UCC).
        *   Order Entry.
        *   Mandate Registration (XSIP/E-Mandate).
        *   Fatca/CRS Upload.
    *   **RTA Parser**: Logic to parse CAMS/Karvy/Franklin mailback files (.dbf, .csv) for reconciliation.
    *   **KYC Provider**: Interface for KRA (CVL/NDML) verification.

### `apps/analytics`
*   **Purpose**: Reporting and Value-added features.
*   **Models**:
    *   `Goal`: User-defined goals (Retirement, Education) linked to Folios.
    *   `RiskProfile`: Answers to risk questionnaire and score.
    *   `CASUpload`: Storing uploaded Consolidated Account Statements.

## 4. Key Functional Requirements

### A. Onboarding & KYC
*   **Digital KYC**: Integrate with KRA to fetch status by PAN.
*   **Paperless**: Integration with eSign providers (Leegality/Digio) for signing forms.
*   **UCC Creation**: Push investor details to BSE StarMF to generate Unique Client Code (UCC).

### B. Mutual Fund Transactions (BSE StarMF)
*   **Explorer**: Search schemes by Performance, Category, or AMC.
*   **Execution**:
    *   **Purchase/Redeem/Switch**: Support both Lumpsum and SIP.
    *   **Payments**: Netbanking and UPI links generated via BSE.
*   **Synchronization**: Daily jobs to fetch Order Status and Allotment feeds.

### C. Portfolio & Reporting
*   **Dashboard**: AUM Summary, Top Schemes, Asset Allocation (Pie Charts).
*   **XIRR**: Extended Internal Rate of Return calculation for accurate performance measuring.
*   **CAS Import**: Allow investors to upload CAS (PDF) to track external investments.

### D. Payout Engine
*   **RTA Mailback**: Source of truth for AUM. Automated ingestion of daily/monthly transaction files.
*   **Tiered Calculation**: Logic to apply different commission rates based on Distributor AUM.
*   **Pass-through**: Calculate share for Sub-distributors vs Master Distributors.

## 5. Technical Guidelines

### Frontend Development
*   **Theme**: Use `theme/` (LimeOne) templates as the source of truth.
*   **Build System**: `laravel-mix` (Webpack).
    *   Source JS: `src/js/pages/`
    *   Output: `assets/js/pages/`
*   **Validation**: Use `JustValidate` library.
*   **Tables**: Use `Grid.js` for data presentation.

### Backend Development
*   **ORM**: Use Django Models with proper `related_name`.
*   **Tasks**: Use Celery (or Django Q) for background tasks (BSE Sync, RTA Parsing).
*   **API**: Use Django Rest Framework (DRF) if internal APIs are needed for dynamic frontend components.
