from django.http import HttpResponseRedirect


class LoginRequiredMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not request.user.is_authenticated:
            if not request.path.startswith('/login') and not request.path.startswith('/admin/login'):
                return HttpResponseRedirect('/login/')
        return self.get_response(request)
