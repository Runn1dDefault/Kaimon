from django.urls import path, re_path, include
from rest_framework.routers import SimpleRouter

from .views import (
    ProductAdminViewSet, ProductReviewAdminView,
    GenreSearchAdminView, TagSearchAdminView,
    OrderAnalyticsView, UserAnalyticsView, ReviewAnalyticsView,
    PromotionAdminViewSet,
    ConversionListAdminView, UpdateConversionAdminView, UserAdminView, OrderAdminViewSet
)

router = SimpleRouter()
router.register('reviews', ProductReviewAdminView, basename='admin-reviews')
router.register('products', ProductAdminViewSet, basename='admin-products')
router.register('orders', OrderAdminViewSet, basename='admin-orders')
router.register('promotions', PromotionAdminViewSet, basename='admin-promotions')
router.register('users', UserAdminView, basename='admin-users')

analytics_urlpatterns = [
    path('analytics/orders/', OrderAnalyticsView.as_view(), name='admin-analytics-orders'),
    path('analytics/users/', UserAnalyticsView.as_view(), name='admin-analytics-users'),
    path('analytics/reviews/', ReviewAnalyticsView.as_view(), name='admin-analytics-users')
]

urlpatterns = analytics_urlpatterns + [
    path('products/genres/', GenreSearchAdminView.as_view(), name='admin-genres-list'),
    path('products/tags/', TagSearchAdminView.as_view(), name='admin-tags-list'),
    path('conversions/', ConversionListAdminView.as_view(), name='admin-conversions-list'),
    re_path('^conversions/(?P<id>.+)/$', UpdateConversionAdminView.as_view(), name='admin-conversion-update'),
    path('', include(router.urls)),
]
