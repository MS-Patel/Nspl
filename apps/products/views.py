from django.views.generic import TemplateView, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin
from .models import Scheme
import json
from django.core.serializers.json import DjangoJSONEncoder

class SchemeListView(LoginRequiredMixin, TemplateView):
    template_name = 'products/scheme_list.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Prepare data for Grid.js
        schemes = Scheme.objects.select_related('amc', 'category').all()

        # Format: [id, name, scheme_code, isin, category, type, min_purchase]
        # Adjust columns based on requirements
        data = []
        for s in schemes:
            data.append({
                'id': s.id,
                'name': s.name,
                'scheme_code': s.scheme_code,
                'rta_code': s.rta_scheme_code,
                'isin': s.isin,
                'category': s.category.name if s.category else '',
                'scheme_type': s.scheme_type or '',
                'nav': 'N/A', # Placeholder for now, or fetch from NAVHistory
                'min_purchase': round(float(s.min_purchase_amount), 2),
            })

        context['grid_data_json'] = json.dumps(data, cls=DjangoJSONEncoder)
        return context

class SchemeDetailView(LoginRequiredMixin, DetailView):
    model = Scheme
    template_name = 'products/scheme_detail.html'
    context_object_name = 'scheme'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        scheme = self.object

        # Fetch NAV History for Graph
        # optimize: limit to last 1 year or so if data is huge, but for now take all
        nav_history = scheme.nav_history.order_by('nav_date').values('nav_date', 'net_asset_value')

        chart_data = []
        for item in nav_history:
            chart_data.append({
                'x': item['nav_date'].strftime('%Y-%m-%d'),
                'y': float(item['net_asset_value'])
            })

        context['nav_history_json'] = json.dumps(chart_data)

        # Get latest NAV for display
        latest_nav = scheme.nav_history.order_by('-nav_date').first()
        context['latest_nav'] = latest_nav.net_asset_value if latest_nav else "N/A"
        context['latest_nav_date'] = latest_nav.nav_date if latest_nav else ""

        return context
