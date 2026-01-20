from django.contrib import admin

from django.urls import path, include

from django.conf import settings

from django.conf.urls.static import static

from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView

from core.jwks import JWKSView

import importlib.util



urlpatterns = [

    path('admin/', admin.site.urls),


    path('health/', include('apps.health.urls')),


    path('', include('django_prometheus.urls')),


    path('.well-known/jwks.json', JWKSView.as_view(), name='jwks'),


    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),

    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),

    path('api/docs/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),


    path('api/auth/', include('apps.accounts.urls')),

    path('api/products/', include('apps.products.urls')),

    path('api/orders/', include('apps.orders.urls')),

    path('api/payments/', include('apps.payments.urls')),

    path('api/notifications/', include('apps.notifications.urls')),

    path('api/analytics/', include('apps.analytics.urls')),

]


if settings.DEBUG:

    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)


    if importlib.util.find_spec("debug_toolbar"):

        import debug_toolbar

        urlpatterns = [

            path('__debug__/', include(debug_toolbar.urls)),

        ] + urlpatterns


admin.site.site_header = "E-Commerce Admin"

admin.site.site_title = "E-Commerce Admin Portal"

admin.site.index_title = "Welcome to E-Commerce Admin Portal"

