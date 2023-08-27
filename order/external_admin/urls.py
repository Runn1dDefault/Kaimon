from django.urls import path

from .views import OrderListView, OrderSearchView


urlpatterns = [
    path('orders/', OrderListView.as_view(), name='admin_orders_list'),
    path('orders/search/', OrderSearchView.as_view(), name='admin_orders_search'),
]
