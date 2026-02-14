from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
import json
from django.core.serializers.json import DjangoJSONEncoder
from django.db.models import Q
import datetime

from apps.users.models import User, InvestorProfile, DistributorProfile, RMProfile, BankAccount, Nominee
from apps.investments.models import Order, SIP
from apps.reconciliation.models import Transaction
from apps.products.models import Scheme
# from apps.integration.bse_client import BSEStarMFClient # No longer needed for direct calls

class ReportDashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'reports/dashboard.html'

class InvestorReportView(LoginRequiredMixin, TemplateView):
    template_name = 'reports/investor_report.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        # Access Control & Queryset
        if user.user_type == User.Types.ADMIN:
            qs = InvestorProfile.objects.select_related('user', 'distributor', 'branch', 'rm').prefetch_related('bank_accounts', 'nominees').all()
        elif user.user_type == User.Types.RM:
            qs = InvestorProfile.objects.filter(
                Q(rm__user=user) | Q(distributor__rm__user=user)
            ).select_related('user', 'distributor', 'branch', 'rm').prefetch_related('bank_accounts', 'nominees').distinct()
        elif user.user_type == User.Types.DISTRIBUTOR:
            qs = InvestorProfile.objects.filter(distributor__user=user).select_related('user', 'distributor', 'branch', 'rm').prefetch_related('bank_accounts', 'nominees')
        elif user.user_type == User.Types.INVESTOR:
            qs = InvestorProfile.objects.filter(user=user).select_related('user', 'distributor', 'branch', 'rm').prefetch_related('bank_accounts', 'nominees')
        else:
            qs = InvestorProfile.objects.none()

        data = []
        for inv in qs:
            # Flatten Bank Details (Take first or default) - Kept for convenience
            bank = inv.bank_accounts.filter(is_default=True).first()
            if not bank:
                bank = inv.bank_accounts.first()

            # Flatten Nominee (Take first) - Kept for convenience
            nominee = inv.nominees.first()

            row = {
                'id': inv.id,
                'name': inv.user.name or inv.user.username,
                'pan': inv.pan,
                'email': inv.email,
                'mobile': inv.mobile,
                'distributor': inv.distributor.user.name if inv.distributor and inv.distributor.user.name else (inv.distributor.user.username if inv.distributor else ''),
                'kyc_status': "Verified" if inv.kyc_status else "Pending",
                'bank_name': bank.bank_name if bank else '',
                'account_no': bank.account_number if bank else '',
                'ifsc': bank.ifsc_code if bank else '',
                'nominee_name': nominee.name if nominee else '',
                'nominee_relation': nominee.relationship if nominee else '',

                # Added All Other Fields
                'username': inv.user.username,
                'firstname': inv.firstname,
                'middlename': inv.middlename,
                'lastname': inv.lastname,
                'dob': inv.dob.strftime('%Y-%m-%d') if inv.dob else '',
                'gender': inv.get_gender_display(),
                'address_1': inv.address_1,
                'address_2': inv.address_2,
                'address_3': inv.address_3,
                'city': inv.city,
                'state': inv.state,
                'pincode': inv.pincode,
                'country': inv.country,
                'foreign_address_1': inv.foreign_address_1,
                'foreign_address_2': inv.foreign_address_2,
                'foreign_address_3': inv.foreign_address_3,
                'foreign_city': inv.foreign_city,
                'foreign_state': inv.foreign_state,
                'foreign_pincode': inv.foreign_pincode,
                'foreign_country': inv.foreign_country,
                'foreign_resi_phone': inv.foreign_resi_phone,
                'foreign_res_fax': inv.foreign_res_fax,
                'foreign_off_phone': inv.foreign_off_phone,
                'foreign_off_fax': inv.foreign_off_fax,
                'tax_status': inv.get_tax_status_display(),
                'occupation': inv.get_occupation_display(),
                'holding_nature': inv.get_holding_nature_display(),
                'place_of_birth': inv.place_of_birth,
                'country_of_birth': inv.country_of_birth,
                'source_of_wealth': inv.get_source_of_wealth_display(),
                'income_slab': inv.get_income_slab_display(),
                'pep_status': inv.get_pep_status_display(),
                'exemption_code': inv.get_exemption_code_display(),
                'client_type': inv.get_client_type_display(),
                'depository': inv.get_depository_display(),
                'dp_id': inv.dp_id,
                'client_id': inv.client_id,
                'second_applicant_name': inv.second_applicant_name,
                'second_applicant_pan': inv.second_applicant_pan,
                'second_applicant_dob': inv.second_applicant_dob.strftime('%Y-%m-%d') if inv.second_applicant_dob else '',
                'second_applicant_email': inv.second_applicant_email,
                'second_applicant_mobile': inv.second_applicant_mobile,
                'third_applicant_name': inv.third_applicant_name,
                'third_applicant_pan': inv.third_applicant_pan,
                'third_applicant_dob': inv.third_applicant_dob.strftime('%Y-%m-%d') if inv.third_applicant_dob else '',
                'third_applicant_email': inv.third_applicant_email,
                'third_applicant_mobile': inv.third_applicant_mobile,
                'guardian_name': inv.guardian_name,
                'guardian_pan': inv.guardian_pan,
                'paperless_flag': inv.get_paperless_flag_display(),
                'lei_no': inv.lei_no,
                'lei_validity': inv.lei_validity.strftime('%Y-%m-%d') if inv.lei_validity else '',
                'mapin_id': inv.mapin_id,
                'nomination_opt': inv.get_nomination_opt_display(),
                'nomination_auth_mode': inv.get_nomination_auth_mode_display(),
                'ucc_code': inv.ucc_code,
                'nominee_auth_status': inv.get_nominee_auth_status_display(),
                'is_offline': inv.is_offline,
                'date_joined': inv.user.date_joined.strftime('%Y-%m-%d %H:%M') if inv.user.date_joined else '',
                'last_login': inv.user.last_login.strftime('%Y-%m-%d %H:%M') if inv.user.last_login else '',
                'is_active': inv.user.is_active,
            }
            data.append(row)

        context['grid_data_json'] = json.dumps(data, cls=DjangoJSONEncoder)
        return context

class TransactionReportView(LoginRequiredMixin, TemplateView):
    template_name = 'reports/transaction_report.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        # Access Control & Queryset
        if user.user_type == User.Types.ADMIN:
            qs = Order.objects.all()
        elif user.user_type == User.Types.RM:
            qs = Order.objects.filter(
                Q(investor__rm__user=user) | Q(investor__distributor__rm__user=user)
            ).distinct()
        elif user.user_type == User.Types.DISTRIBUTOR:
            qs = Order.objects.filter(investor__distributor__user=user)
        elif user.user_type == User.Types.INVESTOR:
            qs = Order.objects.filter(investor__user=user)
        else:
            qs = Order.objects.none()

        qs = qs.select_related('investor', 'investor__user', 'scheme').order_by('-created_at')

        data = []
        for order in qs:
            txn_type_display = order.get_transaction_type_display()
            # If it is SIP Registration, clarify
            if order.transaction_type == 'SIP':
                txn_type_display = "SIP Registration"

            row = {
                'id': order.id,
                'date': order.created_at.strftime('%Y-%m-%d %H:%M'),
                'ref_no': order.unique_ref_no,
                'investor': order.investor.user.name or order.investor.user.username,
                'scheme': order.scheme.name,
                'type': txn_type_display,
                'amount': round(float(order.amount) if order.amount else 0, 2),
                'status': order.get_status_display(),
                'remarks': order.bse_remarks or '',
            }
            data.append(row)

        context['grid_data_json'] = json.dumps(data, cls=DjangoJSONEncoder)
        return context

class MasterReportView(LoginRequiredMixin, TemplateView):
    template_name = 'reports/master_report.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        report_type = self.kwargs.get('type')
        user = self.request.user
        data = []
        title = "Report"
        columns = [] # To pass column config to JS if needed, but we might hardcode in template for now based on type

        if report_type == 'distributor':
            title = "Distributor Master Report"
            if user.user_type == User.Types.ADMIN:
                qs = DistributorProfile.objects.select_related('user', 'rm', 'rm__user', 'parent', 'parent__user').all()
            elif user.user_type == User.Types.RM:
                qs = DistributorProfile.objects.filter(rm__user=user).select_related('user', 'rm', 'rm__user', 'parent', 'parent__user')
            else:
                 # Distributors/Investors shouldn't see full distributor list usually
                 qs = DistributorProfile.objects.none()

            for dist in qs:
                data.append({
                    'name': dist.user.name or dist.user.username,
                    'arn': dist.arn_number,
                    'pan': dist.pan,
                    'mobile': dist.mobile,
                    'euin': dist.euin,
                    'rm': dist.rm.user.name if dist.rm else '',
                    'status': 'Active' if dist.user.is_active else 'Inactive',
                    'email': dist.user.email,
                    'parent_name': dist.parent.user.name if dist.parent else '',
                    'parent_arn': dist.parent.arn_number if dist.parent else '',

                    # Extended Fields
                    'address': dist.address,
                    'city': dist.city,
                    'state': dist.get_state_display() if hasattr(dist, 'get_state_display') else dist.state,
                    'pincode': dist.pincode,
                    'country': dist.country,
                    'alternate_mobile': dist.alternate_mobile,
                    'alternate_email': dist.alternate_email,
                    'dob': dist.dob.strftime('%Y-%m-%d') if dist.dob else '',
                    'gstin': dist.gstin,
                    'bank_name': dist.bank_name,
                    'account_number': dist.account_number,
                    'ifsc_code': dist.ifsc_code,
                    'account_type': dist.get_account_type_display(),
                    'branch_name': dist.branch_name,

                    'date_joined': dist.user.date_joined.strftime('%Y-%m-%d') if dist.user.date_joined else '',
                    'last_login': dist.user.last_login.strftime('%Y-%m-%d %H:%M') if dist.user.last_login else '',
                })

        elif report_type == 'rm':
            title = "Relationship Manager (RM) Master Report"
            if user.user_type == User.Types.ADMIN:
                qs = RMProfile.objects.select_related('user', 'branch').all()
                for rm in qs:
                    data.append({
                        'name': rm.user.name or rm.user.username,
                        'code': rm.employee_code,
                        'branch': rm.branch.name if rm.branch else '',
                        'email': rm.user.email,
                        'status': 'Active' if rm.user.is_active else 'Inactive',
                        'branch_code': rm.branch.code if rm.branch else '',
                        'branch_city': rm.branch.city if rm.branch else '',
                        'branch_state': rm.branch.state if rm.branch else '',

                        # Extended Fields
                        'address': rm.address,
                        'city': rm.city,
                        'state': rm.get_state_display() if hasattr(rm, 'get_state_display') else rm.state,
                        'pincode': rm.pincode,
                        'country': rm.country,
                        'alternate_mobile': rm.alternate_mobile,
                        'alternate_email': rm.alternate_email,
                        'dob': rm.dob.strftime('%Y-%m-%d') if rm.dob else '',
                        'gstin': rm.gstin,
                        'bank_name': rm.bank_name,
                        'account_number': rm.account_number,
                        'ifsc_code': rm.ifsc_code,
                        'account_type': rm.get_account_type_display(),
                        'branch_name': rm.branch_name,

                        'date_joined': rm.user.date_joined.strftime('%Y-%m-%d') if rm.user.date_joined else '',
                        'last_login': rm.user.last_login.strftime('%Y-%m-%d %H:%M') if rm.user.last_login else '',
                    })
            else:
                 qs = [] # Only Admin sees RM list

        elif report_type == 'scheme':
            title = "Scheme Master Report"
            # All authenticated users can see schemes
            qs = Scheme.objects.select_related('amc', 'category').all()
            for s in qs:
                data.append({
                    'name': s.name,
                    'code': s.scheme_code,
                    'rta_code': s.rta_scheme_code,
                    'isin': s.isin,
                    'category': s.category.name if s.category else '',
                    'amc': s.amc.name,
                    'type': s.scheme_type,
                    'min_purchase': round(float(s.min_purchase_amount), 2),

                    # New Fields (All Scheme Fields)
                    'unique_no': s.unique_no,
                    'amc_scheme_code': s.amc_scheme_code,
                    'amfi_code': s.amfi_code,
                    'scheme_plan': s.scheme_plan,
                    'purchase_allowed': s.purchase_allowed,
                    'purchase_transaction_mode': s.purchase_transaction_mode,
                    'additional_purchase_amount': round(float(s.additional_purchase_amount), 3),
                    'max_purchase_amount': round(float(s.max_purchase_amount), 2),
                    'purchase_amount_multiplier': round(float(s.purchase_amount_multiplier), 2),
                    'purchase_cutoff_time': s.purchase_cutoff_time.strftime('%H:%M') if s.purchase_cutoff_time else '',
                    'redemption_allowed': s.redemption_allowed,
                    'redemption_transaction_mode': s.redemption_transaction_mode,
                    'min_redemption_qty': round(float(s.min_redemption_qty), 3),
                    'redemption_qty_multiplier': round(float(s.redemption_qty_multiplier), 4),
                    'max_redemption_qty': round(float(s.max_redemption_qty), 3),
                    'min_redemption_amount': round(float(s.min_redemption_amount), 2),
                    'max_redemption_amount': round(float(s.max_redemption_amount), 2),
                    'redemption_amount_multiple': round(float(s.redemption_amount_multiple), 4),
                    'redemption_cutoff_time': s.redemption_cutoff_time.strftime('%H:%M') if s.redemption_cutoff_time else '',
                    'is_sip_allowed': s.is_sip_allowed,
                    'is_stp_allowed': s.is_stp_allowed,
                    'is_swp_allowed': s.is_swp_allowed,
                    'is_switch_allowed': s.is_switch_allowed,
                    'start_date': s.start_date.strftime('%Y-%m-%d') if s.start_date else '',
                    'end_date': s.end_date.strftime('%Y-%m-%d') if s.end_date else '',
                    'reopening_date': s.reopening_date.strftime('%Y-%m-%d') if s.reopening_date else '',
                    'face_value': round(float(s.face_value), 2) if s.face_value else '',
                    'settlement_type': s.settlement_type,
                    'rta_agent_code': s.rta_agent_code,
                    'amc_active_flag': s.amc_active_flag,
                    'dividend_reinvestment_flag': s.dividend_reinvestment_flag,
                    'amc_ind': s.amc_ind,
                    'exit_load_flag': s.exit_load_flag,
                    'exit_load': s.exit_load,
                    'lock_in_period_flag': s.lock_in_period_flag,
                    'lock_in_period': s.lock_in_period,
                    'channel_partner_code': s.channel_partner_code,
                })

        elif report_type == 'bank':
            title = "Investor Bank Details Master Report"
            if user.user_type == User.Types.ADMIN:
                qs = BankAccount.objects.select_related('investor', 'investor__user').all()
            elif user.user_type == User.Types.RM:
                qs = BankAccount.objects.filter(
                    Q(investor__rm__user=user) | Q(investor__distributor__rm__user=user)
                ).select_related('investor', 'investor__user')
            elif user.user_type == User.Types.DISTRIBUTOR:
                qs = BankAccount.objects.filter(investor__distributor__user=user).select_related('investor', 'investor__user')
            elif user.user_type == User.Types.INVESTOR:
                qs = BankAccount.objects.filter(investor__user=user).select_related('investor', 'investor__user')
            else:
                qs = BankAccount.objects.none()

            for bank in qs:
                data.append({
                    'investor_name': bank.investor.user.name or bank.investor.user.username,
                    'pan': bank.investor.pan,
                    'bank_name': bank.bank_name,
                    'account_number': bank.account_number,
                    'ifsc_code': bank.ifsc_code,
                    'account_type': bank.get_account_type_display(),
                    'branch_name': bank.branch_name,
                    'is_default': 'Yes' if bank.is_default else 'No'
                })

        elif report_type == 'nominee':
            title = "Investor Nominee Details Master Report"
            if user.user_type == User.Types.ADMIN:
                qs = Nominee.objects.select_related('investor', 'investor__user').all()
            elif user.user_type == User.Types.RM:
                qs = Nominee.objects.filter(
                    Q(investor__rm__user=user) | Q(investor__distributor__rm__user=user)
                ).select_related('investor', 'investor__user')
            elif user.user_type == User.Types.DISTRIBUTOR:
                qs = Nominee.objects.filter(investor__distributor__user=user).select_related('investor', 'investor__user')
            elif user.user_type == User.Types.INVESTOR:
                qs = Nominee.objects.filter(investor__user=user).select_related('investor', 'investor__user')
            else:
                qs = Nominee.objects.none()

            for nom in qs:
                data.append({
                    'investor_name': nom.investor.user.name or nom.investor.user.username,
                    'pan': nom.investor.pan,
                    'nominee_name': nom.name,
                    'relationship': nom.relationship,
                    'percentage': round(float(nom.percentage), 2),
                    'date_of_birth': nom.date_of_birth.strftime('%Y-%m-%d') if nom.date_of_birth else '',
                    'guardian_name': nom.guardian_name,
                    'guardian_pan': nom.guardian_pan,
                    'nominee_pan': nom.pan,
                    'address_1': nom.address_1,
                    'city': nom.city,
                    'state': nom.state,
                    'pincode': nom.pincode,
                    'country': nom.country,
                    'mobile': nom.mobile,
                    'email': nom.email,
                    'id_type': nom.get_id_type_display(),
                    'id_number': nom.id_number,
                })

        context['grid_data_json'] = json.dumps(data, cls=DjangoJSONEncoder)
        context['report_title'] = title
        context['report_type'] = report_type
        return context

class OrderStatusReportView(LoginRequiredMixin, TemplateView):
    template_name = 'reports/order_status.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        # Get Filter Params
        from_date_str = self.request.GET.get('from_date')
        to_date_str = self.request.GET.get('to_date')

        # Default to today if not provided
        if not from_date_str:
            from_date_str = datetime.date.today().strftime("%d/%m/%Y")
        if not to_date_str:
            to_date_str = datetime.date.today().strftime("%d/%m/%Y")

        try:
            from_date = datetime.datetime.strptime(from_date_str, "%d/%m/%Y").date()
            # For end date, we want to include the whole day, so we might need strict filtering or lt next day.
            # But simple date filtering on DateTimeField uses 00:00:00.
            # created_at is DateTimeField.
            to_date = datetime.datetime.strptime(to_date_str, "%d/%m/%Y").date()
            # Adjust to_date to end of day
            to_date_end = to_date + datetime.timedelta(days=1)
        except ValueError:
            from_date = datetime.date.today()
            to_date = datetime.date.today()
            to_date_end = to_date + datetime.timedelta(days=1)

        data = []

        # Role-based Filtering
        qs = Order.objects.filter(created_at__range=(from_date, to_date_end))

        if user.user_type == User.Types.ADMIN:
            pass
        elif user.user_type == User.Types.RM:
            qs = qs.filter(
                Q(investor__rm__user=user) | Q(investor__distributor__rm__user=user)
            ).distinct()
        elif user.user_type == User.Types.DISTRIBUTOR:
            qs = qs.filter(investor__distributor__user=user)
        elif user.user_type == User.Types.INVESTOR:
            qs = qs.filter(investor__user=user)
        else:
            qs = Order.objects.none()

        qs = qs.select_related('investor', 'scheme').order_by('-created_at')

        for order in qs:
            data.append({
                'OrderNo': order.bse_order_id or '',
                'ClientCode': order.investor.ucc_code,
                'SchemeCode': order.scheme.scheme_code,
                'OrderType': order.get_transaction_type_display(),
                'BuySell': 'P' if order.transaction_type == 'P' else 'R' if order.transaction_type == 'R' else order.transaction_type,
                'OrderVal': round(float(order.amount), 2),
                'OrderStatus': order.get_status_display(), # Or raw status if preferred
                'OrderRemarks': order.bse_remarks or '',
                'TransNo': order.bse_order_id or '' # Assuming TransNo == OrderNo locally
            })

        context['grid_data_json'] = json.dumps(data, cls=DjangoJSONEncoder)
        context['from_date'] = from_date_str
        context['to_date'] = to_date_str
        return context

class AllotmentReportView(LoginRequiredMixin, TemplateView):
    template_name = 'reports/allotment_statement.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        from_date_str = self.request.GET.get('from_date')
        to_date_str = self.request.GET.get('to_date')

        if not from_date_str:
            from_date_str = datetime.date.today().strftime("%d/%m/%Y")
        if not to_date_str:
            to_date_str = datetime.date.today().strftime("%d/%m/%Y")

        try:
            from_date = datetime.datetime.strptime(from_date_str, "%d/%m/%Y").date()
            to_date = datetime.datetime.strptime(to_date_str, "%d/%m/%Y").date()
        except ValueError:
            from_date = datetime.date.today()
            to_date = datetime.date.today()

        data = []

        # Query Transactions
        # Source BSE, Type Purchase/Switch-In
        # Filtering by date (Transaction has date field which is DateField)
        qs = Transaction.objects.filter(
            source=Transaction.SOURCE_BSE,
            txn_type_code__in=['P', 'SI'],
            date__range=(from_date, to_date)
        )

        if user.user_type == User.Types.ADMIN:
            pass
        elif user.user_type == User.Types.RM:
            qs = qs.filter(
                Q(investor__rm__user=user) | Q(investor__distributor__rm__user=user)
            ).distinct()
        elif user.user_type == User.Types.DISTRIBUTOR:
            qs = qs.filter(investor__distributor__user=user)
        elif user.user_type == User.Types.INVESTOR:
            qs = qs.filter(investor__user=user)
        else:
            qs = Transaction.objects.none()

        qs = qs.select_related('investor', 'scheme').order_by('-date')

        for txn in qs:
            data.append({
                'OrderNo': txn.bse_order_id or '',
                'ClientCode': txn.investor.ucc_code,
                'SchemeCode': txn.scheme.scheme_code if txn.scheme else '',
                'FolioNo': txn.folio_number,
                'AllottedUnit': round(float(txn.units), 2),
                'AllottedAmt': round(float(txn.amount), 2),
                'Nav': round(float(txn.nav) if txn.nav else 0, 2),
                'AllotmentDate': txn.date.strftime("%d/%m/%Y"),
                'TransNo': txn.bse_order_id or ''
            })

        context['grid_data_json'] = json.dumps(data, cls=DjangoJSONEncoder)
        context['from_date'] = from_date_str
        context['to_date'] = to_date_str
        return context

class RedemptionReportView(LoginRequiredMixin, TemplateView):
    template_name = 'reports/redemption_statement.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        from_date_str = self.request.GET.get('from_date')
        to_date_str = self.request.GET.get('to_date')

        if not from_date_str:
            from_date_str = datetime.date.today().strftime("%d/%m/%Y")
        if not to_date_str:
            to_date_str = datetime.date.today().strftime("%d/%m/%Y")

        try:
            from_date = datetime.datetime.strptime(from_date_str, "%d/%m/%Y").date()
            to_date = datetime.datetime.strptime(to_date_str, "%d/%m/%Y").date()
        except ValueError:
            from_date = datetime.date.today()
            to_date = datetime.date.today()

        data = []

        qs = Transaction.objects.filter(
            source=Transaction.SOURCE_BSE,
            txn_type_code__in=['R', 'SO'], # Redemption or Switch Out
            date__range=(from_date, to_date)
        )

        if user.user_type == User.Types.ADMIN:
            pass
        elif user.user_type == User.Types.RM:
            qs = qs.filter(
                Q(investor__rm__user=user) | Q(investor__distributor__rm__user=user)
            ).distinct()
        elif user.user_type == User.Types.DISTRIBUTOR:
            qs = qs.filter(investor__distributor__user=user)
        elif user.user_type == User.Types.INVESTOR:
            qs = qs.filter(investor__user=user)
        else:
            qs = Transaction.objects.none()

        qs = qs.select_related('investor', 'scheme').order_by('-date')

        for txn in qs:
            data.append({
                'OrderNo': txn.bse_order_id or '',
                'ClientCode': txn.investor.ucc_code,
                'SchemeCode': txn.scheme.scheme_code if txn.scheme else '',
                'FolioNo': txn.folio_number,
                'Units': round(float(txn.units), 2),
                'Amount': round(float(txn.amount), 2),
                'Nav': round(float(txn.nav) if txn.nav else 0, 2),
                'Date': txn.date.strftime("%d/%m/%Y"),
                'Remarks': 'Redeemed',
                'TransNo': txn.bse_order_id or ''
            })

        context['grid_data_json'] = json.dumps(data, cls=DjangoJSONEncoder)
        context['from_date'] = from_date_str
        context['to_date'] = to_date_str
        return context
