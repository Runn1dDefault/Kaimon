from django.urls import path, re_path, include
from rest_framework.routers import SimpleRouter

from .views import get_languages_view, GenreProductsListView, SearchProductView, GenreReadViewSet, NewProductsView, \
    ProductReviewView, PopularProductsView


router = SimpleRouter()
router.register('', GenreReadViewSet, basename='product_genres')


urlpatterns = [
    path('languages/', get_languages_view, name='product_languages_list'),
    path('product/genres/', include(router.urls)),
    re_path('^product/genres/(?P<id>.+)/products/$', GenreProductsListView.as_view(), name='product_genre_products'),
    path('product/search/', SearchProductView.as_view(), name='product_search'),
    re_path('^product/(?P<id>.+)/reviews/', ProductReviewView.as_view(), name='product_review'),
    path('product/new/', NewProductsView.as_view(), name='product_new'),
    path('product/popular/', PopularProductsView.as_view(), name='product_popular'),
    path('admin/', include('product.external_admin.urls')),
]
