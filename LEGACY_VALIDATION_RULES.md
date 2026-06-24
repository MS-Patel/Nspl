# Legacy Validation Rules

## Investor validation

| Rule | Enforcement point | Notes |
|---|---|---|
| PAN format `AAAAA9999A` | Form regex and BSE readiness service | Uppercase structure required |
| PAN uniqueness | Database and form lookup against User + InvestorProfile | Existing profile excluded on edit |
| Mobile format | Form/BSE readiness | BSE readiness requires Indian 10-digit number beginning 6–9 |
| Pincode | Form/BSE readiness | Six digits; BSE readiness rejects leading zero |
| Email | Django email field/BSE readiness | Profile or linked User email is accepted for BSE |
| Minor investor | Investor form/BSE readiness | Guardian name/PAN required; tax status must be minor; BSE readiness also needs guardian relationship |
| NRI | BSE readiness | Foreign address line, city, country and pincode required for NRI tax statuses |
| Demat | BSE readiness | Depository and DP/client IDs required |
| Hierarchy | View/form querysets | RM/Distributor/Investor choices are role-scoped; some direct RM/Branch fields can still diverge |
| BSE submission | `validate_investor_for_bse` | Bank, nomination and detailed address/compliance checks run before UCC |

## PAN and KYC validation

- CVL PAN inquiry requires PAN input and authenticates through CVL SOAP.
- BSE PAN search returns external name/status/remarks.
- Local `kyc_status` can be toggled manually; this is not the same as authoritative KRA status.
- NDML registration/modification constructs a large XML payload with several fixed/default codes; provider response controls success.
- PAN check endpoints should be treated as operational tools, not proof that all onboarding fields are valid.

## Bank and folio validation

- IFSC regex: four letters + `0` + six alphanumeric characters.
- Bank account is mandatory for BSE readiness; account number and IFSC must be present.
- Bank accounts are unique by investor + BSE bank slot/index.
- Mandate bank choices are restricted to the selected investor.
- Folio choices are restricted to selected investor and, when scheme is known, same AMC.
- Normalized Folio uniqueness is investor + AMC + folio number.
- Holding uniqueness is investor + scheme + folio number.
- Dedicated redemption validates against current holding value/units.
- No universal folio checksum/external verification exists.

## Nominee validation

- Blank nominee rows are ignored.
- If any nominees are supplied, percentages must total exactly 100%.
- Minor nominee requires guardian name and PAN.
- BSE V183 readiness requires nominee address, city, pincode, country and relationship.
- When nomination is opted in, auth mode plus nominee ID type/number, email and mobile are mandatory.
- Order, switch and SIP submission are blocked while nomination auth is pending.
- Opt-out flow can modify UCC and bulk-set BSE nominee flags.

## Purchase and transaction validation

- Purchase amount is required.
- Amount must meet scheme minimum and, when non-zero, maximum purchase amount.
- Accessible investor choices are role-scoped.
- Existing folio is same investor/same AMC.
- Scheme metadata contains purchase/redemption flags, cutoffs and multiples; not all are enforced server-side.
- No exposure limit, risk-profile limit, cut-off-time control, maker-checker or large-order splitting is implemented.

## Redemption validation

- Mode must be amount, units or all.
- Amount/units must be positive.
- Amount cannot exceed cached current holding value.
- Units cannot exceed cached holding units.
- “All” sets the all-redeem flag and ignores quantity/value.
- Scheme minimum redemption amount/quantity, multiples, lock-in/free-unit constraints and cut-off time are not comprehensively enforced in the form.

## Switch validation

- Target scheme is mandatory.
- Source and target must belong to the same AMC.
- Mode must be amount, units or all; positive value required except all.
- Scheme switch-allowed flag is exposed to UI metadata, but server-side form validation does not explicitly reject a disabled source/target.
- Available source holding value/units are not explicitly checked in the generic switch form.

## SIP validation

- Scheme must allow SIP.
- Approved mandate required.
- Frequency, start date and installment count required.
- Parameter mapping uses scheme/SIP/master values and EUIN fallback.
- No form-level minimum SIP amount, installment-count range, valid installment-day calendar, mandate-limit comparison or start-date lead-time validation was found.
- Lifecycle commands infer status from installment records and link RTA transactions using date/amount/folio signals.

## Mandate validation

- UI restricts type to e-mandate/net banking.
- Investor and bank are role/investor scoped.
- Defaults: start today, end approximately 39 years later.
- SIP queryset only exposes APPROVED mandates.
- Missing validations: positive amount limit, end after start, limit ≥ SIP amount, duplicate active mandate prevention and bank-account verification.

## Brokerage validation

- Month input must be `YYYY-MM`.
- Only one `BrokerageImport` per month/year.
- CAMS file extension `.dbf`; Karvy file extension `.csv`.
- Folio mapping import requires `folio_number` and broker code/ARN.
- Unmapped source rows are retained for correction/reprocessing.
- Category name is unique; no explicit overlap validation for AUM category ranges was found.
- Payout arithmetic uses mapped source rows and share percentage; no maker-checker/payment authorization was found.

## File/import validation

- Investor/distributor/RM imports normalize headers and capture row errors, but several create-or-update paths can leave partial records.
- RTA parser selection depends on source/file format; failed rows are persisted.
- Transaction fingerprinting is the primary duplicate defense.
- CAS requires a password but parser coverage is incomplete.

## Validation gaps that must be preserved as lessons, not copied as behavior

1. Scheme-master rules are richer than execution enforcement.
2. Cached holding values are used for redemption checks and can be stale.
3. Manual KYC toggle can diverge from provider state.
4. Hierarchy is represented through multiple nullable paths.
5. External responses are often treated as strings with provider-specific positional parsing.
6. Several validations occur only immediately before BSE submission, not during initial data entry.

