from django.urls import path, include
from rest_framework.routers import SimpleRouter

from .views import OrderViewSet, DeliveryAddressViewSet

router = SimpleRouter()
router.register('delivery-address', DeliveryAddressViewSet, basename='delivery-address')
router.register('', OrderViewSet, basename='orders')


urlpatterns = [
    path('', include(router.urls)),
]
