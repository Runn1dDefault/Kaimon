from django.urls import path, include, re_path
from rest_framework.routers import SimpleRouter

from .views import CategoryViewSet, ProductsViewSet, UserReviewViewSet, ProductReviewsAPIView, ProductSearchView

router = SimpleRouter()
router.register('categories', CategoryViewSet, basename='categories')
router.register('products', ProductsViewSet, basename='products')
router.register('my-reviews', UserReviewViewSet, basename='user-reviews')

urlpatterns = [
    path('products/search/', ProductSearchView.as_view(), name='products-search'),
    path('', include(router.urls)),
    re_path('^products/(?P<product_id>.+)/reviews$', ProductReviewsAPIView.as_view(), name='product-reviews-list')
]
