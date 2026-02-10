from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
import json
from django.core.serializers.json import DjangoJSONEncoder
from django.db.models import Q
import datetime

from apps.users.models import User, InvestorProfile, DistributorProfile, RMProfile
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
            # Flatten Bank Details (Take first or default)
            bank = inv.bank_accounts.filter(is_default=True).first()
            if not bank:
                bank = inv.bank_accounts.first()

            # Flatten Nominee (Take first)
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
                qs = DistributorProfile.objects.select_related('user', 'rm', 'rm__user').all()
            elif user.user_type == User.Types.RM:
                qs = DistributorProfile.objects.filter(rm__user=user).select_related('user', 'rm', 'rm__user')
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
                    'status': 'Active' if dist.user.is_active else 'Inactive'
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
                        'status': 'Active' if rm.user.is_active else 'Inactive'
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
                    'min_purchase': round(float(s.min_purchase_amount), 2)
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
