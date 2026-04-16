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
from apps.administration.models import SystemConfiguration

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

from .forms import NDMLRegistrationForm
import xml.etree.ElementTree as ET
from datetime import datetime

class NDMLRegistrationToolView(LoginRequiredMixin, View):
    template_name = 'integration/ndml_kyc_registration.html'

    def get(self, request, *args, **kwargs):
        form = NDMLRegistrationForm()
        return render(request, self.template_name, {'form': form})

    def post(self, request, *args, **kwargs):
        form = NDMLRegistrationForm(request.POST)
        context = {'form': form}

        if form.is_valid():
            try:
                # Construct XML dynamically
                data = form.cleaned_data

                # Create root element
                root = ET.Element("APP_REQ_ROOT")

                # Create APP_PAN_INQ element
                app_pan_inq = ET.SubElement(root, "APP_PAN_INQ")

                # Fill elements with data
                ET.SubElement(app_pan_inq, "APP_IOP_FLG").text = "IE"

                # POS Code is fetched from system config in NDMLClient, but for now we put empty or a placeholder if required
                config = SystemConfiguration.get_solo()
                pos_code = config.ndml_pos_code if config else ""
                ET.SubElement(app_pan_inq, "APP_POS_CODE").text = pos_code

                ET.SubElement(app_pan_inq, "APP_TYPE").text = "I"
                ET.SubElement(app_pan_inq, "APP_NO").text = ""
                ET.SubElement(app_pan_inq, "APP_DATE").text = ""

                ET.SubElement(app_pan_inq, "APP_PAN_NO").text = data['pan_no']
                ET.SubElement(app_pan_inq, "APP_PANEX_NO").text = ""
                ET.SubElement(app_pan_inq, "APP_PAN_COPY").text = "Y"
                ET.SubElement(app_pan_inq, "APP_EXMT").text = "N"
                ET.SubElement(app_pan_inq, "APP_EXMT_CAT").text = ""
                ET.SubElement(app_pan_inq, "APP_KYC_MODE").text = "0"
                ET.SubElement(app_pan_inq, "APP_EXMT_ID_PROOF").text = "02"
                ET.SubElement(app_pan_inq, "APP_IPV_FLAG").text = "E"
                ET.SubElement(app_pan_inq, "APP_IPV_DATE").text = datetime.now().strftime("%d-%m-%Y")
                ET.SubElement(app_pan_inq, "APP_GEN").text = data['gender']

                # Split Name (assuming first name and last name, very simple split for XML)
                full_name = data['name']
                name_parts = full_name.split(' ')
                f_name = name_parts[0] if name_parts else ""

                ET.SubElement(app_pan_inq, "APP_NAME").text = full_name
                ET.SubElement(app_pan_inq, "APP_F_NAME").text = f_name
                ET.SubElement(app_pan_inq, "APP_REGNO").text = ""

                dob_str = data['dob'].strftime("%d-%m-%Y")
                ET.SubElement(app_pan_inq, "APP_DOB_DT").text = dob_str
                ET.SubElement(app_pan_inq, "APP_DOI_DT").text = dob_str
                ET.SubElement(app_pan_inq, "APP_COMMENCE_DT").text = ""

                ET.SubElement(app_pan_inq, "APP_NATIONALITY").text = ""
                ET.SubElement(app_pan_inq, "APP_OTH_NATIONALITY").text = "UAE"
                ET.SubElement(app_pan_inq, "APP_COMP_STATUS").text = ""
                ET.SubElement(app_pan_inq, "APP_OTH_COMP_STATUS").text = ""
                ET.SubElement(app_pan_inq, "APP_RES_STATUS").text = ""
                ET.SubElement(app_pan_inq, "APP_RES_STATUS_PROOF").text = ""
                ET.SubElement(app_pan_inq, "APP_UID_NO").text = ""

                ET.SubElement(app_pan_inq, "APP_COR_ADD1").text = data['cor_add1']
                ET.SubElement(app_pan_inq, "APP_COR_ADD2").text = data['cor_add2']
                ET.SubElement(app_pan_inq, "APP_COR_ADD3").text = ""
                ET.SubElement(app_pan_inq, "APP_COR_CITY").text = data['cor_city']
                ET.SubElement(app_pan_inq, "APP_COR_PINCD").text = data['cor_pincode']
                ET.SubElement(app_pan_inq, "APP_COR_STATE").text = data['cor_state']
                ET.SubElement(app_pan_inq, "APP_OTH_COR_STATE").text = data['cor_state']
                ET.SubElement(app_pan_inq, "APP_COR_CTRY").text = data['cor_ctry']

                ET.SubElement(app_pan_inq, "APP_OFF_NO").text = ""
                ET.SubElement(app_pan_inq, "APP_RES_NO").text = ""
                ET.SubElement(app_pan_inq, "APP_MOB_NO").text = data['mobile_no']
                ET.SubElement(app_pan_inq, "APP_FAX_NO").text = ""
                ET.SubElement(app_pan_inq, "APP_EMAIL").text = data['email']

                ET.SubElement(app_pan_inq, "APP_COR_ADD_PROOF").text = "26"
                ET.SubElement(app_pan_inq, "APP_COR_ADD_REF").text = "xxxxxxxx5831"
                ET.SubElement(app_pan_inq, "APP_COR_ADD_DT").text = ""

                # Copying Correspondence to Permanent for simplicity
                ET.SubElement(app_pan_inq, "APP_PER_ADD1").text = data['cor_add1']
                ET.SubElement(app_pan_inq, "APP_PER_ADD2").text = data['cor_add2']
                ET.SubElement(app_pan_inq, "APP_PER_ADD3").text = ""
                ET.SubElement(app_pan_inq, "APP_PER_CITY").text = data['cor_city']
                ET.SubElement(app_pan_inq, "APP_PER_PINCD").text = data['cor_pincode']
                ET.SubElement(app_pan_inq, "APP_PER_STATE").text = "099"
                ET.SubElement(app_pan_inq, "APP_OTH_PER_STATE").text = data['cor_state']
                ET.SubElement(app_pan_inq, "APP_PER_CTRY").text = data['cor_ctry']
                ET.SubElement(app_pan_inq, "APP_PER_ADD_PROOF").text = "26"
                ET.SubElement(app_pan_inq, "APP_PER_ADD_REF").text = ""
                ET.SubElement(app_pan_inq, "APP_PER_ADD_DT").text = ""

                ET.SubElement(app_pan_inq, "APP_INCOME").text = ""
                ET.SubElement(app_pan_inq, "APP_OCC").text = ""
                ET.SubElement(app_pan_inq, "APP_OTH_OCC").text = ""
                ET.SubElement(app_pan_inq, "APP_POL_CONN").text = "NA"
                ET.SubElement(app_pan_inq, "APP_DOC_PROOF").text = "E"
                ET.SubElement(app_pan_inq, "APP_INTERNAL_REF").text = ""
                ET.SubElement(app_pan_inq, "APP_BRANCH_CODE").text = ""
                ET.SubElement(app_pan_inq, "APP_MAR_STATUS").text = "01"
                ET.SubElement(app_pan_inq, "APP_NETWRTH").text = ""
                ET.SubElement(app_pan_inq, "APP_NETWORTH_DT").text = ""
                ET.SubElement(app_pan_inq, "APP_INCORP_PLC").text = ""
                ET.SubElement(app_pan_inq, "APP_OTHERINFO").text = ""
                ET.SubElement(app_pan_inq, "APP_FILLER1").text = ""
                ET.SubElement(app_pan_inq, "APP_FILLER2").text = ""
                ET.SubElement(app_pan_inq, "APP_FILLER3").text = ""
                ET.SubElement(app_pan_inq, "APP_DUMP_TYPE").text = ""
                ET.SubElement(app_pan_inq, "APP_KRA_INFO").text = ""
                ET.SubElement(app_pan_inq, "APP_SIGNATURE").text = ""
                ET.SubElement(app_pan_inq, "APP_FATCA_APPLICABLE_FLAG").text = ""
                ET.SubElement(app_pan_inq, "APP_FATCA_BIRTH_PLACE").text = ""
                ET.SubElement(app_pan_inq, "APP_FATCA_BIRTH_COUNTRY").text = ""
                ET.SubElement(app_pan_inq, "APP_FATCA_COUNTRY_RES").text = ""
                ET.SubElement(app_pan_inq, "APP_FATCA_COUNTRY_CITYZENSHIP").text = ""
                ET.SubElement(app_pan_inq, "APP_FATCA_DATE_DECLARATION").text = ""

                # FATCA ADDL DETAILS
                for _ in range(4):
                    fatca = ET.SubElement(root, "FATCA_ADDL_DTLS")
                    ET.SubElement(fatca, "APP_FATCA_ENTITY_PAN").text = ""
                    ET.SubElement(fatca, "APP_FATCA_COUNTRY_RESIDENCY").text = ""
                    ET.SubElement(fatca, "APP_FATCA_TAX_IDENTIFICATION_NO").text = ""
                    ET.SubElement(fatca, "APP_FATCA_TAX_EXEMPT_FLAG").text = ""
                    ET.SubElement(fatca, "APP_FATCA_TAX_EXEMPT_REASON").text = ""

                # SUMM REC
                summ_rec = ET.SubElement(root, "APP_SUMM_REC")
                ET.SubElement(summ_rec, "APP_REQ_DATE").text = datetime.now().strftime("%d-%m-%Y")
                ET.SubElement(summ_rec, "APP_OTHKRA_BATCH").text = "ACC0671559052174" # Sample
                ET.SubElement(summ_rec, "APP_OTHKRA_CODE").text = "A1249" # Sample
                ET.SubElement(summ_rec, "APP_TOTAL_REC").text = "1"
                ET.SubElement(summ_rec, "NO_OF_FATCA_ADDL_DTLS_RECORDS").text = "4"

                request_xml = ET.tostring(root, encoding='utf-8', method='xml').decode('utf-8')

                client = NDMLClient()
                response = client.kyc_registration(request_xml)

                if response['status'] == 'success':
                    context['success'] = True
                    context['response_data'] = str(response.get('data', 'Registration Successful'))
                else:
                    context['error'] = True
                    context['response_data'] = str(response.get('remarks', 'An error occurred'))

            except Exception as e:
                context['error'] = True
                context['response_data'] = str(e)
        else:
             context['error'] = True
             context['response_data'] = "Please correct the errors in the form below."

        return render(request, self.template_name, context)
