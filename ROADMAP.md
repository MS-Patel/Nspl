# Implementation Roadmap

This document outlines the recommended order of execution for developing the Mutual Fund Portal. Follow these phases sequentially to ensure dependencies are met.

## Phase 1: Foundation & User Management
**Goal:** Establish the hierarchy and authentication system.

1.  **Task**: Define Custom User Model.
    *   *Details*: Implement `User` model inheriting from `AbstractUser`. Add fields like `user_type` (Admin, RM, Distributor, Investor).
2.  **Task**: Implement Profile Models & Hierarchy.
    *   *Details*: Create `RMProfile`, `DistributorProfile`, `InvestorProfile`. Implement `ForeignKey` relationships to establish the tree structure (Investor -> Distributor -> RM -> Company).
3.  **Task**: Authentication Views & UI.
    *   *Details*: Build Login/Logout pages using the LimeOne theme. Implement role-based redirect (Distributors go to their dashboard, Investors to theirs).

## Phase 2: Master Data (Products)
**Goal:** Populate the system with Mutual Fund schemes so we can reference them later.

4.  **Task**: Design Product Models.
    *   *Details*: Create models for `AMC`, `SchemeCategory`, `Scheme`.
5.  **Task**: Import Scheme Master.
    *   *Details*: Create a script/management command to import the BSE StarMF Scheme Master file (CSV/Text) to populate the database.
6.  **Task**: Scheme Explorer UI.
    *   *Details*: Build a page using `Grid.js` to list schemes with filters (AMC, Category, Scheme Type).

## Phase 3: Integration Core (BSE StarMF)
**Goal:** Establish connectivity with the exchange.

7.  **Task**: BSE API Client Wrapper.
    *   *Details*: Create a Python class in `apps/integration` to handle SOAP/REST authentication with BSE StarMF. Implement `getPassword` and session management.
8.  **Task**: Client Creation (UCC) Logic.
    *   *Details*: Map `InvestorProfile` fields to BSE's UCC format. Implement the API call to push client data to BSE.

## Phase 4: Investor Onboarding
**Goal:** Allow Distributors to onboard investors and get them ready for transaction.

9.  **Task**: Investor Creation Form.
    *   *Details*: specific form using `JustValidate` to collect Investor details (PAN, Bank, Address, Nominee).
10. **Task**: KYC Integration & Document Upload.
    *   *Details*: Integrate KRA API to fetch KYC status. Allow uploading of documents (PAN, Cheque).
11. **Task**: Connect UCC Generation.
    *   *Details*: Trigger the BSE API call (from Task 8) upon form submission/approval.

## Phase 5: Investment Execution (Orders)
**Goal:** Enable buying and selling of funds.

12. **Task**: Order Entry Models & UI.
    *   *Details*: Create `Order` model. Build UI for "New Purchase", "Redemption", "Switch".
13. **Task**: Execute Lumpsum Orders.
    *   *Details*: Connect the "Place Order" button to BSE's `OrderEntry` API. Handle API responses and save Order ID.
14. **Task**: SIP Registration & Mandates.
    *   *Details*: Implement `SIP` registration (X-SIP API). Generate Mandate registration link/form.

## Phase 6: Reconciliation & Holdings
**Goal:** Show the investor what they actually own (Source of Truth: RTA).

15. **Task**: RTA Parser Engine.
    *   *Details*: Build parsers for CAMS (`WBR9`), Karvy, and Franklin mailback files.
16. **Task**: Daily Sync Job.
    *   *Details*: Create a background task (Celery) to read uploaded RTA files and update `Transaction` and `Holding` models.
17. **Task**: Portfolio Dashboard.
    *   *Details*: Build the Investor Dashboard showing Total AUM, current value of holdings, and annualized returns (XIRR).

## Phase 7: Payouts & Commissions
**Goal:** Calculate earnings for the Broker and Distributors.

18. **Task**: Commission Structure Configuration.
    *   *Details*: Build a UI for Admin to define payout rules (e.g., "Equity schemes: 0.8% for < 1Cr AUM").
19. **Task**: Brokerage Calculation Engine.
    *   *Details*: Script to run monthly. It takes the average AUM from RTA data, applies the Commission Structure, and generates a `PayoutLedger`.
20. **Task**: Payout Reports.
    *   *Details*: Dashboard for Distributors to see their monthly earnings.

## Phase 8: Analytics & Value Adds
**Goal:** Enhance the user experience.

21. **Task**: Goal Planning Module.
    *   *Details*: UI to create goals and map investments to them.
22. **Task**: CAS Import.
    *   *Details*: Allow PDF upload of CAS to parse external investments.

---
**Note:** You can copy-paste the text of any Task above when assigning work to me in the future.
