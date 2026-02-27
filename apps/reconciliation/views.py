from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django import forms
from .models import RTAFile, Transaction
from .parsers import KarvyParser, FranklinParser, KarvyXLSParser, DBFParser
import threading
from django.db import connections
from django.http import HttpResponseForbidden

class RTAUploadForm(forms.ModelForm):
    class Meta:
        model = RTAFile
        fields = ['rta_type', 'file']

@login_required
def upload_rta_file(request):
    # Only Admin or Operations (assuming Admin for now)
    # Note: User model custom user_type check
    if not request.user.is_authenticated or getattr(request.user, 'user_type', None) != 'ADMIN':
         messages.error(request, "Access Denied")
         return redirect('users:login')

    if request.method == 'POST':
        form = RTAUploadForm(request.POST, request.FILES)
        if form.is_valid():
            rta_file = form.save(commit=False)
            rta_file.file_name = request.FILES['file'].name
            rta_file.save()

            # Trigger Parser Sync
            parser = None
            filename = rta_file.file_name.lower()

            if rta_file.rta_type == RTAFile.RTA_CAMS:
                # CAMS is now strictly DBF
                if filename.endswith('.dbf'):
                    parser = DBFParser(rta_file_obj=rta_file)
                else:
                    # Fallback or Error? 
                    # User said "use the dbf parser only".
                    # If they upload .txt or .xls, we fail.
                    rta_file.status = RTAFile.STATUS_FAILED
                    rta_file.error_log = "Only DBF format is supported for CAMS."
                    rta_file.save()
                    messages.error(request, "Only DBF format is supported for CAMS.")
                    return redirect('reconciliation:rta_upload')

            elif rta_file.rta_type == RTAFile.RTA_KARVY:
                if filename.endswith('.dbf'):
                     parser = DBFParser(rta_file_obj=rta_file)
                elif filename.endswith('.xls') or filename.endswith('.xlsx'):
                     parser = KarvyXLSParser(rta_file_obj=rta_file)
                else:
                    parser = KarvyParser(rta_file_obj=rta_file)
            
            elif rta_file.rta_type == RTAFile.RTA_FRANKLIN:
                parser = FranklinParser(rta_file_obj=rta_file)

            if parser:
                def run_parser():
                    try:
                        parser.parse()
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
