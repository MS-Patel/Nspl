# Legacy Security and Permission Model

## Roles

| Role | Intended scope |
|---|---|
| Admin / superuser | Global data, hierarchy, configuration, integrations, imports, payouts and Django admin |
| RM | Assigned distributors plus investors directly assigned to the RM or under those distributors |
| Distributor | Own investors; parent/sub-distributor structure exists but most querysets only include direct ownership |
| Investor | Own profile, portfolio, reports, goals/CAS and technically some transaction/mandate paths |

## Authorization implementation

- Primary control is `User.user_type`, checked in mixins, `test_func`, querysets and ad hoc branches.
- `IsAdminMixin`, `IsRMMixin`, `IsDistributorMixin`, `IsAdminOrRMMixin` and `InvestorAccessMixin` protect user-management views.
- Investment views use `has_access_to_investor`, role-scoped forms and filtered querysets.
- Reports implement role-specific querysets.
- Payout import/configuration/export screens are mostly Admin-only; payout lists are scoped for RM/distributor.
- Django groups and permissions exist through `AbstractUser` but are not the principal business authorization mechanism.
- Django admin is available at `/admin/` to staff/superusers.

## Hierarchy rules

- RM access commonly includes `investor.rm == RM` or `investor.distributor.rm == RM`.
- Distributor access commonly includes only `investor.distributor.user == current user`.
- Admin receives global querysets.
- Investor receives only its linked profile.
- Branch is used for organization and RM assignment, but there is no reusable branch-scope policy layer.
- Parent distributor relationships are modeled but not consistently included in access calculations.

## Authentication

- Legacy Django username/password login.
- React/API login using session authentication.
- OTP send/verify flow by mobile/user.
- Password reset email.
- Forced password change middleware for imported/default-password users.
- Import paths commonly initialize passwords from PAN, employee code or similar known identifiers, with forced change.

## Security controls present

- Django CSRF protection and session authentication.
- Standard Django password validators.
- Login-required mixins/decorators on most business screens.
- Role-scoped querysets for key reports and masters.
- External-service password masking in selected logs.
- BSE readiness/compliance checks before client/order submission.
- Maintenance middleware and force-password-change middleware.

## High-risk findings

1. Default credentials/secrets are present in settings and local environment files. They must be treated as compromised and rotated; values are intentionally not reproduced here.
2. TLS verification is disabled in multiple BSE HTTP integrations.
3. Integration logs can contain PAN, client codes, bank/nominee data and full payload structures; masking is password-focused.
4. Email, NDML and RTA mailbox passwords are stored in plain database character fields and rendered back into password inputs.
5. `AuditLog` exists but no comprehensive audit-writing mechanism was found.
6. Permission logic is duplicated across views; inconsistent RM/direct-investor and sub-distributor handling is possible.
7. Several JSON API endpoints use plain `View` without `LoginRequiredMixin`; security depends on CSRF/session behavior and endpoint-specific code.
8. Public React catch-all can obscure whether a missing legacy route is intentionally public or merely swallowed by the SPA.
9. OTP records have no highlighted rate-limit/attempt-limit strategy in the analyzed flow.
10. Raw background threads process sensitive files inside web workers with local filesystem assumptions.

## Access anomalies to verify before comparison

- Architecture says Investor is view-only, but order and mandate forms include Investor branches and can submit directly.
- Some integration tool APIs lack explicit login mixins even though tool pages require login.
- Reconciliation failed-record class views do not visibly include `LoginRequiredMixin`; URL access should be tested.
- Goal/CAS forms explicitly cover Admin/Distributor/Investor, while RM handling is less consistent.
- Sub-distributor descendants are not systematically included in distributor scope.

## Migration guidance

Preserve the hierarchy semantics and scoped data views, but replace hard-coded role branching with a centralized policy/permission service. Do not migrate plaintext secrets, disabled TLS, PAN-derived initial passwords, payload logging or page-load synchronization behavior.

