from django.shortcuts import redirect
from django.urls import resolve
from django.http import JsonResponse
from apps.administration.models import SystemConfiguration

class MaintenanceModeMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Allow superusers, staff, and django admin
        if getattr(request, 'user', None) and (request.user.is_superuser or request.user.is_staff):
            return self.get_response(request)

        # Allow access to the maintenance page itself to avoid infinite redirect
        try:
            current_url_name = resolve(request.path_info).url_name
            if current_url_name == 'maintenance':
                return self.get_response(request)
        except Exception:
            pass

        # Allow static files and media
        if request.path.startswith('/static/') or request.path.startswith('/media/'):
            return self.get_response(request)

        # Allow Django admin login
        if request.path.startswith('/admin/'):
            return self.get_response(request)

        # Check if maintenance mode is enabled
        try:
            config = SystemConfiguration.get_solo()
            if config.is_maintenance_mode:
                # If it's an API request or expects JSON, return a 503 Service Unavailable
                if request.path.startswith('/api/') or request.path.startswith('/users/otp/') or getattr(request, 'content_type', '') == 'application/json':
                    return JsonResponse({
                        'error': 'Service Unavailable',
                        'message': 'The system is currently undergoing scheduled maintenance. Please try again later.'
                    }, status=503)

                # Otherwise, redirect to the maintenance HTML page
                return redirect('core:maintenance')
        except Exception:
            # Fallback if DB is completely down or config cannot be loaded
            pass

        return self.get_response(request)
