from django.urls import path, re_path, include
from rest_framework.routers import SimpleRouter

from .views import CategoryViewSet, ProductsViewSet, UserReviewViewSet, ProductReviewsAPIView, ReferenceListAPIView


router = SimpleRouter()
router.register('categories', CategoryViewSet, basename='categories')
router.register('products', ProductsViewSet, basename='products')
router.register('my-reviews', UserReviewViewSet, basename='user-reviews')

urlpatterns = [
    path('products/recommendations/', ReferenceListAPIView.as_view(), name='product-recommendations-list'),
    path('', include(router.urls))
]
