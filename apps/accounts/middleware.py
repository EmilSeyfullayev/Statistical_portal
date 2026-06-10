from django.shortcuts import redirect

from apps.accounts.services import is_admin


class AdminAccessMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path.startswith("/admin/") and request.user.is_authenticated and not is_admin(request.user):
            return redirect("dashboard:home")
        return self.get_response(request)
