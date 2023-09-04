from django.urls import path, re_path, include
from rest_framework.routers import SimpleRouter

from .views import (
    UserListAdminView, UserSearchAdminView, block_or_unblock_user_admin_view,
    ProductListAdminView, ProductReviewAdminView, get_new_reviews_count,
    AdminOrderListView, AdminOrderSearchView, update_order_to_delivered, update_order_to_success,
    PromotionListAdminView, PromotionRetrieveAdminView, PromotionCreateAdminView, PromotionDeleteAdminView,
    ConversionListAdminView, UpdateConversionAdminView
)


promotions_urlpatterns = [
    path('promotions/', PromotionListAdminView.as_view(), name='admin_promotions_list'),
    path('promotions/create/', PromotionCreateAdminView.as_view(), name='admin_promotions_create'),
    re_path('^promotions/retrieve/(?P<id>.+)/$', PromotionRetrieveAdminView.as_view(), name='admin_promotions_retrieve'),
    re_path('^promotions/delete/(?P<id>.+)/$', PromotionDeleteAdminView.as_view(), name='admin_promotions_delete'),
]


users_urlpatterns = [
    path('users/', UserListAdminView.as_view(), name='admin_users_list'),
    path('users/search/', UserSearchAdminView.as_view(), name='admin_users_search'),
    re_path('^users/block-or-unblock/(?P<user_id>.+)/', block_or_unblock_user_admin_view, name='admin_users_blocking')
]

product_router = SimpleRouter()
product_router.register('reviews', ProductReviewAdminView)

product_urlpatterns = [
    path('products/', ProductListAdminView.as_view(), name='admin_product_list'),
    path('new-reviews/count/', get_new_reviews_count, name='admin_reviews'),
    path('', include(product_router.urls)),
]

order_urlpatterns = [
    path('orders/', AdminOrderListView.as_view(), name='admin_orders_list'),
    path('orders/search/', AdminOrderSearchView.as_view(), name='admin_orders_search'),
    re_path('^orders/(?P<id>.+)/update/delivered/$', update_order_to_delivered, name='admin_orders_retrieve'),
    re_path('^orders/(?P<id>.+)/update/success/$', update_order_to_success, name='admin_orders_retrieve'),
]

currencies_urlpatterns = [
    path('conversion/', ConversionListAdminView.as_view(), name='admin_conversion_list'),
    re_path('^conversion/(?P<id>.+)/$', UpdateConversionAdminView.as_view(), name='admin_conversion_update')
]


urlpatterns = (
    users_urlpatterns + product_urlpatterns + order_urlpatterns + promotions_urlpatterns + currencies_urlpatterns
)
