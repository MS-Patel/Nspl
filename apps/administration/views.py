from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from .models import SystemConfiguration
from .forms import SystemConfigurationForm

# Create your views here.
@login_required
def index(request):
    return render(request, 'administration/index.html')

@login_required
@user_passes_test(lambda u: u.is_superuser or getattr(u, 'user_type', '') == 'ADMIN')
def system_configuration(request):
    config = SystemConfiguration.get_solo()

    if request.method == 'POST':
        form = SystemConfigurationForm(request.POST, request.FILES, instance=config)
        if form.is_valid():
            form.save()
            messages.success(request, "System configuration updated successfully.")
            return redirect('administration:system_configuration')
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = SystemConfigurationForm(instance=config)

    return render(request, 'administration/system_configuration.html', {'form': form})
