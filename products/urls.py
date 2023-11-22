from django.urls import path, include, re_path
from rest_framework.routers import SimpleRouter

from .views import CategoryViewSet, ProductsViewSet, UserReviewViewSet, ProductReviewsAPIView


router = SimpleRouter()
router.register('categories', CategoryViewSet, basename='categories')
router.register('products', ProductsViewSet, basename='products')
router.register('my-reviews', UserReviewViewSet, basename='user-reviews')

urlpatterns = [
    path('', include(router.urls)),
    re_path('^products/(?P<product_id>.+)/reviews$', ProductReviewsAPIView.as_view(), name='product-reviews-list')
]
