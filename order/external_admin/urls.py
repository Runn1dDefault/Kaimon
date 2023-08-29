from django.urls import path, re_path

from .views import AdminOrderListView, AdminOrderSearchView, update_order_to_delivered, update_order_to_success


urlpatterns = [
    path('orders/', AdminOrderListView.as_view(), name='admin_orders_list'),
    path('orders/search/', AdminOrderSearchView.as_view(), name='admin_orders_search'),
    re_path('^orders/(?P<id>.+)/update/delivered/$', update_order_to_delivered, name='admin_orders_retrieve'),
    re_path('^orders/(?P<id>.+)/update/success/$', update_order_to_success, name='admin_orders_retrieve'),
]
