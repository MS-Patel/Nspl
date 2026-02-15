from django.template import Template, Context
from django.conf import settings
import requests
import logging

logger = logging.getLogger(__name__)

SMS_TEMPLATES = {
    "otp":"Hi , Your OTP Verification Code is {{ otp }}.This code is valid for next 10 minutes.For security reason do not share this OTP with anyone. Team Buybestfin.com",
    "otp2": "Hi, Your OTP Verification Code is {{ otp }}. This code is valid for the next {{ validity_period }} minutes. For security reasons, do not share this OTP with anyone.",
    "welcome": "Welcome {{ user_name }}! Thank you for registering with us. Your account ID is {{ account_id }}.",
}

def render_sms_template(template_name, context):
    try:
        template_string = SMS_TEMPLATES.get(template_name)
        if not template_string:
            raise ValueError(f"Template '{template_name}' not found.")
        template = Template(template_string)
        return template.render(Context(context))
    except Exception as e:
        logger.error(f"Error rendering template: {e}")
        return None


def send_sms_with_template(mobile_no, template_name, context):
    # Render the message using the template
    message = render_sms_template(template_name, context)
    if not message:
        return {"status": "error", "message": "Failed to render SMS template"}

    # Call the SMS API
    api_key = settings.SMS_API_KEY
    sender = settings.SMS_SENDER_ID
    base_url = settings.SMS_BASE_URL
    url = f"{base_url}?apikey={api_key}&sender={sender}&text={message}&mobileno={mobile_no}"

    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Error sending SMS: {e}")
        return {"status": "error", "message": str(e)}
