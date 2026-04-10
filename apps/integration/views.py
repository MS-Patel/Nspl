from django.shortcuts import render
from django.views import View
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.contrib.auth import get_user_model
from apps.users.models import InvestorProfile, NDMLKYCDetails
from .cvl_client import CVLClient
from .ndml_client import NDMLClient
import json
import requests
import re
from django.utils import timezone

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
            investor_id = data.get('investor_id')

            # 1. Local Check
            user_qs = User.objects.filter(username=pan)
            profile_qs = InvestorProfile.objects.filter(pan=pan)

            if investor_id:
                try:
                    investor = InvestorProfile.objects.get(pk=investor_id)
                    profile_qs = profile_qs.exclude(pk=investor.pk)
                    if investor.user_id:
                        user_qs = user_qs.exclude(pk=investor.user_id)
                except InvestorProfile.DoesNotExist:
                    pass

            if user_qs.exists():
                 return JsonResponse({
                     'status': 'error', 
                     'remarks': f'PAN {pan} is already registered in the system.'
                 })
            
            if profile_qs.exists():
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

class GetBankDetailsView(View):
    def get(self, request, *args, **kwargs):
        ifsc = request.GET.get('ifsc')
        if not ifsc:
            return JsonResponse({'status': 'error', 'message': 'IFSC code is required.'}, status=400)

        ifsc = ifsc.strip().upper()

        # Validate IFSC Format
        if not re.match(r'^[A-Z]{4}0[A-Z0-9]{6}$', ifsc):
             return JsonResponse({'status': 'error', 'message': 'Invalid IFSC Code format.'}, status=400)

        try:
            # Using Razorpay Public IFSC API with timeout
            response = requests.get(f"https://ifsc.razorpay.com/{ifsc}", timeout=10)

            if response.status_code == 200:
                data = response.json()
                return JsonResponse({
                    'status': 'success',
                    'data': {
                        'BANK': data.get('BANK'),
                        'BRANCH': data.get('BRANCH'),
                        'CITY': data.get('CITY'),
                        'STATE': data.get('STATE'),
                        'IFSC': data.get('IFSC')
                    }
                })
            elif response.status_code == 404:
                 return JsonResponse({'status': 'error', 'message': 'Invalid IFSC Code.'}, status=404)
            else:
                 return JsonResponse({'status': 'error', 'message': 'Error fetching bank details.'}, status=500)

        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

class NDMLRegistrationView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        try:
            data = json.loads(request.body)
            request_xml = data.get('request_xml')
            investor_id = data.get('investor_id')

            if not request_xml:
                return JsonResponse({'status': 'error', 'remarks': 'XML request is required.'}, status=400)

            client = NDMLClient()
            response = client.kyc_registration(request_xml)

            if response['status'] == 'success' and investor_id:
                try:
                    investor = InvestorProfile.objects.get(id=investor_id)
                    investor.ndml_last_synced_at = timezone.now()
                    # A robust implementation would parse the response XML here and update fields
                    # e.g., investor.ndml_reg_ack = parsed_ack
                    investor.save()
                except InvestorProfile.DoesNotExist:
                    pass

            return JsonResponse(response)
        except json.JSONDecodeError:
            return JsonResponse({'status': 'error', 'remarks': 'Invalid JSON.'}, status=400)
        except Exception as e:
            return JsonResponse({'status': 'error', 'remarks': str(e)}, status=500)

class NDMLInquiryView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        try:
            data = json.loads(request.body)
            request_xml = data.get('request_xml')
            investor_id = data.get('investor_id')

            if not request_xml:
                return JsonResponse({'status': 'error', 'remarks': 'XML request is required.'}, status=400)

            client = NDMLClient()
            response = client.pan_inquiry_details_two(request_xml)

            if response['status'] == 'success' and investor_id:
                try:
                    investor = InvestorProfile.objects.get(id=investor_id)
                    investor.ndml_last_synced_at = timezone.now()
                    investor.save()
                except InvestorProfile.DoesNotExist:
                    pass

            return JsonResponse(response)
        except json.JSONDecodeError:
            return JsonResponse({'status': 'error', 'remarks': 'Invalid JSON.'}, status=400)
        except Exception as e:
            return JsonResponse({'status': 'error', 'remarks': str(e)}, status=500)

class NDMLDownloadView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        try:
            data = json.loads(request.body)
            request_xml = data.get('request_xml')
            investor_id = data.get('investor_id')

            if not request_xml:
                return JsonResponse({'status': 'error', 'remarks': 'XML request is required.'}, status=400)

            client = NDMLClient()
            response = client.kyc_download_details(request_xml)

            if response['status'] == 'success' and investor_id:
                try:
                    investor = InvestorProfile.objects.get(id=investor_id)
                    # Create or update NDMLKYCDetails
                    details, created = NDMLKYCDetails.objects.get_or_create(investor=investor)
                    # Convert response to string if it's an object/byte string to store in raw_response
                    details.raw_response = str(response.get('data', ''))
                    # A robust implementation would parse the XML and fill in name, dob, etc.
                    details.save()
                except InvestorProfile.DoesNotExist:
                    pass

            return JsonResponse(response)
        except json.JSONDecodeError:
            return JsonResponse({'status': 'error', 'remarks': 'Invalid JSON.'}, status=400)
        except Exception as e:
            return JsonResponse({'status': 'error', 'remarks': str(e)}, status=500)
