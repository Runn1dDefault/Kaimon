from django.urls import path, include
from rest_framework.routers import SimpleRouter

from .views import (
    OrderAnalyticsView, UserAnalyticsView, ReviewAnalyticsView,
    ProductAdminViewSet, ProductReviewAdminViewSet,
    CategoryAdminViewSet, TagListAdminView, PromotionAdminViewSet,
    OrderAdminViewSet, ConversionAdminViewSet, UserAdminViewSet,
)

router = SimpleRouter()
router.register('categories', CategoryAdminViewSet, basename='admin-categories')
router.register('products', ProductAdminViewSet, basename='admin-products')
router.register('reviews', ProductReviewAdminViewSet, basename='admin-reviews')
router.register('orders', OrderAdminViewSet, basename='admin-orders')
router.register('promotions', PromotionAdminViewSet, basename='admin-promotions')
router.register('users', UserAdminViewSet, basename='admin-users')
router.register('conversions', ConversionAdminViewSet, basename='admin-conversions')

analytics_urlpatterns = [
    path('analytics/orders/', OrderAnalyticsView.as_view(), name='admin-analytics-orders'),
    path('analytics/users/', UserAnalyticsView.as_view(), name='admin-analytics-users'),
    path('analytics/reviews/', ReviewAnalyticsView.as_view(), name='admin-analytics-users')
]

urlpatterns = analytics_urlpatterns + [
    path('products/tags/', TagListAdminView.as_view(), name='admin-tag-list'),
    path('', include(router.urls)),
]
