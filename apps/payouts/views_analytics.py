import pandas as pd
import io
from django.shortcuts import get_object_or_404
from django.views.generic import DetailView, View
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.http import HttpResponse
from .models import BrokerageImport
from .analytics import get_investor_brokerage_analytics
from django.contrib.auth import get_user_model

User = get_user_model()

class InvestorAnalyticsDashboardView(LoginRequiredMixin, UserPassesTestMixin, DetailView):
    model = BrokerageImport
    template_name = 'payouts/analytics_dashboard.html'
    context_object_name = 'brokerage_import'

    def test_func(self):
        return self.request.user.user_type == User.Types.ADMIN

    def get_context_data(self, **kwargs):
        import json
        context = super().get_context_data(**kwargs)

        # Get analytical data
        results_list, summary = get_investor_brokerage_analytics(self.object)

        context['analytics_summary'] = summary

        # Prepare aggregated data for RM and Distributor grids
        rm_dict = {}
        dist_dict = {}

        for item in results_list:
            # RM Aggregation
            if item['rm_name']:
                rm_str = item['rm_name']
                # parse Code(Name) format
                if '(' in rm_str and rm_str.endswith(')'):
                    code, name = rm_str[:-1].split('(', 1)
                else:
                    code, name = rm_str, ''

                if code not in rm_dict:
                    rm_dict[code] = {'code': code, 'name': name, 'amount': 0.0}
                rm_dict[code]['amount'] += float(item['total_brokerage'])

            # Distributor Aggregation
            if item['distributor_name']:
                dist_str = item['distributor_name']
                if '(' in dist_str and dist_str.endswith(')'):
                    code, name = dist_str[:-1].split('(', 1)
                else:
                    code, name = dist_str, ''

                if code not in dist_dict:
                    dist_dict[code] = {'code': code, 'name': name, 'amount': 0.0}
                dist_dict[code]['amount'] += float(item['total_brokerage'])

        context['rm_data_json'] = list(rm_dict.values())
        context['distributor_data_json'] = list(dist_dict.values())

        return context

class ExportInvestorAnalyticsView(LoginRequiredMixin, UserPassesTestMixin, View):
    def test_func(self):
        return self.request.user.user_type == User.Types.ADMIN

    def get(self, request, pk, *args, **kwargs):
        brokerage_import = get_object_or_404(BrokerageImport, pk=pk)
        results_list, _ = get_investor_brokerage_analytics(brokerage_import)

        data = []
        for item in results_list:
            data.append({
                'Investor Name': item['investor_name'],
                'PAN': item['pan'],
                'Direct Investor': 'Yes' if item['is_direct'] else '',
                'RM Name': item['rm_name'],
                'RM Code': item['rm_code'],
                'Distributor Name': item['distributor_name'],
                'Distributor Code': item['distributor_code'],
                'Total Brokerage Earned': item['total_brokerage'],
            })

        df = pd.DataFrame(data)

        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Investor Brokerage')

        output.seek(0)

        response = HttpResponse(
            output.read(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename=investor_brokerage_{brokerage_import.id}.xlsx'

        return response
