from django.urls import path, re_path, include
from rest_framework.routers import SimpleRouter

from .views import (
    ProductAdminViewSet, ProductReviewAdminView,
    GenreSearchAdminView, TagSearchAdminView,
    OrderAnalyticsView, OrderAdminViewSet,
    PromotionAdminViewSet,
    ConversionListAdminView, UpdateConversionAdminView, UserAdminView
)

router = SimpleRouter()
router.register('reviews', ProductReviewAdminView)
router.register('products', ProductAdminViewSet)
# router.register('orders', OrderAdminViewSet)
router.register('promotions', PromotionAdminViewSet)
router.register('users', UserAdminView)

urlpatterns = [
    path('analytics/orders/', OrderAnalyticsView.as_view(), name='admin_analytics_orders'),
    path('products/genres/', GenreSearchAdminView.as_view(), name='admin_genres_search'),
    path('products/tags/', TagSearchAdminView.as_view(), name='admin_tags_search'),
    path('conversion/', ConversionListAdminView.as_view(), name='admin_conversion_list'),
    re_path('^conversion/(?P<id>.+)/$', UpdateConversionAdminView.as_view(), name='admin_conversion_update'),
    path('', include(router.urls)),
]
