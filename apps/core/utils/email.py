from django.core.mail import get_connection, EmailMessage, EmailMultiAlternatives
from apps.administration.models import SystemConfiguration
import logging

logger = logging.getLogger(__name__)

def get_system_email_connection():
    """
    Returns an email connection using the settings from SystemConfiguration.
    """
    config = SystemConfiguration.get_solo()

    return get_connection(
        host=config.email_host,
        port=config.email_port,
        username=config.email_host_user,
        password=config.email_host_password,
        use_tls=config.email_use_tls,
        use_ssl=config.email_use_ssl,
        fail_silently=False
    )

def send_system_email(subject, message, recipient_list, html_message=None, fail_silently=False):
    """
    Sends an email using the system configuration settings.
    """
    config = SystemConfiguration.get_solo()
    from_email = config.default_from_email

    connection = get_system_email_connection()

    try:
        if html_message:
            email = EmailMultiAlternatives(
                subject=subject,
                body=message,
                from_email=from_email,
                to=recipient_list,
                connection=connection
            )
            email.attach_alternative(html_message, "text/html")
        else:
            email = EmailMessage(
                subject=subject,
                body=message,
                from_email=from_email,
                to=recipient_list,
                connection=connection
            )

        return email.send(fail_silently=fail_silently)
    except Exception as e:
        logger.error(f"Failed to send system email to {recipient_list}: {str(e)}")
        if not fail_silently:
            raise e
        return 0
