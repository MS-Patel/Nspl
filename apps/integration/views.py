from django.shortcuts import render
from django.views import View
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.contrib.auth import get_user_model
from apps.users.models import InvestorProfile
from .cvl_client import CVLClient
import json

# Create your views here.
User = get_user_model()

class BSEPanCheckToolView(LoginRequiredMixin, TemplateView):
    template_name = 'integration/pan_check.html'

class CheckPANStatusView(View):
    def post(self, request, *args, **kwargs):
        try:
            data = json.loads(request.body)
            pan = data.get('pan')
            if not pan:
                 return JsonResponse({'status': 'error', 'remarks': 'PAN is required.'}, status=400)
            
            pan = pan.strip().upper()

            # 1. Local Check
            if User.objects.filter(username=pan).exists():
                 return JsonResponse({
                     'status': 'error', 
                     'remarks': f'PAN {pan} is already registered in the system.'
                 })
            
            if InvestorProfile.objects.filter(pan=pan).exists():
                 return JsonResponse({
                     'status': 'error', 
                     'remarks': f'Investor Profile with PAN {pan} already exists.'
                 })

            # 2. CVL Check
            client = CVLClient()
            response = client.get_pan_status(pan)
            
            return JsonResponse(response)

        except json.JSONDecodeError:
             return JsonResponse({'status': 'error', 'remarks': 'Invalid JSON.'}, status=400)
        except Exception as e:
            return JsonResponse({'status': 'error', 'remarks': str(e)}, status=500)
