from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django import forms
from .models import RTAFile
from .parsers import CAMSParser, KarvyParser, FranklinParser

class RTAUploadForm(forms.ModelForm):
    class Meta:
        model = RTAFile
        fields = ['rta_type', 'file']

@login_required
def upload_rta_file(request):
    # Only Admin or Operations (assuming Admin for now)
    if request.user.user_type != 'ADMIN':
        messages.error(request, "Access Denied")
        return redirect('dashboard')

    if request.method == 'POST':
        form = RTAUploadForm(request.POST, request.FILES)
        if form.is_valid():
            rta_file = form.save(commit=False)
            rta_file.file_name = request.FILES['file'].name
            rta_file.save()

            # Trigger Parser Sync
            parser = None
            if rta_file.rta_type == RTAFile.RTA_CAMS:
                parser = CAMSParser(rta_file)
            elif rta_file.rta_type == RTAFile.RTA_KARVY:
                parser = KarvyParser(rta_file)
            elif rta_file.rta_type == RTAFile.RTA_FRANKLIN:
                parser = FranklinParser(rta_file)

            if parser:
                parser.parse()
            else:
                rta_file.status = RTAFile.STATUS_FAILED
                rta_file.error_log = "Unknown RTA Type"
                rta_file.save()

            if rta_file.status == RTAFile.STATUS_PROCESSED:
                messages.success(request, "File processed successfully.")
            elif rta_file.status == RTAFile.STATUS_FAILED:
                 messages.error(request, f"Processing Failed: {rta_file.error_log}")
            else:
                messages.warning(request, "File uploaded but processing status is pending.")

            return redirect('rta_upload')
    else:
        form = RTAUploadForm()

    recent_files = RTAFile.objects.all().order_by('-uploaded_at')[:5]
    return render(request, 'reconciliation/upload.html', {'form': form, 'recent_files': recent_files})
