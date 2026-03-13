from django.shortcuts import render

def maintenance_view(request):
    """View to display the maintenance page."""
    # We return a 503 Service Unavailable status code
    return render(request, 'core/maintenance.html', status=503)