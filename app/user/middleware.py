# app/middleware.py
from django.shortcuts import redirect
from django.urls import reverse

class ForcePasswordChangeMiddleware:
    """
    Redirects users to the password reset page if they must reset their password.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            # Suppose you have a boolean field in user model: first_time_login_to_reset_pass
            force_reset = getattr(request.user, "first_time_login_to_reset_pass", False)
            
            reset_url = reverse("password_change")  # change to your url name

            # If the user must reset password and is not already on reset page
            if force_reset and request.path != reset_url:
                return redirect(reset_url)

        return self.get_response(request)
