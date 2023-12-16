from django.urls import path, include, re_path
from rest_framework.routers import SimpleRouter

from .views import OrderViewSet, DeliveryAddressViewSet, FedexQuoteRateView, order_info, InitPaymentView, \
    PayboxResultView

router = SimpleRouter()
router.register('delivery-address', DeliveryAddressViewSet, basename='delivery-address')
router.register('', OrderViewSet, basename='orders')


urlpatterns = [
    path('fedex-quote-rate/', FedexQuoteRateView.as_view(), name='orders-fedex-quotes-rates'),
    path('init_payment/', InitPaymentView.as_view(), name='orders-init-payment'),
    path('paybox-result/', PayboxResultView.as_view(), name='order-paybox-result'),
    path('', include(router.urls)),
    re_path('^order-info/(?P<order_id>.+)/$', order_info, name="order-info")
]
