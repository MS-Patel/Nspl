# Legacy Automation Analysis

## Scheduling architecture

The only checked-in operating-system schedule is `schedular.bat`, intended for Windows Task Scheduler. It activates the virtual environment and runs `python manage.py run_daily_jobs`, appending output to `logs/scheduler_log.txt`. No cron definition, Celery Beat schedule, queue broker configuration or deployment scheduler manifest was found.

## Daily orchestration

`run_daily_jobs` runs sequentially:

1. `sync_bse_reports --days 1`
2. `fetch_rta_emails`
3. `update_navs`
4. `update_holding_values`

If any step raises to the wrapper, later steps do not run. Individual commands often swallow/log exceptions, so the wrapper may report success despite partial failure.

## Command inventory

| Command | Function | Trigger/status |
|---|---|---|
| `run_daily_jobs` | BSE sync → RTA email → NAV → valuation | Scheduled by checked-in Windows batch |
| `sync_bse_reports` | Pull BSE order/allotment/redemption reports | Included daily; manual with day range |
| `sync_historical_orders` | Month-chunk historical BSE allotment matching | Manual |
| `fetch_rta_emails` | IMAP fetch, attachment extraction/import, archive successful mail | Included daily |
| `import_historical_rta` | Import files from historical RTA directory | Manual |
| `update_holding_values` | Apply latest NAV to all holdings | Included daily |
| `update_navs` / `fetch_navs` | Fetch AMFI daily NAV | Included daily / duplicate alias |
| `update_bse_navs` | Scrape/fetch BSE NAV for date | Present but commented out of daily chain |
| `import_schemes` | Import pipe-delimited BSE scheme master | Manual |
| `import_bse`, `import_rta`, `import_amfi` | Source mapping imports | Manual |
| `import_amfi_schemes`, `import_karvy_schemes` | Fuzzy mapping/enrichment | Manual |
| `import_historical_navs` | Fetch per-scheme history from external API | Manual |
| `sync_mfdata` | Enrich AMC/scheme/holdings/ratios from mfdata source | Manual and rate-limited |
| `generate_missing_sip_installments` | Backfill installment schedule | Manual |
| `recalculate_sip_dates` | Refresh next installment | Manual |
| `track_sip_installments_daily` | Update upcoming/triggered/failure states | Named daily but not in scheduler |
| `reconcile_sip_transactions` | Link RTA transactions to expected SIP installments | Manual; called by one Celery task |
| `update_sip_statuses` | Derive SIP master state from installments | Manual |
| `send_sip_alerts` | Send SMS before upcoming SIP | Manual; not in scheduler |
| `calculate_payouts` | Calculate monthly distributor commission and optional XLSX | Manual; UI has a separate import/calc flow |
| `cleanup_old_rta_files` | Delete old records and physical/error files | Duplicate command exists in core and reconciliation; not scheduled |
| `notify_maintenance` | Bulk maintenance email | Manual |
| `change_bse_password` | Change BSE API password | Manual operational tool |
| `update_nominee_flags` | Batch BSE nominee flag correction | Manual |
| `import_old_bse_data` | Legacy clients/mandates CSV import | One-time/manual |

## Background jobs

| Mechanism | Usage | Assessment |
|---|---|---|
| Celery `shared_task` | `reconcile_rta_file`, `reconcile_pending_orders` | Definitions exist; pending-order task is a placeholder and no beat schedule is present |
| Raw Python thread | RTA upload parsing | Runs inside web process; no durability/retry after process restart |
| Raw Python thread | CAS PDF parsing | Runs inside web process; closes DB connections but remains non-durable |
| ThreadPoolExecutor | BSE status sync for multiple Orders | Synchronous request path with up to 10 workers |
| OS scheduler | Daily command batch | Only explicit production schedule in repository |

## Imports

- User/RM/distributor CSV bulk imports.
- BSE/AMFI/RTA/Karvy product masters and mappings.
- RTA transaction DBF/CSV/email attachments.
- Monthly brokerage CAMS DBF and Karvy CSV.
- Folio-to-distributor mapping CSV.
- Password-protected CAS PDF.
- Historical BSE client/mandate CSV.

## Exports

- Client-side Grid.js CSV/XLSX and Order Book PDF.
- Portfolio Wealth, P&L, Capital Gain and Transaction Statement PDFs.
- Payout, AMC payout, brokerage transaction and investor analytics XLSX.
- Scheme master export and sample import templates.
- Failed/error RTA files.

## Notifications

- OTP login SMS with expiry.
- Upcoming SIP SMS command.
- Scheduled-maintenance email command.
- UI messages for synchronous processing.
- No persistent notification queue, delivery status table or retry policy was found.

## Operational gaps

- SIP commands, cleanup and maintenance jobs are not in the visible schedule.
- Celery definitions do not establish that workers/beat run in production.
- Raw threads can lose work.
- Daily-job observability is a text log, not a job-run ledger.
- Duplicate/overlapping NAV, cleanup and payout command paths increase operator ambiguity.
- No alerting/escalation when imports, BSE sync or RTA mailbox processing fail.

