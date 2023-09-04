from django.urls import path, include
from rest_framework.routers import SimpleRouter

from .views import CountryListView, DeliveryAddressViewSet, OrderViewSet

router = SimpleRouter()
router.register('delivery-address', DeliveryAddressViewSet)
router.register('', OrderViewSet)


urlpatterns = [
    path('', include(router.urls)),
    path('countries/', CountryListView.as_view(), name='order_countries')
]
