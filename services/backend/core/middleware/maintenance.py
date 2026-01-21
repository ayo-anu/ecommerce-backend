import logging
import time

from django.conf import settings
from django.core.cache import cache
from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger(__name__)

_last_check = 0.0
_last_value = False


def _get_maintenance_mode():
    global _last_check, _last_value

    ttl = getattr(settings, "MAINTENANCE_MODE_CACHE_TTL", 5)
    now = time.monotonic()
    if now - _last_check < ttl:
        return _last_value

    try:
        _last_value = bool(cache.get("maintenance_mode", False))
    except Exception:
        logger.warning("maintenance_mode_cache_unavailable", exc_info=True)
        _last_value = False

    _last_check = now
    return _last_value


class MaintenanceModeMiddleware(MiddlewareMixin):
    def process_request(self, request):
        maintenance_mode = _get_maintenance_mode()

        if maintenance_mode and not (
            getattr(request, "user", None)
            and request.user.is_authenticated
            and request.user.is_staff
        ):
            return JsonResponse(
                {
                    "error": True,
                    "message": "Site is currently under maintenance. Please check back soon.",
                    "status_code": 503,
                },
                status=503,
            )
