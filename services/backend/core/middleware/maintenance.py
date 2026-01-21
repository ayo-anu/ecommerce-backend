from django.core.cache import cache
from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin


class MaintenanceModeMiddleware(MiddlewareMixin):
    def process_request(self, request):
        maintenance_mode = cache.get("maintenance_mode", False)

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
