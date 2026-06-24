# Legacy Portal Executive Summary

## What does the system do?

The legacy portal operates a broker-led mutual-fund distribution business. It manages branches, RMs, distributors and investors; prepares BSE-compliant client data; creates UCCs, mandates, purchases, redemptions, switches and SIPs; synchronizes BSE status; ingests RTA transactions; values holdings; calculates distributor brokerage/payouts; and produces operational and investor reports.

## Most valuable capabilities

1. Detailed investor/BSE onboarding, including NRI, demat, joint applicant, bank, FATCA and nominee data.
2. End-to-end BSE order, XSIP and mandate integration.
3. BSE provisional-to-RTA-confirmed reconciliation with deduplication and failed-row recovery.
4. Portfolio reconstruction and valuation from transaction evidence.
5. Distributor/RM hierarchy and scoped access.
6. Monthly brokerage ingestion, folio repair mapping, payout calculation and analytics.
7. Operational BSE/RTA/master reports and portfolio PDFs.

## What appears business critical?

- Investor, UCC, bank and nominee master data.
- Scheme/BSE/RTA mappings and transaction-limit metadata.
- Order/Mandate/SIP identifiers and lifecycle history.
- RTA transaction ledger, fingerprints, source files and failed records.
- Holdings and NAV history.
- Distributor attribution, brokerage imports and payout history.
- Hierarchy links between investor, distributor, RM and branch.

## What appears obsolete or transitional?

- Parallel legacy Django and React login/shell routes.
- Upload SOAP client with no active business call found.
- Duplicate NAV, cleanup and payout command paths.
- One-time historical BSE import tools after data conversion is complete.
- Theme/demo navigation links that do not represent portal capabilities.
- Legacy page-triggered synchronization once durable background orchestration exists.

## What appears unique?

The strongest differentiator is not the order form; it is the operational evidence chain:

`BSE execution/provisional data → RTA mailback confirmation → folio/holding valuation → SIP intelligence → distributor brokerage attribution`.

The manual repair tools—failed RTA rows, unmatched schemes and folio-distributor mapping—also encode production knowledge that a greenfield platform can easily miss.

## What should definitely be migrated?

- Canonical hierarchy and investor ownership rules.
- Full investor/BSE field coverage and pre-submission validation lessons.
- UCC, FATCA, nominee-auth, mandate, purchase, redemption, switch and SIP workflows.
- BSE/RTA source precedence and idempotent reconciliation.
- Transaction fingerprints, failed-row queues and repair/reprocess workflows.
- Scheme eligibility/limit master data and external mappings.
- Folio/holding/NAV valuation history.
- SIP installment lifecycle and child-order correlation.
- Brokerage source ingestion, attribution overrides, category/share logic and payout audit history.
- Role-scoped operational and investor reports, after validating calculations.

## What should definitely not be migrated?

- Hardcoded/plaintext credentials and disabled TLS verification.
- Passwords derived from PAN/employee identifiers.
- File payload logs containing PII.
- Synchronous external sync on user page loads.
- Raw threads as the durable job mechanism.
- Placeholder/estimated capital-gain or CAS parsing logic presented as authoritative.
- Duplicated role checks, folio identity and hierarchy state without a canonical policy/model.
- Manual KYC toggle as a replacement for provider-backed evidence.

## Comparison readiness

The companion artifacts provide:

- modules and screens,
- domain models and relationships,
- BSE operations and status flow,
- business workflows and validations,
- report and automation catalogs,
- permission rules,
- an editable feature matrix.

For the future Wealth Platform comparison, evaluate each matrix row against four dimensions: capability present, workflow parity, validation parity and operational recovery parity. A screen-level match alone is insufficient.

