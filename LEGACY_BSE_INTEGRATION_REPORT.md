# Legacy BSE Integration Report

## Integration architecture

The portal uses Zeep SOAP clients for three BSE WSDLs plus direct JSON/HTTP endpoints. WSDLs can be remote or local files under `docs/wsdl/demo`. The configured production branch currently resolves the same local demo WSDL directory, so deployment configuration must be verified independently.

Authentication patterns:

- Order SOAP: `getPassword(UserId, Password, PassKey)` → encrypted password and pass key.
- Upload/query SOAP: `getPassword(UserId, MemberId, Password, PassKey)`.
- Mandate query token: `GetAccessToken` with request type `MANDATE`.
- Some query operations send the configured BSE password directly inside the SOAP parameter object.
- Common UCC/e-mandate/nominee JSON APIs send member/user/password in JSON.
- External calls are retried up to three times for raised exceptions; no circuit breaker exists.

## WSDLs and services

| WSDL / service | Binding | Current usage |
|---|---|---|
| `MFOrder.wsdl` / `MFOrder` | `WSHttpBinding_MFOrderEntry1` | Purchase/redemption order entry, switch, XSIP registration, order authentication |
| `MFUploadService.wsdl` / `MFUploadService` | `WSHttpBinding_IMFUploadService1` | Authentication helper exists; no active business upload call found |
| `StarMFWebService.wsdl` / `StarMFWebService` | `WSHttpBinding_IStarMFWebService1` | MFAPI flags, status/report queries, mandates, child orders, PAN search |

## Endpoint and operation catalog

| Operation / endpoint | Purpose | Request (principal fields) | Response handling | Current usage |
|---|---|---|---|---|
| `getPassword` (Order SOAP) | Obtain encrypted order credential | User ID, configured password, random pass key | Pipe response; code `100` yields token | Before order, switch and XSIP calls |
| `orderEntryParam` | Place purchase or redemption | Member/user credentials, client code, scheme, buy/sell, amount/units, folio, EUIN and reference | Pipe response; code `0` treated as success; echo-format fallback | Purchase and redemption views |
| `switchOrderEntryParam` | Place same-AMC switch | Source/target scheme, client/folio, amount/units/all flag, EUIN and credentials | Pipe response mapped to success/error/exception | Switch branch of generic order form |
| `xsipOrderEntryParam` | Register XSIP | Investor, scheme, amount, dates/frequency/installments, mandate, EUIN and credentials | Pipe response; registration number stored in SIP and Order | SIP registration |
| `MFAPI` flag `06` | Register mandate | Encrypted query password plus pipe-delimited mandate parameter | Code `100`; mandate ID stored | Mandate create/retry |
| E-mandate authorization JSON endpoint | Generate bank authorization URL | Member, user, password, client code, mandate ID, loopback URL | JSON `ResponseString`/`URL` or raw text | Mandate authorization redirect |
| `MandateDetails` | Track mandate status | Member/client/mandate/date range/access token | SOAP object; APPROVED/REJECTED mapped locally | Investor detail sync |
| `ChildOrderDetails` | Fetch XSIP installment child orders | Date, member, client, XSIP registration number, encrypted password | Child rows become local purchase Orders | Dashboard/investor sync |
| Common UCC JSON API (`UCCRegistrationV183`) | Create or modify client | User/member/password, registration type, pipe payload | JSON status `0` success | “Push to BSE” and nominee modification |
| `MFAPI` flag `01` | FATCA upload | Encrypted query password and FATCA pipe payload | Code `100` success | Investor detail FATCA action |
| Nominee flag JSON API | Bulk set nominee flag | Login/member/password, internal ref, request array | JSON status normalized | Management command and opt-out support |
| `AOFPanSearch` | Search PAN/UCC status at BSE | Member, PAN, encrypted password, user | Status, BSE remarks, PAN, investor name | PAN tool |
| `OrderStatus` | Final/current order state | Date range, client/order filters, order type/status, settlement, trans type | SOAP rows shown in report and update local Orders | Reports and daily sync |
| `ProvOrderStatus` | Provisional order status | Same report filters plus trans type/fillers | Raw SOAP object | Client method/tests; limited direct UI use |
| `AllotmentStatement` | Allotted units, amount, NAV, folio | Date range/client/order filters | UI report; provisional Transaction upsert; Folio creation | Reports, page sync and daily job |
| `RedemptionStatement` | Redemption settlement details | Date range/client/order filters | UI report; provisional redemption Transaction upsert | Reports and daily job |
| `MFAPI` flag `11` | Payment status | Client code, order number, `BSEMF` | Pipe result/remarks | Pending-order synchronization |
| `MFAPI` flag `04` | Change BSE password | Old/new/confirm pipe payload | Code `100` success | Manual management command |

## Business flows

### Purchase

Local Order → nominee-auth compliance guard → scheme amount validation → `orderEntryParam` → BSE order ID/status → payment and order-status checks → allotment report → provisional Transaction/Holding → RTA confirmation.

### Redemption

Holding access and value/units validation → local Order with all/amount/units mode → `orderEntryParam` → redemption statement → provisional redemption Transaction → RTA confirmation.

### Switch

Generic order form enforces target scheme and same AMC → `switchOrderEntryParam`. The source/target holdings impact is represented through BSE/RTA records; there is no distinct local two-leg switch model.

### SIP

Approved mandate required → SIP record and registration Order → `xsipOrderEntryParam` → local installment schedule → `ChildOrderDetails` creates purchase child Orders → BSE/RTA synchronization links transactions.

### Mandate

Local temporary ID → `MFAPI(06)` → real mandate ID → e-mandate authorization URL → `MandateDetails` polling → APPROVED/REJECTED.

## Status tracking and source precedence

- BSE allotment/redemption creates or updates provisional `Transaction` rows.
- A non-provisional RTA transaction is not overwritten by BSE synchronization.
- BSE order status updates local `Order`.
- RTA feeds recalculate holdings and are the intended settlement source of truth.
- Fingerprints and BSE order IDs are used to reduce duplicates.

## Integration risks

- TLS certificate verification is disabled for UCC, e-mandate authorization and nominee HTTP calls.
- Several HTTP calls do not specify a timeout.
- API request/response data is written to local log files; masking focuses on passwords, not all PII.
- Credentials/default secrets exist in application settings and configuration fields.
- No persistent integration log, idempotency key registry, dead-letter queue or circuit breaker.
- SOAP status-code expectations vary (`0` vs `100`) and are handled inconsistently.
- Page loads can perform synchronous BSE synchronization using a thread pool, increasing latency and external-service coupling.
- Upload SOAP client is initialized but appears unused.

