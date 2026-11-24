from django.contrib import messages
from django.contrib.auth import logout
from django.shortcuts import redirect
from django.urls import reverse


class ActiveAccountRequiredMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated and not request.user.is_active:
            allowed_paths = (
                reverse('login'),
                reverse('logout'),
                '/static/',
                '/media/',
            )
            if not request.path.startswith(allowed_paths):
                logout(request)
                messages.error(request, 'Your account is inactive. Please contact the school store administrator.')
                return redirect('login')

        return self.get_response(request)
