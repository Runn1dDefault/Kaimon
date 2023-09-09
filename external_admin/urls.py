from django.urls import path, re_path, include
from rest_framework.routers import SimpleRouter

from .views import (
    ProductAdminViewSet, ProductListAdminView, ProductReviewAdminView,
    GenreSearchAdminView, TagSearchAdminView,
    OrderAdminViewSet,
    PromotionAdminViewSet,
    ConversionListAdminView, UpdateConversionAdminView, UserAdminView
)

router = SimpleRouter()
router.register('reviews', ProductReviewAdminView)
router.register('products', ProductAdminViewSet)
router.register('orders', OrderAdminViewSet)
router.register('promotions', PromotionAdminViewSet)
router.register('users', UserAdminView)

urlpatterns = [
    path('products/', ProductListAdminView.as_view(), name='admin_product_list'),
    path('products/genres/search/', GenreSearchAdminView.as_view(), name='product_search'),
    path('products/tags/search/', TagSearchAdminView.as_view(), name='product_search'),
    path('', include(router.urls)),
    path('conversion/', ConversionListAdminView.as_view(), name='admin_conversion_list'),
    re_path('^conversion/(?P<id>.+)/$', UpdateConversionAdminView.as_view(), name='admin_conversion_update')
]
