# Legacy Workflow Analysis

## 1. Investor onboarding and UCC creation

**Users:** Admin, RM, Distributor.

**Steps:** Create investor user/profile → assign hierarchy → enter tax/KYC/applicant/address data → add banks and nominees → optional documents → validate PAN/duplicates/minor/nominee allocation → save → run BSE readiness validation → push NEW or MOD UCC → store UCC/BSE remarks → upload FATCA → complete nomination authentication or opt-out.

**Validations:** PAN/mobile/pincode/IFSC formats; unique PAN; minor guardian and minor tax status; NRI foreign address; demat depository IDs; bank required for BSE; nominees total 100%; nominee identity/contact fields for BSE V183.

**Approvals:** Distributor registration has `is_approved`; UCC itself relies on BSE response. Local KYC flag can be manually toggled.

**Exceptions:** BSE network errors remain retryable/pending; detailed BSE remarks are retained. Bulk CSV import captures row errors but may create partial data.

## 2. Purchase

**Steps:** Select accessible investor → transaction type purchase → filter/select scheme → select existing same-AMC folio or new folio → enter amount/payment mode → submit → local Order → BSE placement → status/payment/allotment sync → provisional transaction → RTA confirmation → holding valuation.

**Validations:** Investor queryset by role; scheme minimum/maximum purchase amount; scheme eligibility supplied by metadata; nominee-auth pending blocks BSE call.

**Approvals:** No internal maker-checker. BSE acceptance/payment/allotment are external state gates.

**Exceptions:** BSE business rejection marks REJECTED; connection/system error leaves PENDING with remarks. No automatic resubmission queue.

## 3. Redemption

**Steps:** Open accessible holding → choose amount, units or all → validate against holding → create redemption Order → BSE order → redemption report/RTA transaction → reduce holding.

**Validations:** Hierarchy access; positive value; amount cannot exceed current value; units cannot exceed holding units; all-redeem flag.

**Approvals:** No internal approval; BSE/RTA lifecycle only.

**Exceptions:** Same pending/rejected treatment as purchase. Scheme-level minimum redemption/multiples are present in master data but are not fully enforced in the dedicated redemption form.

## 4. Switch

**Steps:** Select source scheme/folio and target scheme → choose amount, units or all → submit local Order → BSE switch call → follow BSE/RTA legs.

**Validations:** Target required; source and target must share AMC; amount/units positive; all mode zeroes amount/units. Metadata exposes switch eligibility.

**Approvals:** No maker-checker.

**Exceptions:** A single Order points to source and target schemes; settlement leg matching depends on external records.

## 5. Mandate registration

**Steps:** Select investor and their bank → e-mandate type, amount limit and dates → create TEMP local ID → BSE registration → store real mandate ID → authorize through generated URL → status query updates APPROVED/REJECTED.

**Validations:** Role-scoped investor and bank querysets; only net-banking e-mandate offered; SIP only accepts approved mandates.

**Exceptions:** Failed network submission retains TEMP/PENDING and can be retried. Business rejection marks REJECTED.

## 6. SIP registration and servicing

**Steps:** Choose SIP-capable scheme → approved mandate → frequency/start/installment count → create SIP and registration Order → BSE XSIP → generate expected installments → fetch BSE child orders → reconcile RTA transactions → update installment/master status → send upcoming alerts.

**Validations:** SIP allowed, mandate required, frequency/start/installment count required, nominee-auth compliance block.

**Approvals:** Mandate approval is prerequisite; BSE registration activates the SIP.

**Exceptions:** Failed registration remains pending or rejected. Lifecycle commands exist but are not all included in the only visible scheduler script.

## 7. BSE/RTA reconciliation

**Steps:** Fetch BSE status/allotment/redemption → create provisional transactions → fetch/import RTA attachments → identify parser → normalize and fingerprint row → map investor/scheme → replace/confirm evidence and recalculate holding → store failures → retry failed records.

**Validations:** File type/parser recognition, transaction fingerprint deduplication, investor/scheme mapping, required source fields.

**Approvals:** Operational review through failed-record screens; no explicit sign-off state.

**Exceptions:** Bad rows become `FailedRTARecord`; email is not archived when processing errors occur.

## 8. Brokerage processing

**Steps:** Select month/year → upload CAMS DBF and/or Karvy CSV → prevent duplicate month → parse rows → map distributor using broker/folio/source data → calculate gross brokerage/AUM → choose category/share → create Payouts → inspect unmapped rows → import folio mapping → reprocess → export.

**Validations:** Unique month/year; file extensions; distributor/category mapping; missing identifiers remain unmapped.

**Approvals:** Admin-only operational workflow; payout status exists but no payment-authorization workflow was found.

**Exceptions:** Import status/error logs and mapping remarks retained; reprocess can recover after master-data correction.

## 9. NAV and portfolio valuation

**Steps:** Import/fetch AMFI NAVs (optional BSE fetch) → update latest NAV per scheme → recompute holding current value → portfolio/folio dashboards and PDF reports.

**Validations:** Scheme/date NAV uniqueness and mapping.

**Exceptions:** Missing NAV leaves holding unchanged; unmatched schemes are logged.

## 10. Report generation

**Steps:** Open role-scoped report → optional date/search filters → query live models or BSE → Grid.js display → CSV/XLSX client export, or server-side PDF/XLSX export.

**Validations:** Most local reports filter by role; BSE date defaults cover recent/current periods.

**Exceptions:** BSE report failures generally produce empty data and an error message. Some PDF gain/capital-gain logic contains documented approximations.

## 11. Goal planning

**Steps:** Create goal for accessible investor → define target/date/category → allocate percentages to holdings → monitor current allocated value/progress.

**Validations:** Holding queryset is scoped by view; allocation field is 0–100. No aggregate 100% validation was found for goal mappings.

## 12. CAS import

**Steps:** Upload encrypted CAS PDF and password → create CASUpload → background thread parses file → bulk create ExternalHoldings → mark processed/failed.

**Validations:** Investor scope and password input.

**Exceptions:** Errors stored on upload. Parser comments state that complex CAMS/Karvy format handling is placeholder-grade.

