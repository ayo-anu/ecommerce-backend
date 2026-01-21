import logging
import time

from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger(__name__)


class RequestLoggingMiddleware(MiddlewareMixin):
    def process_request(self, request):
        request.start_time = time.time()

    def process_response(self, request, response):
        if hasattr(request, "start_time"):
            duration = time.time() - request.start_time
            logger.info(
                "request_completed",
                extra={
                    "method": request.method,
                    "path": request.path,
                    "status_code": response.status_code,
                    "duration_ms": round(duration * 1000, 2),
                    "user": str(request.user)
                    if getattr(request, "user", None) and request.user.is_authenticated
                    else "anonymous",
                    "ip": self._get_client_ip(request),
                },
            )
            response["X-Response-Time"] = f"{duration:.3f}s"

        return response

    def _get_client_ip(self, request):
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            return x_forwarded_for.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR")
