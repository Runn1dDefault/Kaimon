from django.urls import path, include
from rest_framework.routers import SimpleRouter

from .views import OrderViewSet, DeliveryAddressViewSet, FedexQuoteRateView

router = SimpleRouter()
router.register('delivery-address', DeliveryAddressViewSet, basename='delivery-address')
router.register('', OrderViewSet, basename='orders')


urlpatterns = [
    path('fedex-quote-rate/', FedexQuoteRateView.as_view(), name='orders-fedex-quotes-rates'),
    path('', include(router.urls)),
]
