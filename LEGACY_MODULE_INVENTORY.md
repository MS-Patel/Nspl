# Legacy Portal Module Inventory

## Scope and status legend

This inventory reflects the codebase inspected on 20 June 2026. “Implemented” means executable code and a route, command, or model exist. “Partial” means important paths contain placeholders, manual dependencies, or incomplete lifecycle behavior. “Reference only” means documentation or dormant code describes the capability but no complete production path was found.

| Module | Purpose | Primary users | Key screens / tools | Dependencies | Status |
|---|---|---|---|---|---|
| Authentication and account security | Password/OTP login, logout, password reset/change, forced first-login password change, profile display/edit | All users | `/legacy/login/`, `/login/`, OTP APIs, profile and password screens | Django auth, SMS gateway, `User`, `OneTimePassword`, force-password middleware | Implemented; two parallel login surfaces exist |
| Branch management | Maintain operational branches and attach RMs/investors | Admin | Branch list/create/update/delete | `Branch`, `RMProfile`, `InvestorProfile` | Implemented |
| RM management | Maintain relationship managers, employee codes, branches, bank/contact data, bulk import | Admin | RM list/create/update/upload, RM mapping | `User`, `RMProfile`, `Branch`, CSV parser | Implemented |
| Distributor management | Maintain distributors/sub-distributors, ARN/EUIN/broker codes, RM ownership, approval and bulk import | Admin, RM | Distributor list/create/update/upload, hierarchy mapping | `DistributorProfile`, `RMProfile`, `User`, payout categories | Implemented; hierarchical parent field exists |
| Investor management and onboarding | Create and maintain detailed BSE-ready investor profiles, applicants, guardians, banks, nominees and documents | Admin, RM, Distributor; limited self-service | Investor list, onboarding wizard, detail/update, bulk upload, distributor/RM mapping | `InvestorProfile`, `BankAccount`, `Nominee`, `Document`, hierarchy models | Implemented and business critical |
| KYC and compliance | PAN inquiry, local KYC flag, NDML registration/inquiry/download/modification, nomination authentication/opt-out | Admin/operations; investor actions through detail workflow | PAN check, NDML tools/status list, push to BSE, FATCA upload, nominee auth | CVL SOAP, NDML SOAP, BSE UCC/FATCA/nominee APIs | Implemented but operationally complex |
| BSE client registration (UCC) | Validate investor data and create/modify BSE client master records | Admin, RM, Distributor with investor access | Investor detail “Push to BSE”, FATCA, nominee actions | BSE common JSON API, BSE parameter mapper, investor/bank/nominee data | Implemented |
| Product and AMC master | Maintain AMC/scheme masters, BSE/RTA mappings, transaction limits, active flags and enrichment | Admin; explorer available to authenticated users | Scheme list/detail/edit/upload, AMC list, NAV upload, explorer | BSE/AMFI/RTA files, `Scheme`, `AMC`, mapping and NAV models | Implemented; several overlapping import paths |
| Scheme explorer | Search/filter schemes by AMC/category/type/plan and display product/performance data | Authenticated users | `/explore/`, scheme detail | Scheme/NAV/enrichment models | Implemented |
| Order management | Create and monitor purchase, redemption, switch and SIP-registration orders | Admin, RM, Distributor; investor is technically permitted by form/view | Order form/list, redemption form, metadata APIs | BSE order SOAP, hierarchy access rules, scheme limits, folios | Implemented; synchronous external calls |
| Mandates | Register e-mandates, retry failed submissions, generate authorization URLs and track status | Admin, RM, Distributor, Investor within hierarchy | Mandate create/retry/auth, mandate report | BSE MFAPI/query service, bank accounts, investor UCC | Implemented |
| SIP lifecycle | Register XSIP, generate planned installments, fetch child orders, alerts, reconciliation and lifecycle status | Operations and all hierarchy viewers | SIP dashboard/insights/upcoming API plus management commands | BSE XSIP/child-order services, mandates, RTA transactions, SMS | Implemented but scheduling is incomplete outside manual commands |
| Folio and portfolio | Track folios, holdings, valuations, gain/loss and investor portfolio dashboards | All roles within hierarchy | Holdings investor list, portfolio dashboard, folio detail | RTA/BSE transactions, NAV, holding recalculation | Implemented and business critical |
| RTA ingestion and reconciliation | Import CAMS/KFintech/Franklin transaction feeds, deduplicate, map investors/schemes, create failures and recalculate holdings | Admin/operations | RTA upload, failed-record list/retry | Email fetcher, DBF/CSV parsers, scheme mappings, transaction fingerprints | Implemented; strongest legacy-specific capability |
| BSE report synchronization | Fetch order status, provisional status, allotment and redemption reports and create provisional transactions | Admin/operations; some sync happens on page load | Report screens, daily sync command, historical sync | BSE query SOAP, orders, transactions, holdings | Implemented |
| Brokerage ingestion | Upload monthly CAMS/Karvy brokerage data and map rows to distributors | Admin | Brokerage upload/import list/detail/reprocess | Brokerage parsers, folio mapping, distributor codes, schemes | Implemented |
| Payout calculation | Aggregate brokerage/AUM, apply distributor category share, produce payout records | Admin; RM/distributor see scoped payout lists | Payout dashboard/list/detail, category CRUD | `BrokerageImport`, `BrokerageTransaction`, `DistributorCategory`, `Payout` | Implemented; model is simpler than architecture’s multi-tier aspiration |
| Payout analytics | Aggregate brokerage by investor, RM, distributor and AMC; export operational files | Admin | Investor analytics dashboard and exports | Brokerage imports, hierarchy and product masters | Implemented |
| Reports | Operational, master, transaction, BSE and portfolio PDF/CSV/XLSX reporting | Role-scoped authenticated users | Reports dashboard and report routes | Most domain models, Grid.js export, ReportLab PDF generator | Implemented; some PDF calculations are explicitly approximate |
| Goals | Create goals and allocate holdings by percentage | Admin, Distributor, Investor; RM behavior is not consistently implemented | Goal list/create/update/detail/delete | Holdings and investor hierarchy | Implemented |
| CAS / external holdings | Upload password-protected CAS PDFs and extract external holdings | Admin, Distributor, Investor | CAS upload/list/external holdings | PDF parser, local file storage, background thread | Partial; parser identifies itself as placeholder for format complexity |
| Administration | Company identity, maintenance mode, report disclaimer, email, NDML and RTA mailbox configuration | Admin/superuser | Administration index/configuration, Django admin | `SystemConfiguration`, middleware, email and integration clients | Implemented; sensitive values stored in plain model fields |
| Notifications | OTP SMS, SIP reminder SMS, maintenance email | All users / operations | OTP endpoints; management commands | SMS gateway, SMTP, system configuration | Implemented; scheduling must be external |
| Public/React shell | Catch-all SPA shell plus legacy Django UI | Public and authenticated users | `/login/` and catch-all route | React build/static assets, Django templates | Implemented; creates dual-portal ambiguity |
| Django admin | Hidden CRUD/diagnostic interface for registered models | Staff/superuser | `/admin/` | Django admin registrations | Implemented; hidden from normal navigation |

## Cross-module dependency chain

The most important production chain is:

`Investor/Hierarchy → BSE UCC and mandate → Order/XSIP → BSE provisional status → RTA confirmed transaction → Holding/NAV valuation → Reports and brokerage attribution`.

Failure or mismatch in investor UCC, scheme mapping, folio attribution, or distributor mapping propagates into portfolios, SIP intelligence, reconciliation and payouts.

