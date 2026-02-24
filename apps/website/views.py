from django.shortcuts import render
from django.urls import reverse
from apps.users.models import User
from django.views.generic import TemplateView

def get_dashboard_url(user):
    if user.user_type == User.Types.RM:
        return reverse('users:rm_dashboard')
    elif user.user_type == User.Types.DISTRIBUTOR:
        return reverse('users:distributor_dashboard')
    elif user.user_type == User.Types.INVESTOR:
        return reverse('users:investor_dashboard')
    else:
        return reverse('users:admin_dashboard')

def home(request):
    dashboard_url = None
    if request.user.is_authenticated:
        dashboard_url = get_dashboard_url(request.user)

    context = {
        'dashboard_url': dashboard_url,
    }
    return render(request, 'website/home.html', context)

def about(request):
    dashboard_url = None
    if request.user.is_authenticated:
        dashboard_url = get_dashboard_url(request.user)
    return render(request, 'website/about.html', {'dashboard_url': dashboard_url})

def contact(request):
    dashboard_url = None
    if request.user.is_authenticated:
        dashboard_url = get_dashboard_url(request.user)
    return render(request, 'website/contact.html', {'dashboard_url': dashboard_url})

def mutual_funds(request):
    dashboard_url = None
    if request.user.is_authenticated:
        dashboard_url = get_dashboard_url(request.user)
    return render(request, 'website/mutual_funds.html', {'dashboard_url': dashboard_url})


def privacypolicy(request):
    dashboard_url = None
    if request.user.is_authenticated:
        dashboard_url = get_dashboard_url(request.user)
    return render(request, 'website/privacypolicy.html', {'dashboard_url': dashboard_url})



def termscondition(request):
    dashboard_url = None
    if request.user.is_authenticated:
        dashboard_url = get_dashboard_url(request.user)
    return render(request, 'website/termscondition.html', {'dashboard_url': dashboard_url})


def documentsdownload(request):
    dashboard_url = None
    if request.user.is_authenticated:
        dashboard_url = get_dashboard_url(request.user)
    return render(request, 'website/documentsdownload.html', {'dashboard_url': dashboard_url})

from django.views.decorators.csrf import ensure_csrf_cookie
from django.utils.decorators import method_decorator

@method_decorator(ensure_csrf_cookie, name='dispatch')
class ReactAppView(TemplateView):
    template_name = "index.html"
