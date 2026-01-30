from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
import json
from django.core.serializers.json import DjangoJSONEncoder
from django.db.models import Q
import datetime

from apps.users.models import User, InvestorProfile, DistributorProfile, RMProfile
from apps.investments.models import Order, SIP
from apps.products.models import Scheme
from apps.integration.bse_client import BSEStarMFClient

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
                'amount': float(order.amount) if order.amount else 0,
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
                    'isin': s.isin,
                    'category': s.category.name if s.category else '',
                    'amc': s.amc.name,
                    'type': s.scheme_type,
                    'min_purchase': float(s.min_purchase_amount)
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
        from_date = self.request.GET.get('from_date')
        to_date = self.request.GET.get('to_date')
        # Default to today if not provided to avoid showing stale/no data?
        # Or show nothing until searched. Let's show today's data as default "Realtime" view.
        if not from_date:
            from_date = datetime.date.today().strftime("%d/%m/%Y")
        if not to_date:
            to_date = datetime.date.today().strftime("%d/%m/%Y")

        data = []

        # Access Logic for Client Code
        target_client_code = None
        if user.user_type == User.Types.INVESTOR:
             profile = InvestorProfile.objects.filter(user=user).first()
             if profile:
                 target_client_code = profile.ucc_code

        client = BSEStarMFClient()
        response = client.get_order_status(from_date=from_date, to_date=to_date, client_code=target_client_code)

        if response and getattr(response, 'Status', None) == '100' and getattr(response, 'OrderDetails', None):
             # Access Control Logic (Post-fetch filtering for non-investors)
             permitted_uccs = None
             if user.user_type == User.Types.DISTRIBUTOR:
                 permitted_uccs = set(InvestorProfile.objects.filter(distributor__user=user).values_list('ucc_code', flat=True))
             elif user.user_type == User.Types.RM:
                 permitted_uccs = set(InvestorProfile.objects.filter(Q(rm__user=user) | Q(distributor__rm__user=user)).values_list('ucc_code', flat=True))
             for item in response.OrderDetails.OrderDetails:
                 # Check permission
                 if permitted_uccs is not None:
                     if item.ClientCode not in permitted_uccs:
                         continue

                 data.append({
                     'OrderNo': getattr(item, 'OrderNumber', ''),
                     'ClientCode': item.ClientCode,
                     'SchemeCode': item.SchemeCode,
                     'OrderType': item.OrderType,
                     'BuySell': item.BuySell,
                     'OrderVal': float(getattr(item, 'Amount', 0) or 0),
                     'OrderStatus': item.OrderStatus,
                     'OrderRemarks': item.OrderRemarks,
                     'TransNo': getattr(item, 'SettNo', getattr(item, 'TransNo', ''))
                 })

        context['grid_data_json'] = json.dumps(data, cls=DjangoJSONEncoder)
        context['from_date'] = from_date
        context['to_date'] = to_date
        return context

class AllotmentReportView(LoginRequiredMixin, TemplateView):
    template_name = 'reports/allotment_statement.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        from_date = self.request.GET.get('from_date')
        to_date = self.request.GET.get('to_date')
        if not from_date:
            from_date = datetime.date.today().strftime("%d/%m/%Y")
        if not to_date:
            to_date = datetime.date.today().strftime("%d/%m/%Y")

        data = []
        target_client_code = None
        if user.user_type == User.Types.INVESTOR:
             profile = InvestorProfile.objects.filter(user=user).first()
             if profile:
                 target_client_code = profile.ucc_code

        client = BSEStarMFClient()
        # Allotment Statement usually focuses on Purchases
        response = client.get_allotment_statement(from_date=from_date, to_date=to_date, client_code=target_client_code, order_type="All")

        if response and getattr(response, 'Status', None) == '100' and getattr(response, 'AllotmentDetails', None):
             permitted_uccs = None
             if user.user_type == User.Types.DISTRIBUTOR:
                 permitted_uccs = set(InvestorProfile.objects.filter(distributor__user=user).values_list('ucc_code', flat=True))
             elif user.user_type == User.Types.RM:
                 permitted_uccs = set(InvestorProfile.objects.filter(Q(rm__user=user) | Q(distributor__rm__user=user)).values_list('ucc_code', flat=True))

             for item in response.AllotmentDetails.AllotmentDetails:
                 if permitted_uccs is not None:
                     if item.ClientCode not in permitted_uccs:
                         continue

                 data.append({
                     'OrderNo': item.OrderNo,
                     'ClientCode': item.ClientCode,
                     'SchemeCode': item.SchemeCode,
                     'FolioNo': item.FolioNo,
                     'AllottedUnit': float(item.AllottedUnit) if item.AllottedUnit else 0,
                     'AllottedAmt': float(item.AllottedAmt) if item.AllottedAmt else 0,
                     'Nav': float(item.Nav) if item.Nav else 0,
                     'AllotmentDate': item.AllotmentDate,
                     'TransNo': getattr(item, 'TransNo', '')
                 })

        context['grid_data_json'] = json.dumps(data, cls=DjangoJSONEncoder)
        context['from_date'] = from_date
        context['to_date'] = to_date
        return context

class RedemptionReportView(LoginRequiredMixin, TemplateView):
    template_name = 'reports/redemption_statement.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        from_date = self.request.GET.get('from_date')
        to_date = self.request.GET.get('to_date')
        if not from_date:
            from_date = datetime.date.today().strftime("%d/%m/%Y")
        if not to_date:
            to_date = datetime.date.today().strftime("%d/%m/%Y")

        data = []
        target_client_code = None
        if user.user_type == User.Types.INVESTOR:
             profile = InvestorProfile.objects.filter(user=user).first()
             if profile:
                 target_client_code = profile.ucc_code

        client = BSEStarMFClient()
        response = client.get_redemption_statement(from_date=from_date, to_date=to_date, client_code=target_client_code)

        if response and getattr(response, 'Status', None) == '100' and getattr(response, 'RedemptionDetails', None):
             permitted_uccs = None
             if user.user_type == User.Types.DISTRIBUTOR:
                 permitted_uccs = set(InvestorProfile.objects.filter(distributor__user=user).values_list('ucc_code', flat=True))
             elif user.user_type == User.Types.RM:
                 permitted_uccs = set(InvestorProfile.objects.filter(Q(rm__user=user) | Q(distributor__rm__user=user)).values_list('ucc_code', flat=True))

             for item in response.RedemptionDetails.RedemptionDetails:
                 if permitted_uccs is not None:
                     if item.ClientCode not in permitted_uccs:
                         continue
                         
                 data.append({
                     'OrderNo': item.OrderNo,
                     'ClientCode': item.ClientCode,
                     'SchemeCode': item.SchemeCode,
                     'FolioNo': item.FolioNo,
                     'Units': float(item.AllottedUnit) if item.AllottedUnit else 0, # In redemption, this might be units redeemed
                     'Amount': float(item.AllottedAmt) if item.AllottedAmt else 0,
                     'Nav': float(item.Nav) if item.Nav else 0,
                     'Date': item.AllotmentDate,
                     'Remarks': getattr(item, 'Remarks', ''),
                     'TransNo': getattr(item, 'TransNo', '')
                 })

        context['grid_data_json'] = json.dumps(data, cls=DjangoJSONEncoder)
        context['from_date'] = from_date
        context['to_date'] = to_date
        return context
