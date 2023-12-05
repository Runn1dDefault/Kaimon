from django.urls import path, include, re_path
from rest_framework.routers import SimpleRouter

from .views import (
    CategoryViewSet, UserReviewViewSet, ProductsViewSet,
    ProductReviewsAPIView, ProductsSearchView, ProductReferenceView, NewProductsView, PopularProductsView
)

router = SimpleRouter()
router.register('categories', CategoryViewSet, basename='categories')
router.register('products', ProductsViewSet, basename='products')
router.register('my-reviews', UserReviewViewSet, basename='user-reviews')

urlpatterns = [
    path('products/new/', NewProductsView.as_view(), name='products-new'),
    path('products/popular/', PopularProductsView.as_view(), name='products-popular'),
    path('products/search/', ProductsSearchView.as_view(), name='products-search'),
    path('', include(router.urls)),
    re_path('^products/(?P<product_id>.+)/reviews$', ProductReviewsAPIView.as_view(), name='product-reviews-list'),
    re_path('^products/(?P<product_id>.+)/reference', ProductReferenceView.as_view(), name='product-reference-list'),
]
