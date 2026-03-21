import datetime
from dateutil.relativedelta import relativedelta
from django.utils import timezone
from .models import SIP, SIPInstallment

def generate_sip_installments(sip):
    """
    Generates SIPInstallment rows based on the SIP master schedule.
    Rules:
    - Handle month-end issues automatically using relativedelta
    - Ensure timezone consistency (using dates)
    """
    if not sip.start_date:
        return

    # Maximum limits to avoid infinite loops
    max_installments = sip.installments if sip.installments and sip.installments > 0 else 1200

    current_date = sip.start_date
    installment_day = sip.installment_day or sip.start_date.day

    count = 0
    installments_to_create = []

    # Get existing due dates to avoid duplicates
    existing_dates = set(
        SIPInstallment.objects.filter(sip_master=sip).values_list('due_date', flat=True)
    )

    while count < max_installments:
        if sip.end_date and current_date > sip.end_date:
            break

        # Calculate the expected due date for this iteration
        if sip.frequency in [SIP.MONTHLY, SIP.QUARTERLY]:
            # Adjust to the correct installment_day, handling month ends
            try:
                expected_due_date = current_date.replace(day=installment_day)
            except ValueError:
                # E.g., replace(day=31) in Feb or April. Find the last day of the current month.
                next_month = current_date.replace(day=28) + relativedelta(days=4)
                expected_due_date = next_month - relativedelta(days=next_month.day)
        else:
            # For weekly/daily, we just strictly follow the current_date increment
            expected_due_date = current_date

        if expected_due_date not in existing_dates:
            installments_to_create.append(
                SIPInstallment(
                    sip_master=sip,
                    due_date=expected_due_date,
                    expected_amount=sip.amount,
                    status=SIPInstallment.STATUS_PENDING
                )
            )
            # Add to existing dates so we don't duplicate within the same generation pass
            # if somehow the logic produces the same date
            existing_dates.add(expected_due_date)

        # Advance the current_date for the next iteration
        if sip.frequency == SIP.MONTHLY:
            current_date += relativedelta(months=1)
        elif sip.frequency == SIP.WEEKLY:
            current_date += relativedelta(weeks=1)
        elif sip.frequency == SIP.DAILY:
            current_date += relativedelta(days=1)
        elif sip.frequency == SIP.QUARTERLY:
            current_date += relativedelta(months=3)
        else:
            break # Unknown frequency

        count += 1

    if installments_to_create:
        SIPInstallment.objects.bulk_create(installments_to_create, batch_size=500)

def get_upcoming_installments(days=30):
    """
    Returns upcoming installments for the next N days.
    """
    today = datetime.date.today()
    end_date = today + datetime.timedelta(days=days)

    installments = SIPInstallment.objects.filter(
        due_date__range=[today, end_date],
        status=SIPInstallment.STATUS_PENDING,
        sip_master__status=SIP.STATUS_ACTIVE
    ).select_related('sip_master', 'sip_master__scheme', 'sip_master__investor')

    return installments
