import logging
import time
from typing import Callable

from django.http import HttpRequest, HttpResponse

logger: logging.Logger = logging.getLogger(__name__)


class RequestLoggingMiddleware:
    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        start_time = time.time()

        logger.info(
            f"Request: {request.method} {request.path} "
            f"- User: {request.user if hasattr(request, 'user') else 'Anonymous'} "
            f"- IP: {self.get_client_ip(request)}"
        )

        response = self.get_response(request)

        duration = time.time() - start_time
        logger.info(
            f"Response: {request.method} {request.path} "
            f"- Status: {response.status_code} "
            f"- Duration: {duration:.3f}s"
        )

        return response

    @staticmethod
    def get_client_ip(request: HttpRequest) -> str:
        """Extract client IP address from request."""
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            ip = x_forwarded_for.split(",")[0]
        else:
            ip = request.META.get("REMOTE_ADDR", "Unknown")
        return ip
