from django.conf import settings


class ForceHTTPSMiddleware:
    """
    Middleware to force HTTPS scheme on requests.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if settings.FORCE_HTTPS:
            request.scheme = "https"

        response = self.get_response(request)
        return response
