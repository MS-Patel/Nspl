# Legacy Technical Observations

## Strong implementations

- Clear separation between local Order intent and RTA/BSE Transaction evidence.
- BSE provisional transactions do not overwrite confirmed RTA transactions.
- Transaction fingerprinting, failed-row persistence and reprocessing support production reconciliation.
- Rich BSE-ready investor schema including applicants, NRI, demat, bank and nominee details.
- Scheme master carries extensive execution limits and eligibility metadata.
- Role-scoped report querysets use `select_related`/`prefetch_related` in several high-volume paths.
- SIP has expected-installment records, child-order ingestion, alerts and RTA matching.
- Brokerage rows preserve raw data and mapping remarks, allowing operational repair.

## Technical debt and risk areas

| Area | Observation | Risk |
|---|---|---|
| Secrets | Credentials/default secrets in settings, `.env` and plain configuration fields | Credential compromise and difficult rotation |
| Transport security | `verify=False` on BSE HTTP calls | MITM exposure of financial/PII payloads |
| Logging | File-based SOAP/JSON payload logs with incomplete PII masking | Privacy leakage and weak search/retention control |
| External calls | Mixed timeout behavior, synchronous calls from views and page loads | Hung workers and user-visible latency |
| Reliability | Raw threads for RTA/CAS; Celery setup incomplete | Lost work and inconsistent retries |
| Observability | No integration/job-run database log | Hard reconciliation and audit |
| Authorization | Repeated role conditions and inconsistent hierarchy paths | Data leakage or denied legitimate access |
| Exception handling | Broad `except Exception`, silent `pass`, fallback dates/values | Hidden defects and incorrect financial state |
| Reporting | Live queries; PDF capital-gain comments describe placeholder/estimated logic | Regulatory/reporting accuracy risk |
| Data model | Folio and hierarchy duplicated across models | Divergence and mapping burden |
| Scheduling | One Windows batch covers only part of operational lifecycle | Stale SIP, cleanup and alert state |
| Imports | Whole-file pandas/openpyxl processing and many overlapping commands | Memory pressure and operator confusion |
| API parsing | Pipe-position and provider-object assumptions | Fragility when BSE response changes |
| Frontend | Legacy Django UI plus React catch-all; duplicate navigation artifacts | Ambiguous ownership and hidden routes |
| Tests | Many tests use `unittest.TestCase` despite current project rule | Inconsistent test style; inventory task made no code change |

## Duplicate or overlapping logic

- Three near-identical SOAP client initialization methods.
- Repeated role filtering in users, investments, reports, payouts and analytics.
- Duplicate `cleanup_old_rta_files` command.
- `fetch_navs` and `update_navs` overlap; BSE NAV is an additional alternate path.
- Payout calculation exists through UI utilities and a management command.
- Inline Grid.js export utility is copied into report templates despite a shared utility file.
- Legacy and API login/password workflows coexist.
- BSE synchronization occurs in commands and on selected dashboard/detail page loads.

## Hardcoded or provider-specific rules

- BSE flags (`01`, `04`, `06`, `11`), status codes and pipe positions.
- NDML XML includes fixed proof/state/nationality/marital/default values.
- E-mandate end date defaults to roughly 39 years.
- Password initialization from PAN/employee identifiers.
- Windows/IIS paths in scheduler batch.
- Source-specific RTA email subjects/senders and archive behavior.
- Fallback transaction dates use “today” when parsing fails.

## Implemented versus aspirational

- Multi-tier distributor hierarchy is modeled; broad descendant access/pass-through payout logic is not clearly implemented.
- Reconciliation engine classes/tasks include placeholder hooks, while concrete parser/holding reconciliation is implemented elsewhere.
- CAS import exists, but parser comments state incomplete format coverage.
- eSign provider integration is described in architecture but not found.
- Risk profiling is described in architecture but no corresponding implemented model/workflow was found.
- Upload SOAP client exists without a discovered active upload operation.

## Features that should not be copied

- Manual KYC truth override as an authoritative state.
- Synchronous BSE sync on page render.
- Plaintext integration secrets.
- Disabled TLS and broad PII payload logging.
- Estimated/placeholder tax-report calculations.
- Raw background threads for financial-file processing.
- Duplicate folio/hierarchy fields without a canonical identity strategy.
- Catch-all routing that masks missing server routes.

## Verification note

This task intentionally did not run production integrations or mutate data. Findings are based on static code, templates, tests, migrations, commands and configuration inspection. “Used in production” in the matrix therefore means “wired into the apparent production UI/scheduler or core operational flow,” not confirmed telemetry.

