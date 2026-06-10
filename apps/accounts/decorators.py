from functools import wraps

from django.contrib.auth.views import redirect_to_login
from django.shortcuts import redirect

from apps.accounts.services import is_admin


def admin_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path())
        if not is_admin(request.user):
            return redirect("dashboard:home")
        return view_func(request, *args, **kwargs)

    return wrapper
