from django.urls import path, include
from rest_framework.routers import SimpleRouter

from .views import CountryListView, DeliveryAddressViewSet, OrderViewSet

router = SimpleRouter()
router.register('delivery-address', DeliveryAddressViewSet)
router.register('', OrderViewSet)


urlpatterns = [
    path('order/', include(router.urls)),
    path('order/countries/', CountryListView.as_view(), name='order_countries'),
    path('admin/', include('order.external_admin.urls'))
]
