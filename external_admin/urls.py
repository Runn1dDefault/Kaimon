from django.urls import path, include
from rest_framework.routers import SimpleRouter

from .views import (
    OrderAnalyticsView, UserAnalyticsView, ReviewAnalyticsView,
    ProductAdminViewSet, ProductReviewAdminViewSet,
    CategoryAdminViewSet, PromotionAdminViewSet,
    OrderAdminViewSet, ConversionAdminViewSet, UserAdminViewSet, ProductInventoryViewSet, TagGroupAdminViewSet,
    ProductListView, ProductSearchListView
)

router = SimpleRouter()
router.register('categories', CategoryAdminViewSet, basename='admin-categories')
router.register('products', ProductAdminViewSet, basename='admin-products')
router.register('inventories', ProductInventoryViewSet, basename='admin-inventories')
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
    path('products/list/', ProductListView.as_view()),
    path('products/search/', ProductSearchListView.as_view()),

    path('tags/', TagGroupAdminViewSet.as_view(), name="admin-grouped-tags"),
    path('', include(router.urls)),
]
