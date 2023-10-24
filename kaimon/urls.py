from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView

docs_urlpatterns = [
    path('api/v1/schema/', SpectacularAPIView.as_view(), name='schema'),
    # Optional UI:
    path('api/v1/schema/swagger-ui/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/v1/schema/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc')
]

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/auth/', include('users.urls')),
    path('api/v1/products/', include('product.urls')),
    # path('api/v1/order/', include('order.urls')),
    # path('api/v1/promotions/', include('promotions.urls')),
    path('api/v1/external-admin/', include('external_admin.urls'))
] + docs_urlpatterns

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, docement_root=settings.STATIC_ROOT)
