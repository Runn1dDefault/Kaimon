from django.urls import path, re_path, include
from rest_framework.routers import SimpleRouter

from .views import (
    OrderAnalyticsView, UserAnalyticsView, ReviewAnalyticsView,
    ProductAdminViewSet, ProductReviewAdminViewSet,
    GenreListAdminView, TagGroupListAdminViewSet, PromotionAdminViewSet,
    OrderAdminViewSet, ConversionAdminViewSet, UserAdminViewSet,
)

router = SimpleRouter()
router.register('products', ProductAdminViewSet, basename='admin-products')
router.register('reviews', ProductReviewAdminViewSet, basename='admin-reviews')
router.register('orders', OrderAdminViewSet, basename='admin-orders')
router.register('promotions', PromotionAdminViewSet, basename='admin-promotions')
router.register('users', UserAdminViewSet, basename='admin-users')
router.register('tag-groups', TagGroupListAdminViewSet, basename='admin-tag-groups')
router.register('conversions', ConversionAdminViewSet, basename='admin-conversions')

analytics_urlpatterns = [
    path('analytics/orders/', OrderAnalyticsView.as_view(), name='admin-analytics-orders'),
    path('analytics/users/', UserAnalyticsView.as_view(), name='admin-analytics-users'),
    path('analytics/reviews/', ReviewAnalyticsView.as_view(), name='admin-analytics-users')
]

urlpatterns = analytics_urlpatterns + [
    path('products/genres/', GenreListAdminView.as_view(), name='admin-genres-list'),
    path('', include(router.urls)),
]
