from django.shortcuts import render
from django.views import View
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from .bse_client import BSEStarMFClient
import json

# Create your views here.

class BSEPanCheckToolView(LoginRequiredMixin, TemplateView):
    template_name = 'integration/pan_check.html'

class CheckPANStatusView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        try:
            data = json.loads(request.body)
            pan = data.get('pan')
            if not pan:
                 return JsonResponse({'status': 'error', 'remarks': 'PAN is required.'}, status=400)

            client = BSEStarMFClient()
            response = client.check_pan_status(pan)
            return JsonResponse(response)
        except json.JSONDecodeError:
             return JsonResponse({'status': 'error', 'remarks': 'Invalid JSON.'}, status=400)
        except Exception as e:
            return JsonResponse({'status': 'error', 'remarks': str(e)}, status=500)
