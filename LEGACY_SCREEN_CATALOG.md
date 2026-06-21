# Legacy URL and Screen Catalog

## Reading notes

- Roles are derived from mixins, view querysets and form scoping, not production telemetry.
- “Hidden” means not linked in the normal sidebar or is an API/action/admin route.
- The final website catch-all serves the React shell for any unmatched non-static/media path, which can mask missing routes.

## Platform, authentication and profile

| URL | View | Purpose | Access roles | Navigation path |
|---|---|---|---|---|
| `/` and unmatched paths | `ReactAppView` | React portal shell | Public/session-dependent | Direct / SPA |
| `/legacy/login/` | `CustomLoginView` | Legacy password login | Public | Direct |
| `/login/` | `ReactAppView` | New login shell | Public | Direct |
| `/logout/` | `CustomLogoutView` | End session | Authenticated | Header → Logout |
| `/users/otp/send/` | `SendOTPView` | Generate/send OTP | Public endpoint | Login workflow (hidden) |
| `/users/otp/login/` | `VerifyOTPLoginView` | Verify OTP and login | Public endpoint | Login workflow (hidden) |
| `/users/api/auth/login/` | `APILoginView` | JSON session login | Public API | SPA (hidden) |
| `/users/api/auth/register/` | `APIRegisterDistributorView` | JSON distributor registration | Public API | SPA (hidden) |
| `/users/api/auth/status/` | `APIAuthStatusView` | Session/user status | Public/session API | SPA (hidden) |
| `/users/api/auth/change-password/` | `APIPasswordChangeView` | JSON password change | Authenticated | SPA (hidden) |
| `/profile/` | `ProfileView` | Role-specific profile | All authenticated | Header → Profile |
| `/profile/edit/` | `ProfileEditView` | Edit permitted profile fields | All authenticated | Profile → Edit |
| `/password-change/` | `UserPasswordChangeView` | Change password | Authenticated | Header / forced-change |
| `/password-reset/` | `UserPasswordResetView` | Request reset email | Public | Login |
| `/password-reset/done/` | Django reset done view | Reset request confirmation | Public | Password reset |
| `/reset/<uidb64>/<token>/` | Django reset confirm view | Set new password | Token holder | Email link |
| `/reset/<uidb64>/set-password/` | Same confirm view | Alternate reset path | Token holder | Email link |
| `/reset/done/` | Django reset complete view | Reset completion | Public | Password reset |
| `/maintenance/` | `maintenance_view` | Maintenance message | Public | Middleware redirect |
| `/sw.js`, `/manifest.json` | `TemplateView` | PWA assets | Public | Hidden |

## Dashboards

| URL | View | Purpose | Access roles | Navigation path |
|---|---|---|---|---|
| `/dashboard/admin/` | `AdminDashboardView` | Global counts, orders, SIPs | Admin | Dashboard |
| `/dashboard/rm/` | `RMDashboardView` | Assigned hierarchy summary | RM | Dashboard |
| `/dashboard/distributor/` | `DistributorDashboardView` | Own investors/orders/AUM/SIPs | Distributor | Dashboard |
| `/dashboard/investor/` | `InvestorDashboardView` | Own portfolio, orders and SIPs | Investor | Dashboard |

## Branch, RM, distributor and investor management

| URL | View | Purpose | Access roles | Navigation path |
|---|---|---|---|---|
| `/users/branch/` | `BranchListView` | Branch list | Admin | Masters → Branches |
| `/users/branch/create/` | `BranchCreateView` | Create branch | Admin | Branch list → Add |
| `/users/branch/<pk>/update/` | `BranchUpdateView` | Edit branch | Admin | Branch list → Edit |
| `/users/branch/<pk>/delete/` | `BranchDeleteView` | Delete branch | Admin | Branch list → Delete |
| `/users/rm/` | `RMListView` | RM list | Admin | Masters → RMs |
| `/users/rm/create/` | `RMCreateView` | Create RM/profile | Admin | RM list → Add |
| `/users/rm/<pk>/update/` | `RMUpdateView` | Edit RM | Admin | RM list → Edit |
| `/users/rm/upload/` | `RMUploadView` | Bulk import RMs | Admin | Uploads / hidden from some nav variants |
| `/users/rm/upload/sample/` | `DownloadRMSampleView` | Download sample CSV | Admin | RM upload |
| `/users/distributor/` | `DistributorListView` | Scoped distributor list | Admin, RM | Masters → Distributors |
| `/users/distributor/create/` | `DistributorCreateView` | Create distributor | Admin, RM | Distributor list → Add |
| `/users/distributor/<pk>/update/` | `DistributorUpdateView` | Edit permitted distributor | Admin, RM | Distributor list → Edit |
| `/users/distributor/upload/` | `DistributorUploadView` | Bulk import distributors | Admin | Uploads → Distributors |
| `/users/distributor/upload/sample/` | `DownloadDistributorSampleView` | Sample import file | Admin | Distributor upload |
| `/users/investor/` | `InvestorListView` | Scoped investor list | Admin, RM, Distributor, Investor | Investors |
| `/users/investor/create/` | `InvestorCreateView` | Legacy create workflow | Admin, RM, Distributor | Investor list → Add |
| `/users/investor/onboard/` | `InvestorCreateView` | Wizard alias | Admin, RM, Distributor | Investor list → Onboard |
| `/users/investor/<pk>/` | `InvestorDetailView` | Investor, banks, nominees, mandates, BSE actions | Hierarchy owner or self | Investor list → Detail |
| `/users/investor/<pk>/update/` | `InvestorUpdateView` | Edit investor and inline children | Hierarchy owner or self with disabled mapping fields | Investor detail → Edit |
| `/users/investor/<pk>/push-bse/` | `PushToBSEView` | Validate and create/modify UCC | Hierarchy access; action route | Investor detail → Push BSE |
| `/users/investor/<pk>/fatca-upload/` | `FATCAUploadView` | Send FATCA to BSE | Hierarchy access; action route | Investor detail |
| `/users/investor/<pk>/trigger-auth/` | `TriggerNomineeAuthView` | Trigger nominee authentication | Hierarchy access; action route | Investor detail |
| `/users/investor/<pk>/opt-out-nominee/` | `OptOutNomineeView` | Modify UCC/nominee flag | Hierarchy access; action route | Investor detail |
| `/users/investor/<pk>/toggle-kyc/` | `ToggleKYCView` | Toggle local KYC flag | Authenticated action; intended operations | Investor detail |
| `/users/investor/upload/` | `InvestorUploadView` | Bulk investor import | Admin | Uploads → Investors |
| `/users/investor/upload/sample/` | `DownloadInvestorSampleView` | Sample import file | Admin, RM | Investor upload |
| `/users/investor/mapping/` | `DistributorMappingView` | Map investors to distributors | Admin, RM | Hidden/action utility |
| `/users/investor/rm-mapping/` | `RMMappingView` | Map investors/distributors to RM | Admin, RM | Hidden/action utility |

## Product master and explorer

| URL | View | Purpose | Access roles | Navigation path |
|---|---|---|---|---|
| `/explore/` | `SchemeExplorerView` | Search/filter schemes | Authenticated | Transactions → Explore |
| `/schemes/` | `SchemeListView` | Scheme master list | Authenticated; admin controls exposed | Masters → Schemes |
| `/schemes/<pk>/` | `SchemeDetailView` | Product detail/performance | Authenticated | Explorer/list → Detail |
| `/schemes/<pk>/edit/` | `SchemeUpdateView` | Edit scheme flags/limits | Admin | Scheme detail/list → Edit |
| `/schemes/upload/` | `SchemeUploadView` | Import scheme master | Admin | Uploads → Schemes |
| `/schemes/upload/sample/` | `DownloadSchemeSampleView` | Scheme sample file | Admin | Scheme upload |
| `/navs/upload/` | `NAVUploadView` | Import NAV data | Admin | Uploads → NAV |
| `/navs/upload/sample/` | `DownloadNAVSampleView` | NAV sample file | Admin | NAV upload |
| `/amc/` | `AMCMasterView` | AMC list/active state | Admin | Masters → AMC |
| `/amc/<pk>/toggle/` | `toggle_amc_status` | Activate/deactivate AMC | Admin action | AMC list |
| `/amc/<pk>/update/` | `update_amc_name` | Inline AMC name update | Admin action | AMC list |
| `/schemes/export/master/` | `DownloadSchemeMasterReportView` | Export scheme master | Admin | Scheme list → Export |

## Orders, mandates, SIPs and portfolios

| URL | View | Purpose | Access roles | Navigation path |
|---|---|---|---|---|
| `/order/create/` | `order_create` | Purchase/switch/SIP order form | All authenticated with scoped investor choices | Transactions / Order list → New |
| `/order/list/` | `order_list` | Scoped order book and exports | All authenticated | Transactions → Orders |
| `/api/folios/` | `get_investor_folios` | Investor folio JSON | Authenticated | Order form (hidden) |
| `/api/metadata/` | `get_order_metadata` | Scheme/filter/limit JSON | Authenticated | Order form (hidden) |
| `/holdings/` | `PortfolioInvestorListView` | Investors with AUM | Admin, RM, Distributor; investor effectively own | Transactions → Holdings |
| `/portfolio/<investor_id>/` | `InvestorPortfolioView` | Portfolio dashboard | Hierarchy access/self | Holdings → View |
| `/folio/<folio_number>/` | `FolioDetailView` | Folio valuation and transactions | Hierarchy access/self | Portfolio → Folio |
| `/redemption/create/<holding_id>/` | `RedemptionCreateView` | Redeem holding | Hierarchy access/self | Portfolio/holding → Redeem |
| `/mandate/create/` | `MandateCreateView` | Register mandate | All authenticated with scoped investors | Investor detail / order workflow |
| `/mandate/<pk>/retry/` | `MandateRetryView` | Retry TEMP/PENDING submission | Hierarchy access | Investor detail |
| `/mandate/<pk>/auth/` | `mandate_authorize` | Redirect to BSE authorization | Hierarchy access | Investor detail |
| `/sip-dashboard/` | `SIPDashboardView` | SIP summary and schedules | Authenticated, role scoped | Transactions → SIP Dashboard |
| `/sip/<sip_id>/insights/` | `SIPInsightsView` | SIP metrics/JSON | Authenticated API; object access should be verified | SIP dashboard (hidden) |
| `/sip/upcoming/` | `UpcomingSIPInstallmentsView` | Upcoming installment JSON | Authenticated API; role scoped in implementation | Dashboard/SIP (hidden) |
| `/portfolio/<id>/export/wealth-report/` | `ExportWealthReportView` | Wealth PDF | Hierarchy access/self | Portfolio → Export |
| `/portfolio/<id>/export/pl-report/` | `ExportPLReportView` | P&L PDF | Hierarchy access/self | Portfolio → Export |
| `/portfolio/<id>/export/capital-gain/` | `ExportCapitalGainReportView` | Capital-gain PDF | Hierarchy access/self | Portfolio → Export |
| `/portfolio/<id>/export/transaction-statement/` | `ExportTransactionStatementView` | Transaction statement PDF | Hierarchy access/self | Portfolio → Export |

## RTA reconciliation

| URL | View | Purpose | Access roles | Navigation path |
|---|---|---|---|---|
| `/reconciliation/upload/` | `upload_rta_file` | Upload/process RTA file and show recent imports | Login required; intended Admin/operations | Uploads → RTA |
| `/reconciliation/failed-records/` | `FailedRTARecordListView` | List parser/mapping failures | No explicit login mixin visible; intended Admin | Hidden operational screen |
| `/reconciliation/failed-records/retry/` | `RetryFailedRTARecordView` | Bulk retry failures | No explicit login mixin visible; intended Admin | Failed records |
| `/reconciliation/failed-records/retry/<pk>/` | Same view | Retry one record | No explicit login mixin visible; intended Admin | Failed records |

## Payouts and brokerage

| URL | View | Purpose | Access roles | Navigation path |
|---|---|---|---|---|
| `/payouts/dashboard/` | `PayoutDashboardView` | Payout summary | Admin, RM, Distributor scoped | Payouts |
| `/payouts/upload/` | `BrokerageUploadView` | Upload monthly brokerage | Admin | Payouts → Upload |
| `/payouts/import-list/` | `BrokerageImportListView` | Import batches | Admin | Hidden / Payout operations |
| `/payouts/import/<pk>/` | `BrokerageImportDetailView` | Rows, mapping state and AJAX data | Admin | Import list → Detail |
| `/payouts/import/<pk>/reprocess/` | `ReprocessImportView` | Retry mapping/calculation | Admin action | Import detail |
| `/payouts/list/` | `PayoutListView` | Scoped payouts | Admin, RM, Distributor | Payouts → List |
| `/payouts/detail/<pk>/` | `PayoutDetailView` | Payout and source rows | Scoped Admin/RM/Distributor | Payout list |
| `/payouts/import/<pk>/export/` | `ExportPayoutReportView` | Distributor payout XLSX | Admin | Import detail → Export |
| `/payouts/import/<pk>/export-amc/` | `ExportAMCPayoutReportView` | AMC brokerage/payable XLSX | Admin | Import detail → Export |
| `/payouts/import/<pk>/export-transactions/` | `ExportTransactionReportView` | Brokerage rows XLSX | Admin | Import detail → Export |
| `/payouts/import/<pk>/analytics/` | `InvestorAnalyticsDashboardView` | Investor/RM/distributor brokerage analytics | Admin | Import detail → Analytics |
| `/payouts/import/<pk>/analytics/export/` | `ExportInvestorAnalyticsView` | Analytics XLSX | Admin | Analytics → Export |
| `/payouts/categories/` | `DistributorCategoryListView` | Payout share categories | Admin | Hidden/configuration |
| `/payouts/categories/add/` | `DistributorCategoryCreateView` | Add category/range/share | Admin | Category list |
| `/payouts/categories/<pk>/edit/` | `DistributorCategoryUpdateView` | Edit category | Admin | Category list |
| `/payouts/categories/<pk>/delete/` | `DistributorCategoryDeleteView` | Delete category | Admin | Category list |
| `/payouts/folio-mappings/` | `FolioMappingListView` | Folio attribution overrides | Admin | Hidden operational screen |
| `/payouts/folio-mappings/import/` | `FolioMappingImportView` | Import override CSV | Admin | Folio mappings |

## Analytics

| URL | View | Purpose | Access roles | Navigation path |
|---|---|---|---|---|
| `/goals/` | `GoalListView` | Scoped goals | Admin, Distributor, Investor; RM handling limited | Analytics → Goals |
| `/goals/create/` | `GoalCreateView` | Create goal/holding allocations | Admin, Distributor, Investor | Goal list |
| `/goals/<pk>/` | `GoalDetailView` | Goal progress/mappings | Owner/hierarchy test | Goal list |
| `/goals/<pk>/update/` | `GoalUpdateView` | Edit goal/mappings | Owner/hierarchy test | Goal detail |
| `/goals/<pk>/delete/` | `GoalDeleteView` | Delete goal | Owner/hierarchy test | Goal detail |
| `/cas/upload/` | `CASUploadView` | Upload encrypted CAS | Admin, Distributor, Investor | Analytics → CAS |
| `/cas/list/` | `CASListView` | CAS processing history | Role scoped | Analytics → CAS |
| `/cas/holdings/` | `ExternalHoldingListView` | Parsed external holdings | Role scoped | CAS list / hidden |

## Integration tools

| URL | View | Purpose | Access roles | Navigation path |
|---|---|---|---|---|
| `/integration/tools/pan-check/` | `BSEPanCheckToolView` | PAN/KRA check form | Authenticated | Utilities → PAN Check |
| `/integration/api/pan-check/` | `CheckPANStatusView` | CVL PAN JSON call | Plain API view; intended authenticated tool | PAN tool (hidden) |
| `/integration/api/bank-details/` | `GetBankDetailsView` | IFSC lookup | Plain API view | Forms (hidden) |
| `/integration/tools/ndml-kyc-registration/` | `NDMLRegistrationToolView` | NDML registration UI | Authenticated | KYC → Registration |
| `/integration/tools/ndml-kyc-status/` | `NDMLKYCStatusListView` | Investors and NDML state | Authenticated | KYC → Status |
| `/integration/tools/ndml-kyc-modification/` | `NDMLModificationToolView` | NDML modification UI | Authenticated | KYC → Modification |
| `/integration/api/ndml/register/` | `NDMLRegistrationView` | Register KYC XML | Login required | NDML tool (hidden) |
| `/integration/api/ndml/inquiry/` | `NDMLInquiryView` | PAN inquiry | Login required | NDML status (hidden) |
| `/integration/api/ndml/download/` | `NDMLDownloadView` | Download KYC details | Login required | NDML status (hidden) |
| `/integration/api/ndml/modify/` | `NDMLModificationView` | Submit modification | Login required | NDML modification (hidden) |

## Reports

| URL | View | Purpose | Access roles | Navigation path |
|---|---|---|---|---|
| `/reports/` | `ReportDashboardView` | Report menu | Authenticated | Reports |
| `/reports/investors/` | `InvestorReportView` | Investor master | All roles, scoped | Reports → Investors |
| `/reports/mandates/` | `MandateReportView` | Mandate master/status | All roles, scoped | Reports → Mandates |
| `/reports/transactions/` | `TransactionReportView` | Local Order report | All roles, scoped | Reports → Transactions |
| `/reports/rta-transactions/` | `RTATransactionReportView` | RTA settlement ledger | All roles, scoped | Report route exists; not in primary sidebar |
| `/reports/masters/distributor/` | `MasterReportView` | Distributor master | Admin, RM | Reports dashboard/hidden |
| `/reports/masters/rm/` | `MasterReportView` | RM master | Admin | Reports dashboard/hidden |
| `/reports/masters/scheme/` | `MasterReportView` | Scheme master | Authenticated | Reports dashboard/hidden |
| `/reports/masters/bank/` | `MasterReportView` | Investor bank master | Role scoped | Reports dashboard/hidden |
| `/reports/masters/nominee/` | `MasterReportView` | Nominee master | Role scoped | Reports dashboard/hidden |
| `/reports/order-status/` | `OrderStatusReportView` | BSE order status | Authenticated; data role filtering depends on BSE query | Reports → Order Status |
| `/reports/allotment/` | `AllotmentReportView` | BSE allotment | Authenticated | Reports → Allotment |
| `/reports/redemption/` | `RedemptionReportView` | BSE redemption | Authenticated | Reports → Redemption |

## Administration and hidden admin

| URL | View | Purpose | Access roles | Navigation path |
|---|---|---|---|---|
| `/administration/` | `administration.index` | Administration landing | Authenticated | Direct/hidden |
| `/administration/configuration/` | `system_configuration` | Company, mail, KYC, RTA and maintenance settings | Admin/superuser | Administration → Configuration |
| `/admin/` and descendants | Django admin site | Hidden model CRUD and diagnostics | Staff/superuser | Direct/hidden |

