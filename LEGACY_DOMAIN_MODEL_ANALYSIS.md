# Legacy Domain Model Analysis

## Domain overview

The database separates intent (`investments.Order`) from settlement evidence (`reconciliation.Transaction`). BSE reports can create provisional transactions; RTA mailbacks are treated as the stronger confirmation source. Holdings are cached/derived by investor, scheme and folio.

## Core models

| Domain | Models | Role |
|---|---|---|
| Identity and hierarchy | `User`, `Branch`, `RMProfile`, `DistributorProfile`, `InvestorProfile` | Authentication, role and ownership tree |
| Investor compliance | `BankAccount`, `Nominee`, `Document`, `NDMLKYCDetails`, `AuditLog`, `OneTimePassword` | BSE/KYC payload data and account security |
| Product master | `AMC`, `SchemeCategory`, `Scheme`, `BSESchemeMapping`, `RTASchemeMapping`, `NAVHistory`, `UnmatchedSchemeLog` | Tradable master, source mappings and valuation |
| Product enrichment | `FundManager`, `SchemeManager`, `SchemeHolding`, `SchemeSectorAllocation`, `SchemeAssetAllocation`, `SchemeRatio` | Explorer/performance content |
| Execution intent | `Mandate`, `Folio`, `SIP`, `Order`, `SIPInstallment` | Order and systematic-plan lifecycle |
| Settlement and positions | `RTAFile`, `Transaction`, `Holding`, `FailedRTARecord`, `OrderReconciliation` | Imported evidence, exceptions and current positions |
| Brokerage and payout | `DistributorCategory`, `BrokerageImport`, `BrokerageTransaction`, `Payout`, `FolioDistributorMapping` | Monthly commission ingestion and distribution |
| Analytics | `Goal`, `GoalMapping`, `CASUpload`, `ExternalHolding` | Goal allocation and externally held assets |
| Configuration | `SystemConfiguration` | Company, email, KYC and RTA operational settings |

## Highlighted business entities

### Investor

`users_investorprofile` is the largest business master. It links one-to-one to `User` and optionally to Distributor, RM and Branch. It stores PAN, names, contact/address, resident/NRI data, tax/occupation/wealth flags, joint applicants, guardian, demat details, FATCA/KYC/UCC state, nominee-auth state and BSE remarks. Child tables store up to multiple banks, nominees and documents.

Critical relationships:

- Investor → Distributor → RM → Branch.
- Investor → Orders, Mandates, SIPs, Folios, RTA Transactions, Holdings, Goals, CAS uploads.
- PAN is unique; UCC is the external BSE client identifier.

### Folio

There are two folio representations:

- `investments_folio`: normalized investor + AMC + folio number, used by orders/SIPs.
- Folio number fields on `Transaction`, `Holding`, `BrokerageTransaction`, `ExternalHolding` and `FolioDistributorMapping`.

This duplication is operationally necessary for raw feeds but creates normalization and matching risk.

### Transaction

`reconciliation_transaction` is the detailed settlement ledger. It stores source/origin, provisional state, BSE order ID, RTA transaction identifiers, financial values, tax/load/GST fields, bank/payment metadata, broker attribution and raw source data. A SHA-256-style fingerprint supports deduplication. It is the source for holdings and portfolio reporting.

### Brokerage

`payouts_brokerageimport` represents a unique month/year import. `BrokerageTransaction` preserves source rows and mapping status. Mapped rows aggregate into one `Payout` per distributor/import. `FolioDistributorMapping` is a manual override/master used when source brokerage rows cannot identify the distributor reliably.

### RM and Branch

`RMProfile` belongs to a `Branch`; distributors and investors can point to an RM. Investors also store Branch directly. This denormalization supports direct investors but permits hierarchy inconsistencies unless actively validated.

### User

`users_user` extends Django user with `user_type` (`ADMIN`, `RM`, `DISTRIBUTOR`, `INVESTOR`), display name and forced password change. Django groups/permissions exist structurally but business authorization is primarily hard-coded by `user_type` and queryset filtering.

## Relationship map

```text
Branch
  └─ RMProfile
       └─ DistributorProfile ── parent → DistributorProfile
            └─ InvestorProfile
                 ├─ BankAccount / Nominee / Document / NDMLKYCDetails
                 ├─ Mandate ── SIP ── SIPInstallment
                 ├─ Order ── Scheme / target Scheme / Folio
                 ├─ Folio ── AMC
                 ├─ Transaction ── Scheme / RTAFile
                 ├─ Holding ── Scheme ── NAVHistory
                 ├─ Goal ── GoalMapping ── Holding
                 └─ CASUpload ── ExternalHolding

BrokerageImport
  ├─ BrokerageTransaction ── Distributor / Scheme
  └─ Payout ── Distributor
```

## Critical tables

| Table | Why critical |
|---|---|
| `users_investorprofile` | Compliance identity and BSE UCC payload source |
| `products_scheme` | Transaction eligibility, limits and all external mappings |
| `investments_order` | Local execution request and BSE lifecycle state |
| `reconciliation_transaction` | Settlement ledger and RTA/BSE evidence |
| `reconciliation_holding` | Current portfolio position cache |
| `investments_sip` / `investments_sipinstallment` | Systematic-plan lifecycle and operational alerts |
| `payouts_brokeragetransaction` / `payouts_payout` | Distributor remuneration |
| `administration_systemconfiguration` | Runtime integration and mail settings |

## Transaction tables

- `investments_order`: purchase, redemption, switch and SIP registration intent.
- `reconciliation_transaction`: BSE provisional and RTA confirmed financial events.
- `investments_sipinstallment`: expected installment and matched transaction.
- `reconciliation_orderreconciliation`: match decision/confidence trail.
- `payouts_brokeragetransaction`: brokerage earning rows, not investor cash transactions.

## Master tables

- User/hierarchy: Branch, RMProfile, DistributorProfile, InvestorProfile.
- Investor submasters: BankAccount, Nominee, Document.
- Product: AMC, SchemeCategory, Scheme and mapping/enrichment tables.
- Commercial: DistributorCategory, FolioDistributorMapping.
- Configuration: SystemConfiguration.

## Reporting tables

There are no dedicated warehouse/reporting tables. Reports query transactional/master tables directly. `Holding`, `Payout` and `ExternalHolding` serve as cached analytical projections.

## Data integrity observations

- Strong constraints: unique PAN, broker code, employee code, AMC code, scheme code/mappings, NAV scheme/date, folio investor/AMC/number, holding investor/scheme/folio, brokerage month/year.
- Weak areas: UCC is not shown as unique; direct RM/Branch and distributor-derived hierarchy can disagree; folio numbers repeat across several tables; source records contain JSON/raw fields with limited database validation.
- `AuditLog` exists but no systematic write path was found.
- Historical product models failed automatic Django shell import, indicating stale or inconsistent historical-model definitions.

