from django.urls import path, include, re_path
from rest_framework.routers import SimpleRouter

from .views import (
    CategoryViewSet, UserReviewViewSet, ProductsViewSet, ProductByCategoryView,
    ProductReviewsAPIView, ProductsSearchView, ProductReferenceView, NewProductsView, PopularProductsView,
    ProductByIdsView, InventoriesByIdsView
)

router = SimpleRouter()
router.register('categories', CategoryViewSet, basename='categories')
router.register('products', ProductsViewSet, basename='products')
router.register('my-reviews', UserReviewViewSet, basename='user-reviews')

urlpatterns = [
    path('products-by-ids/', ProductByIdsView.as_view(), name='product-products-by-ids-list'),
    path('inventory-by-ids/', InventoriesByIdsView.as_view(), name='product-inventory-by-ids-list'),
    path('products/new/', NewProductsView.as_view(), name='products-new'),
    path('products/popular/', PopularProductsView.as_view(), name='products-popular'),
    path('products/search/', ProductsSearchView.as_view(), name='products-search'),
    path('', include(router.urls)),
    re_path('^categories/(?P<category_id>.+)/products/$', ProductByCategoryView.as_view(),
            name='product-category-products-list'),
    re_path('^products/(?P<product_id>.+)/reviews/$', ProductReviewsAPIView.as_view(), name='product-reviews-list'),
    re_path('^products/(?P<product_id>.+)/reference/$', ProductReferenceView.as_view(), name='product-reference-list'),
]
