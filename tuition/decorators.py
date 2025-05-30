from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages

def admin_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if request.user.user_type != 'admin':
            messages.error(request, 'You do not have permission to access this page.')
            return redirect('tuition:admin_login')
        return view_func(request, *args, **kwargs)
    return _wrapped_view

def payer_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if request.user.user_type != 'payer':
            messages.error(request, 'You do not have permission to access this page.')
            return redirect('tuition:payer_login')
        return view_func(request, *args, **kwargs)
    return _wrapped_view
