from django.urls import path, re_path

from .views import OrderListView, OrderSearchView, OrderDetailView, update_order_to_delivered, update_order_to_success


urlpatterns = [
    path('orders/', OrderListView.as_view(), name='admin_orders_list'),
    path('orders/search/', OrderSearchView.as_view(), name='admin_orders_search'),
    path('orders/', OrderListView.as_view(), name='admin_orders_list'),
    re_path('^orders/(?P<id>.+)/$', OrderDetailView.as_view(), name='admin_orders_retrieve'),
    re_path('^orders/(?P<id>.+)/update/delivered/$', update_order_to_delivered, name='admin_orders_retrieve'),
    re_path('^orders/(?P<id>.+)/update/success/$', update_order_to_success, name='admin_orders_retrieve'),
]
