from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django import forms
from django.views.generic import ListView
from django.views import View
from django.utils.decorators import method_decorator
from django.contrib.auth import get_user_model
from django.db import connections
from .models import RTAFile, Transaction, FailedRTARecord
from .parsers import FranklinParser, DBFParser, KarvyCSVParser
import threading
import logging
import pandas as pd

User = get_user_model()
logger = logging.getLogger(__name__)

class RTAUploadForm(forms.ModelForm):
    class Meta:
        model = RTAFile
        fields = ['rta_type', 'file']

@login_required
def upload_rta_file(request):
    # Only Admin or Operations (assuming Admin for now)
    # Note: User model custom user_type check
    # Transaction.objects.all().delete()

    if not request.user.is_authenticated or getattr(request.user, 'user_type', None) != 'ADMIN':
         messages.error(request, "Access Denied")
         return redirect('users:login')

    if request.method == 'POST':
        form = RTAUploadForm(request.POST, request.FILES)
        if form.is_valid():
            rta_file = form.save(commit=False)
            rta_file.file_name = request.FILES['file'].name
            rta_file.save()
            rta_file.refresh_from_db() # Get ID

            # Trigger Parser Sync
            parser = None
            filename = rta_file.file_name.lower()

            if rta_file.rta_type == RTAFile.RTA_CAMS:
                # CAMS is now strictly DBF
                if filename.endswith('.dbf'):
                    parser = DBFParser(rta_file_obj=rta_file)
                else:
                    rta_file.status = RTAFile.STATUS_FAILED
                    rta_file.error_log = "Only DBF format is supported for CAMS."
                    rta_file.save()
                    messages.error(request, "Only DBF format is supported for CAMS.")
                    return redirect('reconciliation:rta_upload')

            elif rta_file.rta_type == RTAFile.RTA_KARVY:
                # Karvy is now strictly CSV (removed DBF/XLS/TXT support for Karvy as per request "use only csv format")
                if filename.endswith('.csv'):
                     parser = KarvyCSVParser(rta_file_obj=rta_file)
                else:
                    rta_file.status = RTAFile.STATUS_FAILED
                    rta_file.error_log = "Only CSV format is supported for Karvy."
                    rta_file.save()
                    messages.error(request, "Only CSV format is supported for Karvy.")
                    return redirect('reconciliation:rta_upload')
            
            elif rta_file.rta_type == RTAFile.RTA_FRANKLIN:
                parser = FranklinParser(rta_file_obj=rta_file)

            if parser:
                def run_parser():
                    try:
                        parser.parse()
                    except Exception as e:
                        logger.error(f"Parsing Error: {e}")
                    finally:
                        connections.close_all()

                thread = threading.Thread(target=run_parser)
                thread.start()
                messages.success(request, "File uploaded. Processing started in background.")

            return redirect('reconciliation:rta_upload')
    else:
        form = RTAUploadForm()

    recent_files = RTAFile.objects.all().order_by('-uploaded_at')[:5]
    return render(request, 'reconciliation/upload.html', {'form': form, 'recent_files': recent_files})

@method_decorator(login_required, name='dispatch')
class FailedRTARecordListView(ListView):
    model = FailedRTARecord
    template_name = 'reconciliation/failed_record_list.html'
    context_object_name = 'failed_records'
    paginate_by = 50

    def dispatch(self, request, *args, **kwargs):
        if getattr(request.user, 'user_type', None) != 'ADMIN':
             messages.error(request, "Access Denied")
             return redirect('users:login')
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        qs = FailedRTARecord.objects.filter(status=FailedRTARecord.STATUS_FAILED)

        rta_type = self.request.GET.get('rta_type')
        if rta_type:
            qs = qs.filter(rta_type=rta_type)

        error_reason = self.request.GET.get('error_reason')
        if error_reason:
            qs = qs.filter(error_reason__icontains=error_reason)

        return qs.order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['rta_types'] = RTAFile.RTA_CHOICES
        return context

@method_decorator(login_required, name='dispatch')
class RetryFailedRTARecordView(View):
    def dispatch(self, request, *args, **kwargs):
        if getattr(request.user, 'user_type', None) != 'ADMIN':
             messages.error(request, "Access Denied")
             return redirect('users:login')
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, pk=None):
        if pk:
            records = [get_object_or_404(FailedRTARecord, pk=pk, status=FailedRTARecord.STATUS_FAILED)]
        else:
            records = list(FailedRTARecord.objects.filter(status=FailedRTARecord.STATUS_FAILED))

        if not records:
            messages.warning(request, "No failed records found to retry.")
            return redirect('reconciliation:failed_records')

        # Group by parser type
        records_by_type = {
            'CAMS': [],
            'KARVY': [],
            'FRANKLIN': []
        }
        for r in records:
            if r.rta_type in records_by_type:
                records_by_type[r.rta_type].append(r)

        success_count = 0
        fail_count = 0

        # We will reconstruct dataframes and pass to parsers
        for rta_type, type_records in records_by_type.items():
            if not type_records:
                continue

            rows = [r.row_data for r in type_records]

            # Since these are failed rows, we might need to recreate a dummy parser or
            # bypass standard file opening.

            # For simplicity, we can reuse parsers by giving them a dataframe
            if rta_type == 'CAMS':
                df = pd.DataFrame(rows)
                # Need to restore numeric/date types properly?
                # Pandas will do its best.

                for record in type_records:
                    # Some values might have been saved as strings but need to be null/NaN for pandas
                    cleaned_row_data = {}
                    for k, v in record.row_data.items():
                        if v == 'None' or v is None:
                            cleaned_row_data[k] = None
                        else:
                            cleaned_row_data[k] = v

                    single_df = pd.DataFrame([cleaned_row_data])
                    single_parser = DBFParser()
                    single_parser.is_retry = True
                    single_parser.rta_file = record.source_file # pass original file context
                    single_parser.failed_rows = []

                    try:
                        single_parser.parse_cams(single_df)
                        if not single_parser.failed_rows:
                            record.status = FailedRTARecord.STATUS_RESOLVED
                            record.save()
                            success_count += 1
                        else:
                            record.error_reason = single_parser.failed_rows[0].get('error', 'Unknown Error')
                            record.save()
                            fail_count += 1
                    except Exception as e:
                        record.error_reason = str(e)
                        record.save()
                        fail_count += 1

            elif rta_type == 'KARVY':
                for record in type_records:
                    # Karvy logic expects dataframe with certain columns.
                    # Our json field has them.
                    cleaned_row_data = {}
                    for k, v in record.row_data.items():
                        if v == 'None' or v is None:
                            cleaned_row_data[k] = None
                        else:
                            cleaned_row_data[k] = v

                    single_df = pd.DataFrame([cleaned_row_data])
                    single_parser = KarvyCSVParser()
                    single_parser.is_retry = True
                    single_parser.rta_file = record.source_file
                    single_parser.failed_rows = []

                    import tempfile
                    import os
                    try:
                        fd, temp_path = tempfile.mkstemp(suffix='.csv')
                        with os.fdopen(fd, 'w', newline='', encoding='utf-8') as f:
                            single_df.to_csv(f, index=False)

                        single_parser.file_path = temp_path
                        single_parser.parse()

                        if not single_parser.failed_rows:
                            record.status = FailedRTARecord.STATUS_RESOLVED
                            record.save()
                            success_count += 1
                        else:
                            record.error_reason = single_parser.failed_rows[0].get('error', 'Unknown Error')
                            record.save()
                            fail_count += 1

                    except Exception as e:
                        record.error_reason = str(e)
                        record.save()
                        fail_count += 1
                    finally:
                        if os.path.exists(temp_path):
                            os.remove(temp_path)

            elif rta_type == 'FRANKLIN':
                for record in type_records:
                    import tempfile
                    import os
                    import csv
                    try:
                        fd, temp_path = tempfile.mkstemp(suffix='.txt')
                        with os.fdopen(fd, 'w', newline='', encoding='utf-8') as f:
                            writer = csv.writer(f, delimiter='|')
                            # The row_data for Franklin is stored as dict indices "0", "1", "2"...
                            row_list = [record.row_data.get(str(i)) for i in range(len(record.row_data))]
                            writer.writerow(row_list)

                        single_parser = FranklinParser()
                        single_parser.is_retry = True
                        single_parser.rta_file = record.source_file
                        single_parser.file_path = temp_path
                        single_parser.failed_rows = []
                        single_parser.parse()

                        if not single_parser.failed_rows:
                            record.status = FailedRTARecord.STATUS_RESOLVED
                            record.save()
                            success_count += 1
                        else:
                            record.error_reason = single_parser.failed_rows[0].get('error', 'Unknown Error')
                            record.save()
                            fail_count += 1

                    except Exception as e:
                        record.error_reason = str(e)
                        record.save()
                        fail_count += 1
                    finally:
                        if os.path.exists(temp_path):
                            os.remove(temp_path)

        messages.success(request, f"Retried records. {success_count} succeeded, {fail_count} failed again.")
        return redirect('reconciliation:failed_records')
