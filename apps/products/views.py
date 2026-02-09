from django.views.generic import TemplateView
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
                'min_purchase': float(s.min_purchase_amount),
            })

        context['grid_data_json'] = json.dumps(data, cls=DjangoJSONEncoder)
        return context
