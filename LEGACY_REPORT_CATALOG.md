# Legacy Report Catalog

## Report inventory

| Name | Purpose | Input filters | Output columns / sections | Export formats | Users |
|---|---|---|---|---|---|
| Investor Report | Complete investor/KYC/master extract | Search; role scope | Name, PAN, contact, distributor, KYC, username/name parts, DOB/gender, domestic/foreign address, tax/occupation/holding/wealth/PEP, demat IDs, applicants/guardian, nomination/UCC/offline, login/active, default bank and first nominee | CSV, XLSX | Admin global; RM/distributor/investor scoped |
| Mandate Report | Mandate and bank status | Search; role scope | Mandate ID/type/limit/dates/status/timestamps, investor, PAN/UCC, bank/account/IFSC | CSV, XLSX | All roles scoped |
| Transaction Report | Local order book report | Search; role scope | Date, reference, investor, scheme, transaction type, amount, status, BSE remarks | CSV, XLSX | All roles scoped |
| RTA Transaction Report | Settlement/source transaction ledger | Search and role scope | Transaction date/number/type/action/nature, investor/PAN, folio, scheme, amount, units, NAV, source/origin, BSE ID, broker/EUIN and source-specific fields | CSV, XLSX through Grid.js pattern | All roles scoped |
| Distributor Master | Distributor hierarchy and operational master | Search; role scope | Name, ARN, PAN, mobile/email, EUIN, RM, parent distributor/ARN, status, dates plus address/bank/GST fields in data payload | CSV, XLSX | Admin; RM assigned distributors |
| RM Master | RM/branch master | Search | Name, employee code, branch/code/city/state, email, status, dates plus address/bank/GST fields in payload | CSV, XLSX | Admin |
| Scheme Master | Full scheme execution master | Search | Scheme/code/RTA/ISIN/type/category/AMC, purchase/redemption limits/multiples/cutoffs, SIP/STP/SWP/switch flags, dates, settlement, exit load, lock-in, partner codes | CSV, XLSX | Authenticated |
| Bank Master | Investor bank accounts | Search; role scope | Investor, PAN, bank, account, IFSC, account type, branch, default flag | CSV, XLSX | All roles scoped |
| Nominee Master | Investor nominee details | Search; role scope | Investor/PAN, nominee, relationship/percentage/DOB, guardian, nominee PAN, address/contact and ID fields | CSV, XLSX | All roles scoped |
| BSE Order Status | Live BSE order report | From/to date; search | Order No, Trans No, Client Code, Scheme Code, Type, Buy/Sell, Order Value, Status, Remarks | CSV, XLSX | Authenticated |
| BSE Allotment Statement | Live BSE allotment report | From/to date; search | Order No, Trans No, Client Code, Scheme Code, Folio, Units, Amount, NAV, Date | CSV, XLSX | Authenticated |
| BSE Redemption Statement | Live BSE redemption report | From/to date; search | Order No, Trans No, Client Code, Scheme Code, Folio, Units, Amount, NAV, Date | CSV, XLSX | Authenticated |
| Order Book | Operational local orders | Search, status filter, role scope | Date, order ref, investor, scheme, type, amount, status, remarks, BSE ref | CSV, XLSX, PDF | All roles scoped |
| Portfolio Investor List | Find investor portfolios | Search by name/PAN | Investor, PAN, distributor, total AUM, action | Screen only | Admin/RM/distributor scoped |
| Investor Portfolio Dashboard | AUM and folio summary | Investor; report dates/type | Summary cards; folio, AMC, invested value, current value, gain/loss; allocation charts | PDF reports via selected type | Hierarchy access/self |
| Wealth Report | Consolidated portfolio snapshot | Investor; optional report dates | Investor/company header, holdings, invested/current value, gains and allocation | PDF | Hierarchy access/self |
| P&L Report | Portfolio profit/loss | Investor; optional report dates | Holdings/transactions with invested/current value and gain/loss | PDF | Hierarchy access/self |
| Capital Gain Report | Gain classification | Investor; date range | Scheme/folio/redemption or gain rows, short/long term sections and totals | PDF | Hierarchy access/self; calculation requires validation |
| Transaction Statement | Investor transaction history | Investor; date range | Date, scheme, folio, type, amount, units, NAV and balance-style details | PDF | Hierarchy access/self |
| Folio Detail | One-folio valuation/history | Folio number | Value, units, NAV, gain/loss, transactions and SIP amount | Screen | Hierarchy access/self |
| SIP Dashboard | SIP portfolio and due/failure insights | Role scope | SIP identity, investor/scheme, amount/frequency, status, next installment and installment metrics | Screen/API | Authenticated scoped |
| Payout List/Detail | Distributor payout summary and source rows | Import/month and role scope | Distributor/category, AUM, gross, share, payable, status; source transactions | Screen | Admin/RM/distributor scoped |
| Payout Report | Monthly distributor payout extract | Brokerage import | Distributor, broker code, ARN, PAN, total AUM, category, gross brokerage, share %, payable, status | XLSX | Admin |
| AMC Payout Report | Brokerage/payable by AMC | Brokerage import | AMC, gross brokerage, payable amount | XLSX | Admin |
| Brokerage Transaction Export | Raw/mapped brokerage rows | Brokerage import | Date, source, investor, folio, scheme, amount, brokerage, mapping status/distributor/remark | XLSX | Admin |
| Investor Brokerage Analytics | Attribute brokerage by investor/hierarchy | Brokerage import | Investor, PAN, direct flag, RM code/name, distributor code/name, total brokerage | Screen, XLSX | Admin |
| RM/Distributor Brokerage Dashboard | Aggregated brokerage totals | Brokerage import | RM or distributor code/name and total earned; summary cards | Screen | Admin |
| Scheme Master Export | Operational scheme master download | None / current master | Scheme master fields defined by export utility | File download (spreadsheet/CSV depending view implementation) | Admin |
| Goal Progress | Goal funding progress | Role scope | Goal/category/target date/target/current/progress/investor; detail allocations by scheme/folio/value/% | Screen | Goal owner/hierarchy |
| External Holdings | CAS-extracted off-platform holdings | Role/CAS scope | Scheme, folio, units, NAV/value and statement source fields | Screen | Admin/distributor/investor scoped |
| RTA Import/Failed Records | Operational ingestion status | Recent files/status | File/source/status/count/error and failed row reason/raw fields | Screen/error file | Operations/Admin intended |

## Export and calculation observations

- Grid reports export the currently loaded JavaScript data and typically ignore pagination only because the full dataset is embedded.
- BSE reports call the external service at request time.
- Server-side PDF reports use ReportLab.
- Capital-gain/P&L generator comments explicitly describe simplified or placeholder gain logic in portions of the implementation. These reports must be mathematically certified before migration.
- There is no immutable report snapshot/audit table; rerunning a report can produce different results as masters/NAVs change.

